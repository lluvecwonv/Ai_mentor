from util.dbClient import DbClient

db = DbClient()
db.connect()



# (선택) 결과 확인
rows = db.execute_query("""
    SELECT tool_name, description, api_body, api_url
    FROM jbnu_tool_list;
""")
for r in rows:
    print(r)

db.close()
