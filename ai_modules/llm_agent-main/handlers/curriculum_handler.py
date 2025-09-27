"""
커리큘럼 핸들러 - 외부 커리큘럼 서비스 연동
"""

import httpx
import logging
from typing import Dict, Any, Optional
from .base_handler import BaseQueryHandler
from config.settings import settings

logger = logging.getLogger(__name__)


class CurriculumHandler(BaseQueryHandler):
    """커리큘럼 서비스와 연동하는 핸들러"""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or settings.curriculum_service_url.replace('/chat', '')
        # 기본적으로 사용 가능하다고 가정하고, 필요시 워밍업에서 검증
        self._health_status = True

        # 기본적인 동기 검증
        try:
            import os
            # API 키 확인 (curriculum 서비스가 OpenAI를 사용할 수 있는지)
            if not os.getenv("OPENAI_API_KEY"):
                logger.warning("⚠️ OPENAI_API_KEY가 설정되지 않았습니다")
                # API 키가 없어도 curriculum 서비스 자체는 작동할 수 있음

            # URL 형식 검증
            if not self.base_url or not self.base_url.startswith('http'):
                logger.warning(f"⚠️ 잘못된 curriculum 서비스 URL: {self.base_url}")
                self._health_status = False

        except Exception as e:
            logger.warning(f"⚠️ Curriculum 핸들러 초기화 중 경고: {e}")
            # 경고만 하고 계속 진행

    async def warmup(self) -> None:
        """커리큘럼 서비스 워밍업"""
        logger.info("🔥 Curriculum 핸들러 워밍업 시작")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # /chat GET 엔드포인트로 헬스체크
                response = await client.get(f"{self.base_url}/chat")

                if response.status_code == 200:
                    logger.info("✅ Curriculum 서비스 워밍업 성공")
                    self._health_status = True
                else:
                    logger.warning(f"⚠️ Curriculum 서비스 응답 코드: {response.status_code}")
                    self._health_status = False

        except Exception as e:
            logger.warning(f"Curriculum 워밍업 중 경고: {e}")
            self._health_status = False

        logger.info("✅ Curriculum 핸들러 워밍업 완료")

    def get_health_status(self) -> Dict[str, Any]:
        """헬스 상태 반환"""
        return {
            "service": "curriculum",
            "healthy": self._health_status,
            "base_url": self.base_url
        }

    async def process(self, query: str, session_id: str = "default", **kwargs) -> Dict[str, Any]:
        """커리큘럼 추천 요청 처리"""
        logger.info("🔄 커리큘럼 서비스 HTTP 통신 시작")

        try:
            # 요청 데이터 구성
            request_data = {
                "query": query,
                "required_dept_count": kwargs.get("required_dept_count", 30)
            }

            logger.info(f"📦 커리큘럼 서비스 요청 데이터:")
            logger.info(f"  📝 쿼리: {query}")
            logger.info(f"  📊 요구 학과 수: {request_data['required_dept_count']}")
            logger.info(f"  🎯 세션 ID: {session_id}")

            url = f"{self.base_url}/chat"
            logger.info(f"🌐 HTTP 요청: POST {url}")

            async with httpx.AsyncClient(timeout=120.0) as client:
                logger.info("📡 HTTP 요청 전송 중...")
                response = await client.post(
                    url,
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                )

                logger.info(f"📨 HTTP 응답 수신: {response.status_code}")

                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"✅ JSON 파싱 성공")

                    message = result.get("message", "")
                    logger.info(f"📄 응답 메시지 길이: {len(message)}자")

                    # 응답 데이터 정리
                    curriculum_response = {
                        "success": True,
                        "message": message,
                        "service": "curriculum",
                        "query": query
                    }

                    logger.info(f"✅ 커리큘럼 처리 성공")
                    return curriculum_response

                else:
                    error_text = response.text[:200] + "..." if len(response.text) > 200 else response.text
                    logger.error(f"❌ 커리큘럼 서비스 HTTP 오류: {response.status_code}")
                    logger.error(f"❌ 오류 응답: {error_text}")
                    return {
                        "success": False,
                        "error": f"커리큘럼 서비스 오류: {response.status_code}",
                        "service": "curriculum"
                    }

        except httpx.TimeoutException:
            logger.error("⏰ 커리큘럼 서비스 타임아웃 (120초 초과)")
            return {
                "success": False,
                "error": "커리큘럼 서비스 타임아웃",
                "service": "curriculum"
            }

        except Exception as e:
            logger.error(f"❌ 커리큘럼 HTTP 통신 실패: {e}")
            import traceback
            logger.error(f"❌ 스택 트레이스: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"커리큘럼 처리 오류: {str(e)}",
                "service": "curriculum"
            }

    async def handle(self, user_message: str, query_analysis: Dict, **kwargs) -> str:
        """Handle curriculum-related queries"""
        logger.info("\n" + "="*60)
        logger.info("📚 커리큘럼 에이전트 처리 시작")
        logger.info(f"📥 사용자 질문: {user_message}")
        logger.info(f"📊 쿼리 분석 데이터: {query_analysis}")
        logger.info(f"🔧 추가 인자: {kwargs}")
        logger.info(f"🏥 서비스 상태: {'정상' if self._health_status else '비정상'}")
        logger.info(f"🌐 베이스 URL: {self.base_url}")

        try:
            # 쿼리 분석 정보 활용 - LLM이 이미 분석한 결과 그대로 사용
            enhanced_query = user_message
            additional_context = {}

            if query_analysis and isinstance(query_analysis, dict):
                # LLM이 이미 향상시킨 쿼리가 있으면 사용
                llm_enhanced = query_analysis.get("enhanced_query")
                if llm_enhanced and llm_enhanced.strip():
                    enhanced_query = llm_enhanced
                    logger.info(f"🧠 LLM 향상 쿼리 사용: {enhanced_query}")

                # 복잡도 정보는 그대로 활용
                complexity = query_analysis.get("complexity", "medium")
                additional_context["complexity"] = complexity
                logger.info(f"📊 쿼리 복잡도: {complexity}")

                # 확장된 컨텍스트 정보 로깅
                expansion_context = query_analysis.get("expansion_context", "")
                if expansion_context:
                    logger.info(f"🔍 LLM 확장 컨텍스트: {expansion_context[:100]}...")
                else:
                    logger.info("📝 원본 사용자 쿼리 사용")

            # 커리큘럼 서비스 호출
            logger.info("🔄 커리큘럼 서비스 호출 시작")
            # query 파라미터가 있으면 사용, 없으면 enhanced_query 사용
            query = kwargs.get("query", enhanced_query)
            # kwargs에서 query를 제거하고 추가 컨텍스트 병합
            process_kwargs = {k: v for k, v in kwargs.items() if k != "query"}
            process_kwargs.update(additional_context)

            response = await self.process(query, **process_kwargs)

            logger.info(f"📡 커리큘럼 서비스 응답: {response}")

            if response.get("success"):
                message = response.get("message", "커리큘럼 정보를 찾을 수 없습니다.")
                message_length = len(message)
                logger.info(f"✅ 커리큘럼 응답 성공: {message_length}자 응답")

                # 응답 내용 일부 로깅 (너무 길면 생략)
                if message_length > 0:
                    preview = message[:200] + "..." if message_length > 200 else message
                    logger.info(f"📄 응답 미리보기: {preview}")

                logger.info("="*60)
                return message
            else:
                error_msg = response.get("error", "커리큘럼 서비스 오류가 발생했습니다.")
                logger.error(f"❌ 커리큘럼 서비스 실패: {error_msg}")
                logger.info("="*60)
                return error_msg

        except Exception as e:
            logger.error(f"❌ Curriculum handler 전체 처리 실패: {e}")
            import traceback
            logger.error(f"❌ 스택 트레이스: {traceback.format_exc()}")
            logger.info("="*60)
            return "커리큘럼 서비스에 문제가 발생했습니다."

    def is_available(self) -> bool:
        """Check if curriculum service is available"""
        return self._health_status

