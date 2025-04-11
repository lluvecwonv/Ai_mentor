# 1536 차원

import pymysql

from openai import OpenAI


def db_connect1():
    host = "your_host"
    port = 3311
    user = "root"
    password = "your_password"
    database = "nll"

    connect = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset='utf8mb4'
    )

    return connect

def db_connect2():
    host = "your_host"
    port = 3313
    user = "root"
    password = "your_password"
    database = "nll"

    connect = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset='utf8mb4'
    )

    return connect


def main() -> None:

    aiClient = OpenAI(api_key="your_api_code")

    
    rawDB = db_connect1()
    cursor1 = rawDB.cursor()
    vectorDB = db_connect2()
    cursor2 = vectorDB.cursor()
    
    get_query = "SELECT * FROM jbnu_class"
    cursor1.execute(get_query)
    
    for i, row in enumerate(cursor1.fetchall()):

        print(i)

        name = row[3]
        description = row[16]

        response = aiClient.embeddings.create(
            input=description,
            model="text-embedding-3-small"
        )
        embedding = response.data[0].embedding

        insert_query = f"INSERT INTO jbnu_class (name, vector) VALUES ('{name}', '{embedding}')"
        cursor2.execute(insert_query)
        vectorDB.commit()

    # 커넥션 끊기
    rawDB.close()
    vectorDB.close()


if __name__ == "__main__":
    main()
