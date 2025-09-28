import os
import httpx
from .base_handler import BaseQueryHandler
from config.settings import settings
from typing import Dict


class DepartmentMappingHandler(BaseQueryHandler):
    """Department mapping handler for name normalization"""

    def __init__(self):
        super().__init__()
        self.http = httpx.AsyncClient(timeout=10.0)
        self.mapping_service_url = os.getenv(
            "DEPARTMENT_MAPPING_URL", settings.mapping_service_url
        )

    def is_available(self) -> bool:
        """Check if mapping service is available"""
        return self.http is not None

    async def handle(self, user_message: str, query_analysis: Dict, **kwargs) -> Dict:
        """Handle department mapping query and return standardized response"""
        if not self.is_available():
            return self.create_response(
                agent_type="department_mapping",
                result=None,
                normalized="",
                display="학과 매핑 서비스를 사용할 수 없습니다.",
                success=False
            )

        try:
            # previous_context 확인 (첫 번째 단계라서 보통 비어있음)
            previous_context = kwargs.get("previous_context", {})

            # Department-Mapping은 첫 번째 단계이므로 원본 쿼리 사용
            # 하지만 이전 컨텍스트가 있다면 로깅
            if previous_context.get("step_count", 0) > 0:
                self.logger.info(f"[DEPT] 이전 컨텍스트 존재: {previous_context}")

            payload = {"query": user_message, "top_k": 1}
            resp = await self.http.post(self.mapping_service_url, json=payload)

            if resp.status_code == 200:
                data = resp.json()
                dept_name = data.get("message", "학과를 찾을 수 없습니다.")

                return self.create_response(
                    agent_type="department_mapping",
                    result=dept_name,
                    normalized=dept_name,  # 정규화된 학과명
                    display=f"학과: {dept_name}",
                    metadata={
                        "confidence": data.get("confidence", 1.0),
                        "source": "mapping_service",
                        "original_query": user_message
                    },
                    success=True
                )

            return self.create_response(
                agent_type="department_mapping",
                result=None,
                display=f"학과명 매핑 중 오류가 발생했습니다: HTTP {resp.status_code}",
                success=False
            )

        except Exception as e:
            return self.create_response(
                agent_type="department_mapping",
                result=None,
                display=f"학과명 매핑 중 오류가 발생했습니다: {str(e)}",
                metadata={"error": str(e)},
                success=False
            )

    def get_fallback_message(self) -> str:
        return "학과 매핑 서비스를 사용할 수 없습니다."