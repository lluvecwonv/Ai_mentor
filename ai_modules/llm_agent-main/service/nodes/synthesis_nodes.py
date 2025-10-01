import logging
from typing import Dict, Any
from langchain_core.messages import AIMessage
from .base_node import BaseNode, NodeTimer

logger = logging.getLogger(__name__)


class SynthesisNodes(BaseNode):
    """결과 합성 관련 노드들"""

    def __init__(self, result_synthesizer, llm_handler=None):
        self.result_synthesizer = result_synthesizer
        self.llm_handler = llm_handler

        # ResultSynthesizer에 llm_handler 전달
        if self.result_synthesizer and llm_handler:
            self.result_synthesizer.set_llm_handler(llm_handler)

    async def synthesis_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """결과 합성 노드 - 실제 LLM 합성 수행 (department는 1000자 제한)"""
        with NodeTimer("합성") as timer:
            try:
                final_result = state.get("final_result")
                processing_type = state.get("processing_type", "")

                if not final_result:
                    final_result = "죄송합니다. 요청하신 정보를 찾지 못했습니다."
                # 🔥 curriculum은 이미지가 포함되어 있어서 합성 건너뛰기
                elif processing_type == "medium_curriculum":
                    logger.info("📊 Curriculum 결과는 이미지 포함으로 합성 건너뛰기")
                    # final_result 그대로 사용
                else:
                    # 🔥 핵심 수정: 재구성된 쿼리 또는 실제 처리된 쿼리 사용
                    is_continuation = state.get("is_continuation", False)

                    if is_continuation and state.get("query"):
                        # 연속대화면 재구성된 쿼리 사용
                        user_query = state.get("query")
                        logger.info(f"🔄 합성 시 재구성된 쿼리 사용: '{user_query}'")
                    else:
                        # 새로운 질문이면 user_message 사용 (routing에서 이미 재구성됨)
                        user_query = state.get("user_message", "")
                        logger.info(f"🆕 합성 시 user_message 사용: '{user_query}'")

                    # department 에이전트만 1000자로 제한
                    if processing_type == "medium_department":
                        final_result_truncated = final_result[:1000]
                    else:
                        final_result_truncated = final_result

                    # ResultSynthesizer를 사용한 실제 합성
                    final_result = await self.result_synthesizer.synthesize_with_llm(
                        user_query, final_result_truncated, processing_type  # 🔥 수정: user_query 사용
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
