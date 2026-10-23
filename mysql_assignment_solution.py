# %%
import csv
import os
from decimal import Decimal

import mysql.connector
import pandas as pd
from mysql.connector import Error
from ingest_data import ingest_csv_to_mysql

# %%
DB_CONFIG = {
    "host": "********",
    "user": "********",
    "password": "*******",
    "database": "company_db",
}
CSV_PATH = os.path.abspath("employees_data.csv")

# %%
def get_connection(use_database=True):
    config = DB_CONFIG.copy()
    if not use_database:
        config.pop("database", None)
    return mysql.connector.connect(**config)

# %%
def create_database_and_table():
    conn = get_connection(use_database=False)
    cursor = conn.cursor()
    try:
        cursor.execute("CREATE DATABASE IF NOT EXISTS company_db")
        conn.commit()
        print("Database 'company_db' is ready.")
    finally:
        cursor.close()
        conn.close()

    conn = get_connection(use_database=True)
    cursor = conn.cursor()
    try:
        cursor.execute("DROP TABLE IF EXISTS employees")
        cursor.execute(
            """
            CREATE TABLE employees (
                employee_id INT AUTO_INCREMENT PRIMARY KEY,
                first_name VARCHAR(50) NOT NULL,
                last_name VARCHAR(50) NOT NULL,
                department VARCHAR(50) NOT NULL,
                salary DECIMAL(10,2) NOT NULL,
                hire_date DATE NOT NULL,
                Day_of_Week VARCHAR(15),
                Day_of_month INT,
                Month VARCHAR(15),
                Year INT
            )
            """
        )
        conn.commit()
        print("Table 'employees' created successfully.")
    finally:
        cursor.close()
        conn.close()

