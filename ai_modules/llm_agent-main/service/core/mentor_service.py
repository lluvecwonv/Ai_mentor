import logging
from typing import Dict, Any
from datetime import datetime

from config.settings import settings
from exceptions import AIMentorException
from service.memory.memory import ConversationMemory

logger = logging.getLogger(__name__)


from .langgraph_app import LangGraphApp
UNIFIED_LANGGRAPH_AVAILABLE = True


class HybridMentorService:
    """통합 LangGraph 전용 AI Mentor 서비스"""

    def __init__(self, use_unified_langgraph: bool = True):
        logger.info("🚀 HybridMentorService 초기화")
        # 대화 메모리
        self.conversation_memory = ConversationMemory(
            max_history_length=settings.max_history_length
        )
        # LangGraph 앱
        self.langgraph_app = LangGraphApp(self.conversation_memory)
        logger.info("✅ 초기화 완료")


    async def run_agent(self, user_message: str, session_id: str = "default") -> Dict[str, Any]:
        """메인 처리 함수"""
        logger.info(f"🤖 질문 처리: {user_message}...")

        # Follow-up 질문 생성 요청 완전 차단
        if "### Task:" in user_message and "follow-up questions" in user_message:
            logger.info("🚫 Follow-up 질문 생성 요청 차단")
            return {
                "id": "chatcmpl-ai-mentor",
                "object": "chat.completion",
                "created": int(datetime.now().timestamp()),
                "model": "ai-mentor",
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": ""},
                    "finish_reason": "stop"
                }]
            }

        try:
            result = await self.langgraph_app.process_query(user_message, session_id)

            # OpenAI 호환 형식으로 변환
            if isinstance(result, dict) and "response" in result:
                content = result["response"]
            else:
                content = str(result)

            return {
                "id": "chatcmpl-ai-mentor",
                "object": "chat.completion",
                "created": int(datetime.now().timestamp()),
                "model": "ai-mentor",
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop"
                }]
            }

        except Exception as e:
            logger.error(f"❌ 처리 실패: {e}")
            raise AIMentorException(f"처리 중 오류: {str(e)}")

    def get_health_status(self) -> Dict[str, Any]:
        """헬스 체크"""
        return {
            "status": "healthy",
            "service": "ai-mentor",
            "version": "3.0-simple",
            "mode": "unified_langgraph",
            "timestamp": datetime.now().isoformat()
        }

    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """세션 정보"""
        return {
            "session_info": {
                "session_id": session_id,
                "service_mode": "unified_langgraph"
            }
        }

    def clear_session_history(self, session_id: str) -> bool:
        """세션 초기화"""
        try:
            if hasattr(self.conversation_memory, 'clear_session'):
                self.conversation_memory.clear_session(session_id)
            return True
        except Exception:
            return False