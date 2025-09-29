import pymysql

class DatabaseHandler:
    def __init__(self, host, port, user, password, database, charset):
        self.db_config = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "database": database,
            "charset": charset
        }
        self.connection = None
        self.cursor = None

    def connect(self):
        """Establish a database connection using provided configurations."""
        try:
            self.connection = pymysql.connect(**self.db_config)
            self.cursor = self.connection.cursor()
        except Exception as e:
            print('Error connecting to database:', e)
            raise e

    def execute_query(self, query, params=None):
        """Execute a custom SQL query and return results."""
        try:
            if not self.connection or not self.cursor:
                raise Exception("Database connection is not established.")

            self.cursor.execute(query, params)
            columns = [col[0] for col in self.cursor.description]
            rows = self.cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
        except pymysql.MySQLError as e:
            print(f"Error executing query: {e}")
            raise

    def fetch_all_departments(self):
        """Fetch all department IDs and names from the department table."""
        try:
            if not self.connection or not self.cursor:
                raise Exception("Database connection is not established.")

            sql_query = """
            SELECT 
                id AS department_id,
                name AS department_name
            FROM jbnu_department
            ORDER BY id;
            """
            self.cursor.execute(sql_query)
            columns = [col[0] for col in self.cursor.description]
            rows = self.cursor.fetchall()
            print(f"{len(rows)} departments fetched.")
            return [dict(zip(columns, row)) for row in rows]

        except pymysql.MySQLError as e:
            print(f"Error executing query: {e}")
            raise

    def fetch_depart_goal(self):
        """
        Fetch course information for 3rd and 4th year students including department and college info.
        """
        try:
            if not self.connection or not self.cursor:
                raise Exception("Database connection is not established.")

            sql_query = """
                SELECT
                    jc.id AS class_id,
                    jc.name AS class_name,
                    jc.description AS class_description,
                    jc.student_grade AS class_student_grade,
                    jd.name AS department_name,
                    jd.id AS department_id,
                    jco.name AS college_name
                FROM jbnu_class jc
                JOIN jbnu_department jd ON jc.department_id = jd.id
                JOIN jbnu_college jco ON jd.college_id = jco.id
                WHERE jc.student_grade IN (3, 4)
                ORDER BY jc.id;
            """
            self.cursor.execute(sql_query)
            columns = [col[0] for col in self.cursor.description]
            rows = self.cursor.fetchall()
            results = [dict(zip(columns, row)) for row in rows]
            return results

        except pymysql.MySQLError as e:
            print(f"Error executing query: {e}")
            raise

    def fetch_classes_by_department(self, department_id):
        """
        Fetch classes for a given department ID.
        """
        try:
            if not self.connection or not self.cursor:
                raise Exception("Database connection is not established.")

            sql_query = """
                SELECT
                    jc.id,
                    jc.name,
                    jc.description,
                    jc.student_grade,
                    jd.name,
                    jco.name
                FROM jbnu_class jc
                JOIN jbnu_department jd ON jc.department_id = jd.id
                JOIN jbnu_college jco ON jd.college_id = jco.id
                WHERE jc.student_grade IN (3, 4)
                ORDER BY jc.id;
            """
            self.cursor.execute(sql_query, (department_id,))
            columns = [col[0] for col in self.cursor.description]
            rows = self.cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]

        except pymysql.MySQLError as e:
            print(f"Error executing query: {e}")
            raise

    def fetch_classes_info_by_department(self):
        """
        Fetch detailed course information, filtering out specific colleges.
        """
        try:
            if not self.connection or not self.cursor:
                raise Exception("Database connection is not established.")

            sql_query = """
                SELECT 
                    jc.id AS class_id,
                    jc.name AS class_name,
                    jc.description AS class_description,
                    jc.student_grade AS student_grade,
                    jc.prerequisite AS R_prerequisite,
                    jc.semester AS semester,
                    jd.name AS department_name,
                    jd.id AS department_id,
                    jco.name AS college_name
                FROM jbnu_class jc
                JOIN jbnu_department jd ON jc.department_id = jd.id
                JOIN jbnu_college jco ON jd.college_id = jco.id
                WHERE jco.name NOT IN ('사범대학', '예술대학', '글로벌융합대학')
                ORDER BY jc.student_grade, jc.id;
            """
            self.cursor.execute(sql_query)
            columns = [col[0] for col in self.cursor.description]
            rows = self.cursor.fetchall()
            results = [dict(zip(columns, row)) for row in rows]
            return results

        except pymysql.MySQLError as e:
            print(f"Error executing query: {e}")
            raise

    def fetch_prerequisites(self, class_id):
        """
        Fetch prerequisite classes for a given class ID.
        """
        try:
            if not self.connection or not self.cursor:
                raise Exception("Database connection is not established.")

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
            self.cursor.execute(sql_query, (class_id,))
            columns = [col[0] for col in self.cursor.description]
            rows = self.cursor.fetchall()
            results = [dict(zip(columns, row)) for row in rows]
            return results

        except pymysql.MySQLError as e:
            print(f"Error executing query: {e}")
            raise

    def fetch_postrequisites(self, department_name, class_name):
        """
        Fetch postrequisite courses for a specific course in a given department.
        
        Args:
            department_name (str): Name of the department
            class_name (str): Target class name for which to find postrequisites
        
        Returns:
            list: List of postrequisite courses as dictionaries
        """
        try:
            if not self.connection or not self.cursor:
                raise Exception("Database connection is not established.")

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
            AND main_class.prerequisite REGEXP CONCAT('(^|,\\s*)', %s, '(\\s*,|$)') 
            ORDER BY main_class.student_grade, main_class.id;
            """

            self.cursor.execute(sql_query, (department_name, class_name))
            columns = [col[0] for col in self.cursor.description]
            rows = self.cursor.fetchall()
            results = [dict(zip(columns, row)) for row in rows]
            return results

        except pymysql.MySQLError as e:
            print(f"Error executing query: {e}")
            raise

    def close(self):
        """Close database connection and cursor."""
        if self.connection:
            self.cursor.close()
            self.connection.close()
            self.connection = None
            self.cursor = None
        else:
            raise Exception("Database connection not established.")
