# jbnu_department 데이터 삽입 스크립트 
# 도현

import mysql.connector
from openpyxl import load_workbook
from dotenv import load_dotenv
import os

load_dotenv()  # .env 파일 자동 로드

db_host = os.getenv("DB_HOST")
db_password = os.getenv("DB_PASSWORD")

host = db_host
port = '3311'
database = 'nll'
user = 'root'
password = db_password

connection = mysql.connector.connect(host=host, port=port, database=database, user=user, password=password)

cursor = connection.cursor()

wb = load_workbook('department_list.xlsx')

ws = wb.active

for row in ws.rows:
    row_values = [cell.value for cell in row]

    select_query = "select id from jbnu_college where name = %s"
    select_data = (row_values[0],)

    cursor.execute(select_query, select_data)
    rows = cursor.fetchall()
    college_id = rows[0][0]
    print(college_id)


    insert_query = 'INSERT INTO jbnu_department (name, description, college_id) VALUES (%s, %s, %s)'
    insert_data = (row_values[1], 'none', college_id,)


    cursor.execute(insert_query, insert_data)
    connection.commit()

connection.close()
