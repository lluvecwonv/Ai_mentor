
import pymysql
from dotenv import load_dotenv
import os

load_dotenv()  # .env 파일 자동 로드

db_host = os.getenv("DB_HOST")
db_password = os.getenv("DB_PASSWORD")

class DbClient():

    def __init__(self):
        self.host = db_host
        self.port = 3312
        self.user = "root"
        self.password = db_password
        self.database = "nll_third"
        self.connection = None

    def connect(self):
        if self.connection is None:
            try:
                self.connection = pymysql.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    database=self.database,
                    cursorclass=pymysql.cursors.DictCursor
                )
                print("✅ DB 연결 성공")
            except pymysql.MySQLError as e:
                print(f"❌ DB 연결 실패: {e}")
                self.connection = None

    # R
    def execute_query(self, query, params=None):
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
        except pymysql.MySQLError:
            return None

    # CUD
    def execute_update(self, query, params=None):
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                self.connection.commit()
        except pymysql.MySQLError:
            self.connection.rollback()

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None