# %%
QUERIES = [
    (
        "1. Intra-Department Salary Ranking",
        """
        SELECT
            department,
            first_name,
            salary,
            RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS salary_rank
        FROM employees
        ORDER BY department, salary DESC
        """,
    ),
    (
        "2. Peer Salary Delta Analysis",
        """
        WITH dept_salary_order AS (
            SELECT
                department,
                first_name,
                salary,
                LAG(salary) OVER (PARTITION BY department ORDER BY salary DESC) AS previous_highest_salary
            FROM employees
        )
        SELECT
            department,
            first_name,
            salary,
            salary - COALESCE(previous_highest_salary, salary) AS salary_delta_from_previous_highest
        FROM dept_salary_order
        ORDER BY department, salary DESC
        """,
    ),
    (
        "3. High-Expenditure Outlier Departments",
        """
        WITH dept_total AS (
            SELECT department, SUM(salary) AS total_salary
            FROM employees
            GROUP BY department
        ),
        dept_avg AS (
            SELECT AVG(total_salary) AS avg_total_salary
            FROM dept_total
        )
        SELECT
            dt.department,
            dt.total_salary
        FROM dept_total dt
        CROSS JOIN dept_avg da
        WHERE dt.total_salary > da.avg_total_salary
        ORDER BY dt.total_salary DESC
        """,
    ),
    (
        "4. Cross-Department Ceiling Breakers",
        """
        SELECT
            e.employee_id,
            e.first_name,
            e.last_name,
            e.department,
            e.salary
        FROM employees e
        WHERE e.salary > (
            SELECT MAX(salary)
            FROM employees
            WHERE department = 'HR'
        )
        ORDER BY e.salary DESC
        """,
    ),
    (
        "5. Cumulative Departmental Spending",
        """
        SELECT
            department,
            first_name,
            hire_date,
            salary,
            SUM(salary) OVER (
                PARTITION BY department
                ORDER BY hire_date
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) AS cumulative_department_spend
        FROM employees
        ORDER BY department, hire_date
        """,
    ),
    (
        "6. The Second-Highest Earner Problem",
        """
        WITH ranked_emp AS (
            SELECT
                department,
                first_name,
                last_name,
                salary,
                RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS dept_rank
            FROM employees
        )
        SELECT
            department,
            first_name,
            last_name,
            salary,
            dept_rank
        FROM ranked_emp
        WHERE dept_rank = 2
        ORDER BY department, salary DESC
        """,
    ),
    (
        "7. Aggressive Hiring Month Detection",
        """
        WITH monthly_hires AS (
            SELECT
                YEAR(hire_date) AS hire_year,
                MONTHNAME(hire_date) AS month_name,
                COUNT(*) AS hires_in_month
            FROM employees
            GROUP BY YEAR(hire_date), MONTHNAME(hire_date)
        ),
        yearly_avgs AS (
            SELECT
                hire_year,
                AVG(hires_in_month) AS avg_monthly_hires
            FROM monthly_hires
            GROUP BY hire_year
        )
        SELECT
            m.hire_year,
            m.month_name,
            m.hires_in_month
        FROM monthly_hires m
        JOIN yearly_avgs y ON m.hire_year = y.hire_year
        WHERE m.hires_in_month > y.avg_monthly_hires
        ORDER BY m.hire_year, MONTH(STR_TO_DATE(m.month_name, '%M'))
        """,
    ),
    (
        "8. Departmental Salary Quartiles",
        """
        SELECT
            department,
            first_name,
            last_name,
            salary,
            NTILE(4) OVER (PARTITION BY department ORDER BY salary DESC) AS salary_quartile
        FROM employees
        ORDER BY department, salary DESC
        """,
    ),
    (
        "9. Budget Percentage Contribution",
        """
        SELECT
            department,
            first_name,
            salary,
            (salary / SUM(salary) OVER (PARTITION BY department)) * 100 AS pct_of_department_budget
        FROM employees
        ORDER BY department, salary DESC
        """,
    ),
    (
        "10. Rolling 3-Employee Salary Moving Average",
        """
        SELECT
            department,
            first_name,
            hire_date,
            salary,
            AVG(salary) OVER (
                PARTITION BY department
                ORDER BY hire_date
                ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING
            ) AS rolling_3_employee_avg
        FROM employees
        ORDER BY department, hire_date
        """,
    ),
    (
        "11. Volatility Analysis (Salary Spread)",
        """
        WITH dept_spread AS (
            SELECT
                department,
                MAX(salary) - MIN(salary) AS salary_spread
            FROM employees
            GROUP BY department
        )
        SELECT
            department,
            salary_spread
        FROM dept_spread
        WHERE salary_spread = (
            SELECT MAX(salary_spread)
            FROM dept_spread
        )
        """,
    ),
    (
        "12. Anchor Earner Cohorts",
        """
        WITH lowest_salary_employee AS (
            SELECT
                YEAR(hire_date) AS hire_year,
                MONTH(hire_date) AS hire_month
            FROM employees
            ORDER BY salary ASC
            LIMIT 1
        )
        SELECT
            e.employee_id,
            e.first_name,
            e.last_name,
            e.department,
            e.hire_date,
            e.salary
        FROM employees e
        JOIN lowest_salary_employee lse
            ON YEAR(e.hire_date) = lse.hire_year
           AND MONTH(e.hire_date) = lse.hire_month
        ORDER BY e.hire_date
        """,
    ),
    (
        "13. Dense Grouping for Elite Earners",
        """
        WITH dept_dense_rank AS (
    SELECT
        department,
        first_name,
        last_name,
        salary,
        DENSE_RANK() OVER (
            PARTITION BY department
            ORDER BY salary DESC
        ) AS `dense_rank`
    FROM employees
)
SELECT
    department,
    first_name,
    last_name,
    salary,
    `dense_rank`
FROM dept_dense_rank
WHERE `dense_rank` <= 3
ORDER BY department, `dense_rank`, salary DESC
        """,
    ),
    (
        "14. High-Value Operational Units",
        """
        SELECT DISTINCT department
        FROM employees e
        WHERE EXISTS (
            SELECT 1
            FROM employees e2
            WHERE e2.department = e.department
              AND e2.salary > 120000
        )
        ORDER BY department
        """,
    ),
    (
        "15. Hiring Bookends Analysis",
        """
        WITH dept_bookends AS (
            SELECT
                department,
                MIN(hire_date) AS earliest_hire_date,
                MAX(hire_date) AS latest_hire_date
            FROM employees
            GROUP BY department
        ),
        earliest AS (
            SELECT
                d.department,
                e.first_name,
                e.last_name,
                e.hire_date,
                'earliest_hire' AS hire_type
            FROM dept_bookends d
            JOIN employees e
              ON e.department = d.department
             AND e.hire_date = d.earliest_hire_date
        ),
        latest AS (
            SELECT
                d.department,
                e.first_name,
                e.last_name,
                e.hire_date,
                'latest_hire' AS hire_type
            FROM dept_bookends d
            JOIN employees e
              ON e.department = d.department
             AND e.hire_date = d.latest_hire_date
        )
        SELECT *
        FROM earliest
        UNION ALL
        SELECT *
        FROM latest
        ORDER BY department, hire_date
        """,
    ),
    (
        "16. Dynamic Top-Earner Tagging",
        """
        SELECT
            employee_id,
            first_name,
            last_name,
            department,
            salary,
            FIRST_VALUE(CONCAT(first_name, ' ', last_name)) OVER (
                PARTITION BY department
                ORDER BY salary DESC
                ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
            ) AS top_earner_name
        FROM employees
        ORDER BY department, salary DESC
        """,
    ),
    (
        "17. Year-Over-Year Hiring Trajectory",
        """
        WITH yearly_hires AS (
            SELECT
                YEAR(hire_date) AS hire_year,
                COUNT(*) AS headcount
            FROM employees
            GROUP BY YEAR(hire_date)
        )
        SELECT
            hire_year,
            headcount,
            LAG(headcount) OVER (ORDER BY hire_year) AS previous_year_headcount,
            headcount - COALESCE(LAG(headcount) OVER (ORDER BY hire_year), 0) AS yoy_change
        FROM yearly_hires
        ORDER BY hire_year
        """,
    ),
    (
        "18. Peak-Period Cohorts",
        """
        WITH monthly_hires AS (
            SELECT
                YEAR(hire_date) AS hire_year,
                MONTH(hire_date) AS hire_month,
                COUNT(*) AS total_hires
            FROM employees
            GROUP BY YEAR(hire_date), MONTH(hire_date)
        ),
        peak_month AS (
            SELECT hire_year, hire_month
            FROM monthly_hires
            WHERE total_hires = (
                SELECT MAX(total_hires)
                FROM monthly_hires
            )
        )
        SELECT
            e.employee_id,
            e.first_name,
            e.last_name,
            e.department,
            e.hire_date,
            e.salary
        FROM employees e
        JOIN peak_month p
          ON YEAR(e.hire_date) = p.hire_year
         AND MONTH(e.hire_date) = p.hire_month
        ORDER BY e.hire_date
        """,
    ),
    (
        "19. Polarization Index",
        """
        WITH ranked_emp AS (
            SELECT
                department,
                salary,
                PERCENT_RANK() OVER (PARTITION BY department ORDER BY salary) AS pct_rank
            FROM employees
        ),
        top_earners AS (
            SELECT department, AVG(salary) AS avg_top_salary
            FROM ranked_emp
            WHERE pct_rank >= 0.90
            GROUP BY department
        ),
        bottom_earners AS (
            SELECT department, AVG(salary) AS avg_bottom_salary
            FROM ranked_emp
            WHERE pct_rank <= 0.10
            GROUP BY department
        )
        SELECT
            t.department,
            t.avg_top_salary - b.avg_bottom_salary AS polarization_index
        FROM top_earners t
        JOIN bottom_earners b
          ON t.department = b.department
        ORDER BY t.department
        """,
    ),
    (
        "20. The Executive Master Summary",
        """
        WITH dept_avg AS (
            SELECT department, AVG(salary) AS avg_salary
            FROM employees
            GROUP BY department
        ),
        ranked_salaries AS (
            SELECT
                department,
                salary,
                ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary) AS rn,
                COUNT(*) OVER (PARTITION BY department) AS total_count
            FROM employees
        ),
        median_salary AS (
            SELECT
                department,
                AVG(salary) AS median_salary
            FROM ranked_salaries
            WHERE rn IN ((total_count + 1) / 2, (total_count + 2) / 2)
            GROUP BY department
        ),
        staff_rank AS (
            SELECT
                e.employee_id,
                e.first_name,
                e.last_name,
                e.department,
                e.salary,
                da.avg_salary AS department_average_salary,
                RANK() OVER (PARTITION BY e.department ORDER BY e.salary DESC) AS department_rank
            FROM employees e
            JOIN dept_avg da ON da.department = e.department
        )
        SELECT
            sr.first_name,
            sr.last_name,
            sr.department,
            sr.salary,
            sr.department_average_salary,
            sr.department_rank,
            CASE
                WHEN sr.salary >= ms.median_salary THEN 'Above'
                ELSE 'Below'
            END AS salary_status
        FROM staff_rank sr
        JOIN median_salary ms ON ms.department = sr.department
        ORDER BY sr.department, sr.department_rank, sr.salary DESC
        """,
    ),
]

# %%
def execute_question_set():
    conn = get_connection(use_database=True)
    try:
        for idx, (title, query) in enumerate(QUERIES, start=1):
            print(f"\n{'=' * 100}")
            print(title)
            print(f"{'=' * 100}\n")

            cursor = conn.cursor()
            try:
                cursor.execute(query)
                rows = cursor.fetchall()
                column_names = [col[0] for col in cursor.description]

                print("SQL raw tuples:")
                for row in rows:
                    print(row)

                df = pd.read_sql(query, conn)
                print("\nPandas verification:")
                print(df)
                print("\nColumn names:", list(df.columns))
                print("Row count from cursor:", len(rows))
                print("Row count from pandas:", len(df))
                print("Row count matches:", len(rows) == len(df))
            finally:
                cursor.close()
    finally:
        conn.close()


def main():
    create_database_and_table()
    ingest_csv_to_mysql()
    execute_question_set()


if __name__ == "__main__":
    main()

