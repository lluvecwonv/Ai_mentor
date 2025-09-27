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

    async def handle(self, user_message: str, query_analysis: Dict, **kwargs) -> List[Dict]:
        """벡터 검색 처리 - 원시 데이터 반환"""
        if not self.is_available():
            return []

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
                return data.get('results', []) if isinstance(data, dict) else data
            else:
                self.logger.error(f"API 오류: {response.status_code}")
                return []

        except Exception as e:
            self.logger.error(f"벡터 검색 실패: {e}")
            return []

