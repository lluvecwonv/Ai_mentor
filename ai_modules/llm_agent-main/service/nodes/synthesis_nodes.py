"""
결과 합성 노드 - 단순화 버전
모든 에이전트 결과를 자연스러운 답변으로 통합
"""

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
        """결과 합성 노드 - 간단하고 친화적인 답변 생성"""
        with NodeTimer("합성") as timer:
            try:
                user_message = self.get_user_message(state)
                slots = state.get("slots", {})

                # 결과 수집
                results = []
                for key, value in slots.items():
                    if value and str(value).strip():
                        results.append(str(value))

                # 결과가 없으면 기본 메시지
                if not results:
                    final_result = "죄송합니다. 요청하신 정보를 찾지 못했습니다."
                # 결과가 하나면 그대로 사용
                elif len(results) == 1:
                    final_result = results[0]
                # 여러 결과가 있으면 ResultSynthesizer로 통합
                else:
                    combined_results = "\n\n".join(results)
                    final_result = await self.result_synthesizer.synthesize_with_llm(
                        user_message=user_message,
                        found_results=combined_results,
                        processing_type="unified",
                        query_analysis={"complexity": state.get("complexity", "medium")},
                        conversation_history=""
                    )

                logger.info("✅ 합성 완료")

                return {
                    **state,
                    "final_result": final_result,
                    "step_times": self.update_step_time(state, "synthesis", timer.duration),
                    "messages": state.get("messages", []) + [AIMessage(content=final_result)]
                }

            except Exception as e:
                logger.error(f"❌ 합성 노드 실패: {e}")
                return self.create_error_state(state, e, "synthesis")