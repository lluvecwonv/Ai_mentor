import os
import httpx
from .base_handler import BaseQueryHandler
from typing import Dict


class DepartmentMappingHandler(BaseQueryHandler):
    """Department mapping handler for name normalization"""

    def __init__(self):
        super().__init__()
        self.http = httpx.AsyncClient(timeout=10.0)
        self.mapping_service_url = os.getenv(
            "DEPARTMENT_MAPPING_URL", "http://department-mapping:8000/agent"
        )

    def is_available(self) -> bool:
        """Check if mapping service is available"""
        return self.http is not None

    async def handle(self, user_message: str, query_analysis: Dict, **kwargs) -> str:
        """Handle department mapping query"""
        if not self.is_available():
            return "학과 매핑 서비스를 사용할 수 없습니다."

        try:
            payload = {"query": user_message, "top_k": 1}
            resp = await self.http.post(self.mapping_service_url, json=payload)

            if resp.status_code == 200:
                data = resp.json()
                return str(data.get("message", "학과를 찾을 수 없습니다."))

            return f"학과명 매핑 중 오류가 발생했습니다: HTTP {resp.status_code}"

        except Exception as e:
            return f"학과명 매핑 중 오류가 발생했습니다: {str(e)}"

    def get_fallback_message(self) -> str:
        return "학과 매핑 서비스를 사용할 수 없습니다."