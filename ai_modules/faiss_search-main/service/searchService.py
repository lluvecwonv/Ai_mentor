import faiss
import numpy as np
import logging
from typing import Dict, List
from util.langchainLlmClient import LangchainLlmClient
from util.utils import load_prompt, extract_sql_from_response, prepare_vectors

logger = logging.getLogger(__name__)

class SearchService:
    """간소화된 하이브리드 검색: SQL → FAISS"""

    def __init__(self, db_client):
        self.llm_client = LangchainLlmClient()
        self.db_client = db_client 

    def search_hybrid(self, query_text: str, count: int = 10) -> List[Dict]:
        logger.info(f"검색 시작: '{query_text}'")
        # 1. SQL로 관련 강의 필터링
        filtered_courses = self._get_filtered_courses(query_text)

        # 2. 벡터 검색
        results = self._vector_search(query_text, filtered_courses, count)

        logger.info(f"검색 완료: {len(results)}개 결과")
        return results

    def _get_filtered_courses(self, query_text: str) -> List[Dict]:
        """LLM SQL 생성 + 강의 필터링 (통합)"""
      
        if not self.db_client or not self.db_client.ensure_connection():
            return []

        # 1. LLM으로 SQL 생성
        prompt = load_prompt("sql_prefilter_generator")
        full_prompt = f"{prompt}\n\n사용자 쿼리: {query_text}"
        response = self.llm_client.get_llm().invoke(full_prompt)

        sql_query = extract_sql_from_response(response.content)

        # 2. SQL 실행
        with self.db_client.connection.cursor() as cursor:
            logger.info(f"SQL 생성됨: {sql_query}")
            cursor.execute(sql_query)
        return cursor.fetchall()

    def _vector_search(self, query_text: str, courses: List[Dict], count: int) -> List[Dict]:

        vectors, metadata = prepare_vectors(courses)
        if not vectors:
            return []

        # FAISS 검색 - LangChain 임베딩 사용
        query_vector = np.array(
            self.llm_client.get_embeddings().embed_query(query_text),
            dtype=np.float32
        )
        if query_vector is None:
            return []

        # 인덱스 생성 및 검색
        vectors_array = np.array(vectors)
        index = faiss.IndexFlatIP(vectors_array.shape[1])
        index.add(vectors_array)

        # 쿼리 벡터 정규화
        query_vector = query_vector.reshape(1, -1).astype(np.float32)
        query_vector = query_vector / np.linalg.norm(query_vector)

        # 검색 실행
        scores, indices = index.search(query_vector, min(count, len(vectors)))

        # 결과 구성
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(metadata) and scores[0][i] > 0:
                result = metadata[idx].copy()
                result['similarity_score'] = float(scores[0][i])
                results.append(result)

        return results[:count]

  