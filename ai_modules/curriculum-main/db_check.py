# sample_usage.py
from util.dbClient import DbClient

if __name__ == "__main__":
    db = DbClient()
    print("▶ DB 연결 준비:")
    print(f"   HOST = {db.host}")
    print(f"   PORT = {db.port}")
    print(f"   USER = {db.user}")
    print(f"   DATABASE = {db.database}")
    print("─────────────────────────")

    db.connect()
    table_name = "jbnu_tool_list"

    try:

        print("\n--- Data in `jbnu_tool_list` ---")
        # 데이터 내용 출력
        data_rows = db.execute_query(f"SELECT * FROM {table_name};")
        for dr in data_rows:
            print(dr)
    finally:
        db.close()
