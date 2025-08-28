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
        data_rows = db.execute_query(f"SELECT * FROM {table_name};")
        for t in data_rows:
            result = {
                "tool_name": t["tool_name"],
                "tool_description": t["description"],
                "api_body": t["api_body"],
                "api_url": t["api_url"]
            }
            print(result)
    finally:
        db.close()
