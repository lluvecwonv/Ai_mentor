
import pymysql
from dotenv import load_dotenv
import os

load_dotenv()  # .env 파일 자동 로드

db_host = os.getenv("DB_HOST")
db_port = int(os.getenv("DB_PORT", "3311"))  # 기본값 3311
db_user = os.getenv("DB_USER", "root")  # 기본값 root
db_name = os.getenv("DB_NAME", "nll_third")  # 기본값 nll_third
db_password = os.getenv("DB_PASSWORD")

class DbClient():

    def __init__(self):
        self.host = db_host
        self.port = db_port
        self.user = db_user
        self.password = db_password
        self.database = db_name
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
