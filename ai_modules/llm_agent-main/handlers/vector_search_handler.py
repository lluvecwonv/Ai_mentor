import httpx
from .base_handler import BaseQueryHandler
from config.settings import settings
from typing import Dict, List

class VectorSearchHandler(BaseQueryHandler):
    """초간단 FAISS 벡터 검색 핸들러"""

    def __init__(self):
        super().__init__()
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.faiss_service_url = settings.search_service_url

    def is_available(self) -> bool:
        return self.http_client is not None

    async def handle(self, user_message: str, query_analysis: Dict, **kwargs) -> Dict:
        """벡터 검색 처리 - 표준화된 응답 반환"""
        if not self.is_available():
            return self.create_response(
                agent_type="vector_search",
                result=[],
                normalized="",
                display="벡터 검색 서비스를 사용할 수 없습니다.",
                success=False
            )

        try:
            # 쿼리 준비
            query_text = user_message
            expanded_queries = query_analysis.get('expanded_queries', [])
            if expanded_queries:
                keywords = [eq.get('text', '') for eq in expanded_queries
                           if eq.get('kind') != 'base' and eq.get('text')]
                if keywords:
                    query_text = f"{user_message} {' '.join(keywords)}"

            # API 호출
            payload = {"query": query_text, "count": 10}
            response = await self.http_client.post(self.faiss_service_url, json=payload)

            if response.status_code == 200:
                data = response.json()
                results = data.get('results', []) if isinstance(data, dict) else data

                # 결과가 있으면 course_name들을 추출해서 정규화
                course_names = []
                if results:
                    course_names = [item.get("course_name", "") for item in results[:5]]

                return self.create_response(
                    agent_type="vector_search",
                    result=results,
                    normalized=", ".join(course_names),  # 과목명 리스트로 정규화
                    display=f"검색된 강의 {len(results)}개: {', '.join(course_names)} ",
                    metadata={
                        "count": len(results),
                        "query_text": query_text,
                        "source": "faiss_service"
                    },
                    success=True
                )
            else:
                self.logger.error(f"API 오류: {response.status_code}")
                return self.create_response(
                    agent_type="vector_search",
                    result=[],
                    display=f"벡터 검색 API 오류: HTTP {response.status_code}",
                    success=False
                )

        except Exception as e:
            self.logger.error(f"벡터 검색 실패: {e}")
            return self.create_response(
                agent_type="vector_search",
                result=[],
                display=f"벡터 검색 중 오류가 발생했습니다: {str(e)}",
                metadata={"error": str(e)},
                success=False
            )

