# %%
import csv 
import mysql.connector 
from mysql.connector import Error 
 
def ingest_csv_to_mysql(): 
    try: 
        # 1. Connect to MySQL Server 
        conn = mysql.connector.connect( 
            host="********", 
            user="******", 
            password="*******", 
            database="company_db" # Ensure this database is created beforehand 
        ) 
        cursor = conn.cursor() 
 
        # 2. Create the Table 
        cursor.execute("DROP TABLE IF EXISTS employees;") 
        create_table_query = """ 
        CREATE TABLE employees ( 
            employee_id INT AUTO_INCREMENT PRIMARY KEY, 
            first_name VARCHAR(50) NOT NULL, 
            last_name VARCHAR(50) NOT NULL, 
            department VARCHAR(50) NOT NULL, 
            salary DECIMAL(10, 2) NOT NULL, 
            hire_date DATE NOT NULL, 
            Day_of_Week VARCHAR(15), 
            Day_of_month INT, 
            Month VARCHAR(15), 
            Year INT 
        ); 
        """ 
        cursor.execute(create_table_query) 
        print("Table 'employees' created successfully.") 
 
        # 3. Read CSV and Ingest 
        with open("employees_data.csv", mode="r") as file: 
            csv_reader = csv.reader(file) 
            header = next(csv_reader) # Skip header row 
             
            insert_query = """ 
            INSERT INTO employees ( 
                first_name, last_name, department, salary,  
                hire_date, Day_of_Week, Day_of_month, Month, Year 
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s); 
            """ 
             
            # Batch insert rows 
            records_to_insert = [tuple(row) for row in csv_reader] 
            cursor.executemany(insert_query, records_to_insert) 
            conn.commit() 
             
            print(f"Successfully ingested {cursor.rowcount} records into the database.") 
 
    except Error as e: 
        print(f"Error: {e}") 
    finally: 
        if conn.is_connected(): 
            cursor.close() 
            conn.close() 
 
if __name__ == "__main__": 
    ingest_csv_to_mysql() 


