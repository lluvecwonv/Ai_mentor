import httpx
import logging
from typing import Dict, Any
from .base_handler import BaseQueryHandler
from config.settings import settings

logger = logging.getLogger(__name__)


class CurriculumHandler(BaseQueryHandler):
    """커리큘럼 서비스와 연동하는 핸들러 - 최대 간소화"""

    def __init__(self, base_url: str = None):
        super().__init__()
        self.base_url = base_url or settings.curriculum_service_url.replace('/chat', '')
        self.http_client = httpx.AsyncClient(timeout=120.0)

    async def handle(self, user_message: str, query_analysis: Dict, **kwargs) -> Dict[str, Any]:
        """커리큘럼 쿼리 처리"""
        if not self.is_available():
            return self.create_response(
                agent_type="curriculum",
                result=None,
                display="커리큘럼 서비스를 사용할 수 없습니다.",
                success=False
            )
        try:
            # 쿼리 개선
            enhanced_query = query_analysis.get("enhanced_query", user_message)

            # 커리큘럼 서비스 직접 호출
            request_data = {
                "query": enhanced_query,
            }

            response = await self.http_client.post(
                f"{self.base_url}/chat",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

            # HTTP 상태 코드로 직접 판단
            if response.status_code == 200:
                result = response.json()
                message = result.get("message", "커리큘럼 정보를 찾을 수 없습니다.")
                graph_image_url = result.get("graph_image_url", "")

                # 그래프 이미지 URL을 Markdown 형식으로 추가
                if graph_image_url:
                    display_message = f"{message}\n\n📊 **커리큘럼 로드맵**\n\n![커리큘럼 그래프]({graph_image_url})"
                else:
                    display_message = message

                return self.create_response(
                    agent_type="curriculum",
                    result=message,
                    display=display_message,
                    metadata={
                        "source": "curriculum_service",
                        "response_length": len(message),
                        "graph_url": graph_image_url
                    },
                    success=True
                )
            else:
                return self.create_response(
                    agent_type="curriculum",
                    result=None,
                    display=f"서비스 오류: {response.status_code}",
                    success=False
                )

        except Exception as e:
            logger.error(f"Curriculum 처리 실패: {e}")
            return self.create_response(
                agent_type="curriculum",
                result=None,
                display="커리큘럼 서비스에 문제가 발생했습니다.",
                success=False
            )

    def is_available(self) -> bool:
        """서비스 사용 가능 여부"""
        return self.http_client is not None
