from langchain_community.utilities import SQLDatabase
from dotenv import load_dotenv
import os

load_dotenv()

db_host = os.getenv("DB_HOST")
db_password = os.getenv("DB_PASSWORD")

class DbClient:
    def __init__(self):
        self.host = db_host
        self.port = 3311
        self.user = "root"
        self.password = db_password
        self.database = "nll"
        self.mysql_uri = (
            f"mysql+pymysql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )

        # pool_pre_ping=True 로 “MySQL server has gone away” 방지
        self.db = SQLDatabase.from_uri(
            self.mysql_uri,
            engine_args={"pool_pre_ping": True}
        )

    def execute_query(self, query: str):
        try:
            result = self.db.run(query)
            return result
        except Exception as e:
            print(f"Error reading data: {e}")
            return None
