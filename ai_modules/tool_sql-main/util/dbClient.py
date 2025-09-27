import os
import pymysql
from dotenv import load_dotenv

load_dotenv()  # 컨테이너/로컬 환경 변수 로드


class DbClient:

    def __init__(self):
        # 환경변수 우선, 없으면 합리적인 기본값 사용
        self.host = os.getenv("DB_HOST", "210.117.181.113")
        self.port = int(os.getenv("DB_PORT", "3313"))
        self.user = os.getenv("DB_USER", "root")

        # VECTOR_DB_PASSWORD 우선, 없으면 DB_PASSWORD 사용
        self.password = os.getenv("DB_PASSWORD") 
        # 기본 DB는 운영에서 사용하는 'nll'
        self.database = os.getenv("DB_NAME", "nll_third")
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
                    cursorclass=pymysql.cursors.DictCursor,
                    charset='utf8mb4'  # UTF-8 인코딩 명시
                )
                print(f"✅ 벡터 DB 연결 성공: {self.host}:{self.port}/{self.database}")
            except pymysql.MySQLError as e:
                print(f"❌ 벡터 DB 연결 실패: {self.host}:{self.port}/{self.database} - {e}")
                self.connection = None

    def ensure_connection(self):
        """연결 상태 확인 및 재연결"""
        if not self.connection or not self.connection.open:
            print("🔄 DB 연결이 끊어져 재연결 시도...")
            self.connection = None
            self.connect()
        return self.connection is not None

    # R
    def execute_query(self, query, params=None):
        if not self.ensure_connection():
            return None
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
        except pymysql.MySQLError:
            return None

    # CUD
    def execute_update(self, query, params=None):
        if not self.ensure_connection():
            return False
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                self.connection.commit()
                return True
        except pymysql.MySQLError:
            if self.connection:
                self.connection.rollback()
            return False

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None
