import os
import pickle
import numpy as np
import faiss
import logging
from typing import List, Dict, Optional
import openai
import os
        
logger = logging.getLogger(__name__)


class ClassRetriever:
    def __init__(self, db_client=None, data_path="./data"):
        self.db_client = db_client
        self.data_path = data_path
        self.index = None
        self.lookup_index = None
        self.is_loaded = False

    def load_data(self):
    
        class_file = os.path.join(self.data_path, "class_Dataset.pkl")
        try:
            with open(class_file, "rb") as f:
                data = pickle.load(f)
                embeddings = data["embeddings"]
                embeddings_array = np.array(embeddings, dtype=np.float32)
                self.lookup_index = data["lookup_index"]

            # FAISS 인덱스 생성
            embeddings_array /= np.linalg.norm(embeddings_array, axis=1, keepdims=True)  # 정규화
            dim = embeddings_array.shape[1]
            self.index = faiss.IndexFlatIP(dim)
            self.index.add(embeddings_array)

            self.is_loaded = True

        except Exception as e:
            logger.error(f"과목 데이터 로드 실패: {e}")
            raise

    def get_query_embedding(self, query: str) -> np.ndarray:
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        response = client.embeddings.create(
            input=query,
            model='text-embedding-3-large'
        )

        return np.array(response.data[0].embedding, dtype=np.float32)


    def search_class_by_departments(self, query: str, department_list: List[Dict], exclude_class_ids: List[int] = None) -> Dict[str, List[Dict]]:
        """특정 학과들에서만 과목 검색 - 효율적인 버전"""
        if not self.is_loaded:
            self.load_data()

        # 쿼리 임베딩 생성
        query_embedding = self.get_query_embedding(query)
        query_emb = query_embedding.reshape(1, -1)
        query_emb /= np.linalg.norm(query_emb, axis=1, keepdims=True)

        # 학과 ID 추출
        selected_dept_ids = {dept.get('department_id') for dept in department_list}

        # 학과별 결과 저장
        results_by_dept = {}
        for dept in department_list:
            results_by_dept[dept.get("department_name", "Unknown")] = []

        # 한 번에 모든 과목을 확인하고 해당 학과에 속하는 것만 필터링
        for i, class_info in enumerate(self.lookup_index):
            # 지정된 학과에 속하는지 확인
            if class_info.get("department_id") not in selected_dept_ids:
                continue

            # 제외할 과목 ID가 있다면 스킵
            if exclude_class_ids and class_info.get("class_id") in exclude_class_ids:
                continue

            # 해당 과목의 임베딩과 쿼리 간 유사도 계산
            class_emb = self.index.reconstruct(i).reshape(1, -1)
            similarity = np.dot(query_emb, class_emb.T)[0, 0]

            # 해당 학과 결과에 추가
            dept_name = class_info.get("department_name", "Unknown")
            if dept_name in results_by_dept:
                results_by_dept[dept_name].append({
                    "class_id": class_info.get("class_id"),
                    "class_name": class_info.get("class_name", "Unknown"),
                    "department_id": class_info.get("department_id"),
                    "department_name": dept_name,
                    "student_grade": class_info.get("student_grade", "Unknown"),
                    "semester": class_info.get("semester", "Unknown"),
                    "prerequisite": class_info.get("prerequisite", ""),
                    "description": class_info.get("text", ""),
                    "score": float(similarity)
                })

        # 각 학과별로 점수순 정렬하고 상위 count개만 유지
        for dept_name in results_by_dept:
            results_by_dept[dept_name].sort(key=lambda x: x["score"], reverse=True)
            results_by_dept[dept_name] = results_by_dept[dept_name]
            print(f"🔍 {dept_name} 검색 결과: {len(results_by_dept[dept_name])}개")

        return results_by_dept
