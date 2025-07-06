from util.dbClient import DbClient


db = DbClient()
db.connect()
table_name="jbnu_class" 
try:
    rows = db.execute_query(f"DESCRIBE {table_name};")
    print(f"--- Structure of `{table_name}` ---")
    for row in rows:
        # row keys: Field, Type, Null, Key, Default, Extra
        print(f"{row['Field']:20} {row['Type']:20} NULL={row['Null']:3} KEY={row['Key']:3} DEFAULT={row['Default']} EXTRA={row['Extra']}")
finally:
    db.close()


