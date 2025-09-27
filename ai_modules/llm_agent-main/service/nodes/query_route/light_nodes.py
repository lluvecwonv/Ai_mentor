"""
Light 복잡도 노드들
간단한 응답이나 인사말 처리
"""

import logging
from typing import Dict, Any
from ..base_node import BaseNode, NodeTimer

logger = logging.getLogger(__name__)


class LightNodes(BaseNode):
    """Light 복잡도 처리 노드들"""

    def __init__(self, llm_handler=None):
        self.llm_handler = llm_handler

    async def light_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Light 노드 - 간단한 질문, 인사말 등 처리"""
        with NodeTimer("Light") as timer:
            user_message = BaseNode.get_user_message(state)
            response = await self.llm_handler.chat(user_message)
   
            return self.add_step_time(state, {
                "final_result": response,
                "processing_type": "light",
                "complexity": "light"
            }, timer)

         