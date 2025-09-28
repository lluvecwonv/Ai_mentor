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

    async def handle(self, user_message: str, query_analysis: dict, **kwargs) -> dict:
        """SQL 처리 - 표준화된 응답 반환"""
        if not self.is_available():
            return self.create_response(
                agent_type="sql_query",
                result=None,
                normalized="",
                display="데이터베이스 서비스를 사용할 수 없습니다.",
                success=False
            )

        # enhanced_query가 있으면 사용, 없으면 원본 user_message 사용
        query_to_use = query_analysis.get("enhanced_query", user_message)
        self.logger.info(f"🔍 SQL 쿼리 사용: '{query_to_use}'")

        try:
            response = await self.http_client.post(
                self.sql_service_url,
                json={"query": query_to_use}
            )

            if response.status_code == 200:
                result = response.json()
                db_result = result.get("result", result.get("message", "조회 결과를 가져올 수 없습니다."))

                return self.create_response(
                    agent_type="sql_query",
                    result=db_result,
                    display=str(db_result),
                    metadata={
                        "source": "sql_service",
                        "query": user_message,
                        "response_length": len(str(db_result))
                    },
                    success=True
                )
            else:
                return self.create_response(
                    agent_type="sql_query",
                    result=None,
                    display=f"데이터베이스 조회 실패 (상태코드: {response.status_code})",
                    success=False
                )

        except Exception as e:
            self.logger.error(f"SQL 처리 실패: {e}")
            return self.create_response(
                agent_type="sql_query",
                result=None,
                display=f"데이터베이스 조회 중 오류가 발생했습니다: {str(e)}",
                metadata={"error": str(e)},
                success=False
            )

    def get_fallback_message(self) -> str:
        return "데이터베이스 조회 서비스를 사용할 수 없습니다."
