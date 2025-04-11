
import pymysql

class DbClient():

    def __init__(self):
        self.host = "210.117.181.113"
        self.port = 3313
        self.user = "root"
        self.password = "vmfhaltmskdls123"
        self.database = "nll"
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
            except pymysql.MySQLError:
                pass

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