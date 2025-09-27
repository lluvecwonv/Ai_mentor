"""
Light 복잡도 노드들
간단한 응답이나 인사말 처리
"""

import logging
from typing import Dict, Any
from .base_node import BaseNode, NodeTimer

logger = logging.getLogger(__name__)


class LightNodes(BaseNode):
    """Light 복잡도 처리 노드들"""

    def __init__(self, llm_handler=None):
        self.llm_handler = llm_handler

    async def light_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Light 노드 - 간단한 질문, 인사말 등 처리"""
        with NodeTimer("Light") as timer:
            try:
                user_message = self.get_user_message(state)
                logger.info(f"💡 [LIGHT] 간단한 처리: '{user_message}...'")

                # LLM 핸들러가 있으면 사용, 없으면 기본 응답
                if self.llm_handler:
                    response = await self.llm_handler.generate_simple_response(user_message)
                else:
                    response = "안녕하세요! 무엇을 도와드릴까요?"

                return self.add_step_time(state, {
                    "final_result": response,
                    "processing_type": "light",
                    "complexity": "light"
                }, timer)

            except Exception as e:
                logger.error(f"❌ [LIGHT] 오류: {e}")
                return self.add_step_time(state, {
                    "final_result": "죄송합니다. 처리 중 오류가 발생했습니다.",
                    "processing_type": "error",
                    "error": str(e)
                }, timer)