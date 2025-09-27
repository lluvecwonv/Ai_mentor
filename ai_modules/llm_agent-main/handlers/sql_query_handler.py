"""
간단한 SQL Query Handler
"""
import httpx
from .base_handler import BaseQueryHandler
from config.settings import settings

class SqlQueryHandler(BaseQueryHandler):
    def __init__(self):
        super().__init__()
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.sql_service_url = settings.sql_service_url

    def is_available(self) -> bool:
        return self.http_client is not None

    async def handle(self, user_message: str, query_analysis: dict, **kwargs) -> str:
        """간단한 SQL 처리"""
        if not self.is_available():
            return "데이터베이스 서비스를 사용할 수 없습니다."

        try:
            response = await self.http_client.post(
                self.sql_service_url,
                json={"query": user_message}
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("message", "조회 결과를 가져올 수 없습니다.")
            else:
                return f"데이터베이스 조회 실패 (상태코드: {response.status_code})"

        except Exception as e:
            self.logger.error(f"SQL 처리 실패: {e}")
            return f"데이터베이스 조회 중 오류가 발생했습니다: {str(e)}"

    def get_fallback_message(self) -> str:
        return "데이터베이스 조회 서비스를 사용할 수 없습니다."
