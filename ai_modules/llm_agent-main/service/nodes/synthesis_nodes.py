import logging
from typing import Dict, Any
from langchain_core.messages import AIMessage
from .base_node import BaseNode, NodeTimer

logger = logging.getLogger(__name__)


class SynthesisNodes(BaseNode):
    """결과 합성 관련 노드들"""

    def __init__(self, result_synthesizer):
        self.result_synthesizer = result_synthesizer

    async def synthesis_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """결과 합성 노드 - 실제 LLM 합성 수행"""
        with NodeTimer("합성") as timer:
            try:
                final_result = state.get("final_result")

                if not final_result:
                    final_result = "죄송합니다. 요청하신 정보를 찾지 못했습니다."
                else:
                    # 실제 합성 로직 수행
                    user_message = state.get("user_message", "")
                    processing_type = state.get("processing_type", "")
                    query_analysis = state.get("query_analysis", {})
                    conversation_history = state.get("conversation_history", "")

                    # ResultSynthesizer를 사용한 실제 합성
                    final_result = await self.result_synthesizer.synthesize_with_llm(
                        user_message, final_result, processing_type,
                        query_analysis, conversation_history
                    )

                return {
                    **state,
                    "final_result": final_result,
                    "step_times": self.update_step_time(state, "synthesis", timer.duration),
                    "messages": state.get("messages", []) + [AIMessage(content=final_result)]
                }

            except Exception as e:
                logger.error(f"❌ 합성 노드 실패: {e}")
                return self.create_error_state(state, e, "synthesis")