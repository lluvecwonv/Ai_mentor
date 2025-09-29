from typing import Dict, Any
from utils.utils import load_config, load_data, load_embeddings, build_faiss_index, get_query_embedding

class MappingService:
    def __init__(self):
        self.keyword_mapping = load_config()  # 중첩 딕셔너리
        self.departments_data = load_data()   # 학과 정보 리스트
        self.embeddings = load_embeddings()
        self.faiss_index = build_faiss_index(self.embeddings)



    def get_department_description(self, department_name: str) -> Dict[str, Any]:
        """학과명으로 학과 설명을 찾는 함수"""
        for dept in self.departments_data:
            if dept.get("학과") == department_name:
                return {
                    "department_name": department_name,
                    "description": dept.get("학과설명", "학과 설명을 찾을 수 없습니다.")
                }

        return {
            "department_name": department_name,
            "description": "해당 학과를 찾을 수 없습니다."
        }

    def find_department_with_description(self, query: str) -> Dict[str, Any]:
        """학과를 찾고 설명도 함께 반환하는 통합 함수"""
        # 1. 키워드 매핑 먼저 시도
        for category, mappings in self.keyword_mapping.items():
            for keyword, dept_name in mappings.items():
                if keyword in query.lower():
                    description_info = self.get_department_description(dept_name)
                    return {
                        "departments": [description_info]
                    }

        # 2. FAISS 벡터 검색
        query_embedding = get_query_embedding(query)
        if query_embedding is not None:
            scores, indices = self.faiss_index.search(query_embedding.reshape(1, -1), 1)
            best_idx = indices[0][0]
            best_dept = self.departments_data[best_idx]
            dept_name = best_dept["학과"]
            description_info = self.get_department_description(dept_name)
            return {
                "departments": [description_info]
            }

        return {"departments": []}