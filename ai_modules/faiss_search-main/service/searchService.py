import faiss
import numpy as np
import ast
import logging
from typing import Dict, List, Optional
from openai import OpenAI
from service.queryService import QueryService

logger = logging.getLogger(__name__)


class SearchService:
    """간단한 하이브리드 검색: SQL → FAISS"""

    def __init__(self, openai_client: OpenAI, db_client):
        self.llm_client = openai_client
        self.db_client = db_client
        self.query_service = QueryService(openai_client, db_client)

    def generate_embedding(self, text: str) -> Optional[np.ndarray]:
        """텍스트를 OpenAI 임베딩으로 변환"""
        try:
            response = self.llm_client.embeddings.create(
                model="text-embedding-ada-002",
                input=text,
                encoding_format="float"
            )
            embedding = np.array(response.data[0].embedding, dtype=np.float32)
            return embedding
        except Exception as e:
            logger.error(f"❌ [SearchService] 임베딩 생성 실패: {e}")
            return None

    def search_hybrid(self, query_text: str, count: int = 10) -> List[Dict]:
        """간단한 하이브리드 검색: SQL → FAISS (SQL 실패시 전체 DB 검색)"""
        logger.info(f"🚀 [SearchService] 검색 시작: '{query_text}'")

        # 1. SQL로 관련 강의 필터링
        filtered_courses = self.query_service.get_filtered_courses(query_text)

        if not filtered_courses:
            logger.warning("⚠️ [SearchService] SQL 필터링 결과 없음 - 전체 DB에서 벡터 검색 실행")
            # SQL 필터링이 실패하면 전체 데이터베이스에서 벡터 검색
            filtered_courses = self._get_all_courses_with_vectors()
            if not filtered_courses:
                logger.error("❌ [SearchService] 전체 DB 조회 실패")
                return []
            logger.info(f"📊 [SearchService] 전체 DB 검색: {len(filtered_courses)}개 강의")
        else:
            logger.info(f"📊 [SearchService] SQL 필터링 결과: {len(filtered_courses)}개 강의")

        # 2. 필터링된 강의로 벡터 검색
        results = self._search_in_filtered_courses(query_text, filtered_courses, count)

        logger.info(f"✅ [SearchService] 검색 완료: {len(results)}개 결과")
        return results

    def _search_in_filtered_courses(self, query_text: str, filtered_courses: List[Dict], count: int) -> List[Dict]:
        """필터링된 강의들로만 벡터 검색"""
        logger.info(f"🎯 [SearchService] 벡터 검색 시작: {len(filtered_courses)}개 강의")

        # 1. 벡터 데이터 준비
        vectors = []
        metadata = []

        for course in filtered_courses:
            try:
                vector_str = course.get('vector', '[]')
                if not vector_str or vector_str == '[]':
                    continue

                vector = ast.literal_eval(vector_str)
                vector_array = np.array(vector, dtype=np.float32)

                # 정규화
                norm = np.linalg.norm(vector_array)
                if norm > 0:
                    vector_array = vector_array / norm

                vectors.append(vector_array)
                metadata.append({
                    'id': course['id'],
                    'name': course['name'],
                    'department': course.get('department_full_name', course.get('department', '')),
                    'professor': course.get('professor', '정보없음'),
                    'credits': course.get('credits', 0),
                    'schedule': course.get('schedule', '정보없음'),
                    'location': course.get('location', '정보없음'),
                    'delivery_mode': course.get('delivery_mode', '정보없음'),
                    'gpt_description': course.get('gpt_description', ''),
                    'description': course.get('gpt_description', ''),
                })

            except Exception as e:
                logger.warning(f"⚠️ [SearchService] 벡터 파싱 실패: {course.get('name', 'Unknown')} - {e}")
                continue

        if not vectors:
            logger.error("❌ [SearchService] 유효한 벡터 데이터 없음")
            return []

        logger.info(f"✅ [SearchService] 유효한 벡터: {len(vectors)}개")

        # 2. FAISS 인덱스 생성 및 검색
        try:
            vectors = np.array(vectors)
            logger.info(f"🔧 [SearchService] 벡터 배열 생성: shape={vectors.shape}")

            index = faiss.IndexFlatIP(vectors.shape[1])
            index.add(vectors)
            logger.info(f"🔧 [SearchService] FAISS 인덱스 생성 완료: dimension={vectors.shape[1]}")

            # 쿼리 벡터 생성
            logger.info(f"🔧 [SearchService] 쿼리 임베딩 생성 시작: '{query_text}'")
            query_vector = self.generate_embedding(query_text)
            if query_vector is None:
                logger.error("❌ [SearchService] 쿼리 임베딩 생성 실패")
                return []

            logger.info(f"🔧 [SearchService] 쿼리 벡터 생성 완료: shape={query_vector.shape}")
            query_vector = query_vector.reshape(1, -1).astype(np.float32)
            query_vector = query_vector / np.linalg.norm(query_vector)
            logger.info(f"🔧 [SearchService] 쿼리 벡터 정규화 완료: shape={query_vector.shape}")

            # 검색
            search_count = min(count, len(vectors))
            logger.info(f"🔧 [SearchService] FAISS 검색 시작: search_count={search_count}")
            scores, indices = index.search(query_vector, search_count)
            logger.info(f"🔧 [SearchService] FAISS 검색 완료: scores={scores[0][:3]}, indices={indices[0][:3]}")

            # 결과 구성
            results = []
            for i, idx in enumerate(indices[0]):
                if idx < len(metadata) and scores[0][i] > 0:
                    result = metadata[idx].copy()
                    result['similarity_score'] = float(scores[0][i])
                    result['similarity'] = float(scores[0][i])
                    results.append(result)
                    logger.info(f"🔧 [SearchService] 결과 {i+1}: {result['name']}, score={scores[0][i]:.4f}")

            logger.info(f"🎯 [SearchService] 벡터 검색 완료: {len(results)}개 결과")
            return results[:count]

        except Exception as e:
            logger.error(f"❌ [SearchService] 벡터 검색 실패: {str(e)}")
            import traceback
            logger.error(f"❌ [SearchService] 상세 오류: {traceback.format_exc()}")
            return []

    def _get_all_courses_with_vectors(self) -> List[Dict]:
        """전체 데이터베이스에서 벡터 데이터를 포함한 강의 목록 반환"""
        try:
            if not self.db_client.ensure_connection():
                return []

            with self.db_client.connection.cursor() as cursor:
                sql = """
                SELECT id, name, department_full_name, department, professor, credits,
                       schedule, location, delivery_mode, gpt_description, vector
                FROM jbnu_class_gpt
                WHERE vector IS NOT NULL AND vector != '[]'
                LIMIT 1000
                """

                logger.info("🔍 [SearchService] 전체 DB에서 벡터 데이터 조회")
                cursor.execute(sql)
                results = cursor.fetchall()

                logger.info(f"📊 [SearchService] 전체 DB 조회 결과: {len(results)}개 강의")
                return results

        except Exception as e:
            logger.error(f"❌ [SearchService] 전체 DB 조회 실패: {e}")
            return []