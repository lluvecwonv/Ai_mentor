import os
import pickle
import numpy as np
import faiss
import logging
from typing import List, Dict, Optional
from ..open_ai import llm_select_departments

logger = logging.getLogger(__name__)


class DepartmentRetriever:
    """간소화된 학과 검색기 - 로드 + 검색만"""

    def __init__(self, db_client=None, data_path="./data"):
        self.db_client = db_client
        self.data_path = data_path
        self.index = None
        self.lookup_index = None
        self.is_loaded = False

    def load_data(self):
        """저장된 학과 데이터 로드"""
        if self.is_loaded:
            return

        dept_file = os.path.join(self.data_path, "department_Dataset.pkl")

        if not os.path.exists(dept_file):
            raise FileNotFoundError(f"학과 데이터 파일을 찾을 수 없습니다: {dept_file}")

        try:
            with open(dept_file, "rb") as f:
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
            logger.error(f"학과 데이터 로드 실패: {e}")
            raise

    def get_query_embedding(self, query: str) -> np.ndarray:
        """쿼리 임베딩 생성 (OpenAI API 사용)"""
        import openai
        import os

        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        response = client.embeddings.create(
            input=query,
            model='text-embedding-3-large'
        )

        return np.array(response.data[0].embedding, dtype=np.float32)

    def search_department(self, query: str, count: int = 10, threshold_diff: float = 0.015) -> List[Dict]:
        """하이브리드 검색"""
        if not self.is_loaded:
            self.load_data()

        # 쿼리 임베딩 생성
        query_embedding = self.get_query_embedding(query)
        query_emb = query_embedding.reshape(1, -1)
        query_emb /= np.linalg.norm(query_emb, axis=1, keepdims=True)

        # FAISS 검색으로 후보 학과 찾기
        similarities, indices = self.index.search(query_emb, k=count * 2)  # 더 많은 후보 확보

        # 1차 필터링: 임계값 기반
        candidate_depts = []
        prev_score = None

        for i, (idx, score) in enumerate(zip(indices[0], similarities[0])):
            if i >= 2 and prev_score is not None and abs(prev_score - score) >= threshold_diff:
                break

            dept_info = self.lookup_index[idx]
            candidate_depts.append({
                "department_id": dept_info["department_id"],
                "department_name": dept_info.get("department_name", "Unknown"),
                "score": float(score),
                "text": dept_info.get("text", "")
            })
            prev_score = score

        # 2차 선택: LLM이 쿼리와 가장 관련된 학과 선택
        selected_depts = llm_select_departments(query, candidate_depts, count)

        # 최종 결과 포맷
        results = []
        for dept in selected_depts:
            results.append({
                "department_id": dept["department_id"],
                "department_name": dept["department_name"],
                "course_name": f"{dept['department_name']} 대표과목",
                "score": dept["score"]
            })

        return results