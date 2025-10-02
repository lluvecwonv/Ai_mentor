"""
Light 복잡도 노드들
간단한 응답이나 인사말 처리
"""

import logging
from typing import Dict, Any
from ..base_node import BaseNode, NodeTimer
from ...handlers.llm_client_main import LlmClient

logger = logging.getLogger(__name__)


class LightNodes(BaseNode):
    """Light 복잡도 처리 노드들"""

    def __init__(self, llm_handler=None):
        self.llm_handler = llm_handler

    async def light_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Light 노드 - 간단한 질문, 인사말 등 처리"""
        with NodeTimer("Light") as timer:
            # ✅ router에서 재구성된 쿼리 사용 (연속대화 처리 완료됨)
            user_message = state.get("user_message") or state.get("query_for_handlers") or state.get("query", "")

            logger.info(f"🔍 [LIGHT] 사용 쿼리: '{user_message}'")

            # Light 노드용 LLM 설정 (빠른 응답을 위해 작은 모델 사용)
            light_llm = LlmClient.create_with_config(
                model="gpt-4.1",  # 빠른 응답을 위한 작은 모델
                max_tokens=400  # 간단한 응답을 위한 적은 토큰
            )

            response = await light_llm.chat(user_message)

            return self.add_step_time(state, {
                "final_result": response,
                "processing_type": "light",
                "complexity": "light"
            }, timer)

