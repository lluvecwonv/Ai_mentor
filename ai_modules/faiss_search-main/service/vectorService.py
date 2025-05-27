import faiss
import numpy as np

import ast

from util.dbClient import DbClient


class VectorService():
    
    def __init__(self):
        self.dbClient = DbClient()
        self.dbClient.connect()

        self.dim = 1536
        self.index = faiss.IndexFlatIP(self.dim)
        self.keys = []  # 과목명 키 리스트
        self.vectors = []  # 벡터 리스트
        self.load_embedding_to_faiss()

    def load_embedding_to_faiss(self) -> None:

        load_embedding_sql = "SELECT * FROM jbnu_class"
        embedding_list = self.dbClient.execute_query(load_embedding_sql)

        for i, row in enumerate(embedding_list):

            name = row["name"]
            vector_target = row["vector"]
            print(f"{i}, {name}")

            vector_target = ast.literal_eval(vector_target)
            vector_target = np.array(vector_target, dtype=np.float32)
            vector_target /= np.linalg.norm(vector_target)  # 코사인 유사도를 위한 정규화

            self.keys.append(name)
            self.vectors.append(vector_target)

        self.vectors = np.array(self.vectors).astype(np.float32)
        self.index.add(self.vectors)

        self.dbClient.close()


    def search_vector(self, k, key) -> list:
        
        if key not in self.keys:
            raise ValueError(f"키 '{key}'에 해당하는 벡터가 없습니다.")

        idx = self.keys.index(key)
        vector = self.vectors[idx].reshape(1, -1)

        # 벡터를 정규화 (내적 기반의 코사인 유사도 계산을 위한 정규화)
        vector /= np.linalg.norm(vector)

        scores, indices = self.index.search(vector, k)

        return [self.keys[i] for i in indices[0]]
