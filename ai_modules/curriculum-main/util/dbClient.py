
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

    def fetch_prerequisites(self, class_id):
        """
        Fetch prerequisite classes for a given class ID.
        """
        try:
            if not self.connection:
                self.connect()

            sql_query = """
             SELECT
                prereq.id AS class_id,
                prereq.name AS class_name,
                prereq.student_grade,
                prereq.semester,
                prereq.description,
                prereq.language,
                prereq.prerequisite AS prerequisite,
                jd.name AS department_name,
                jco.name AS college_name
            FROM jbnu_class main_class
            JOIN jbnu_class prereq
                ON FIND_IN_SET(TRIM(prereq.name), REPLACE(main_class.prerequisite, ' ', '')) > 0
                AND main_class.department_id = prereq.department_id
            JOIN jbnu_department jd ON prereq.department_id = jd.id
            JOIN jbnu_college jco ON jd.college_id = jco.id
            WHERE main_class.id = %s
            ORDER BY prereq.student_grade, prereq.id;
            """

            with self.connection.cursor() as cursor:
                cursor.execute(sql_query, (class_id,))
                rows = cursor.fetchall()
                return rows

        except pymysql.MySQLError as e:
            print(f"Error executing fetch_prerequisites: {e}")
            return []

    def fetch_postrequisites(self, department_name, class_name):
        """
        Fetch postrequisite courses for a specific course in a given department.
        """
        try:
            if not self.connection:
                self.connect()

            sql_query = """
            SELECT
                main_class.id AS class_id,
                main_class.name AS class_name,
                main_class.student_grade,
                main_class.semester,
                main_class.description,
                main_class.language,
                main_class.prerequisite AS prerequisite,
                jd.id AS department_id,
                jd.name AS department_name,
                jco.name AS college_name
            FROM jbnu_class main_class
            JOIN jbnu_department jd ON main_class.department_id = jd.id
            JOIN jbnu_college jco ON jd.college_id = jco.id
            WHERE jd.name = %s
            AND main_class.prerequisite REGEXP CONCAT('(^|,\\\\s*)', %s, '(\\\\s*,|$)')
            ORDER BY main_class.student_grade, main_class.id;
            """

            with self.connection.cursor() as cursor:
                cursor.execute(sql_query, (department_name, class_name))
                rows = cursor.fetchall()
                return rows

        except pymysql.MySQLError as e:
            print(f"Error executing fetch_postrequisites: {e}")
            return []

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None
