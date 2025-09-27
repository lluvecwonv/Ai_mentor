"""
결과 합성 노드들
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
        """결과 합성 노드 - 모든 경로의 결과를 통합"""
        with NodeTimer("통합 합성") as timer:
            try:
                processing_type = state.get("processing_type", "unknown")

                # Light 처리는 이미 완료된 상태
                if processing_type == "light_llm" or processing_type == "light_greeting":
                    logger.info("💬 Light 처리 완료 - 합성 스킵")
                    return state

                user_message = self.get_user_message(state)
                slots = state.get("slots", {})

                # 결과들을 문자열로 변환
                found_results = self._format_results(slots)

                if not found_results.strip():
                    found_results = "검색 결과가 없습니다."

                # 대화 히스토리 준비
                conversation_history = self._format_conversation_history(state)

                # ResultSynthesizer 호출
                synthesized_result = await self.result_synthesizer.synthesize_with_llm(
                    user_message=user_message,
                    found_results=found_results,
                    processing_type=f"unified_{processing_type}",
                    query_analysis={"complexity": state.get("complexity", "medium")},
                    conversation_history=conversation_history
                )

                logger.info(f"✅ 통합 합성 완료: {len(synthesized_result)} 문자 결과")
                logger.info(f"🎯 [최종답변] Synthesis 결과: {synthesized_result}")

                return {
                    **state,
                    "step_times": self.update_step_time(state, "synthesis", timer.duration),
                    "messages": state.get("messages", []) + [AIMessage(content=synthesized_result)],
                    "final_result": synthesized_result,
                    "result_confidence": 0.8
                }

            except Exception as e:
                logger.error(f"❌ 통합 합성 노드 실패: {e}")
                return self.create_error_state(state, e, "synthesis")

    def _format_results(self, slots: Dict[str, Any]) -> str:
        """슬롯 결과들을 문자열로 포맷팅"""
        found_results = ""
        for key, value in slots.items():
            found_results += f"### {key.upper()} 결과:\n{str(value)}\n\n"
        return found_results

    def _format_conversation_history(self, state: Dict[str, Any]) -> str:
        """대화 히스토리 포맷팅"""
        conversation_history = ""
        messages = state.get("messages", [])
        for msg in messages:
            if hasattr(msg, 'content'):
                conversation_history += f"{msg.content}\n"
        return conversation_history

    async def quick_synthesis_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """빠른 합성 노드 - 간단한 결과 통합"""
        with NodeTimer("빠른 합성") as timer:
            try:
                slots = state.get("slots", {})
                processing_type = state.get("processing_type", "unknown")

                # 단순 결과 통합
                if not slots:
                    final_result = "죄송합니다. 검색 결과를 찾지 못했습니다."
                else:
                    # 첫 번째 유효한 결과 사용
                    for key, value in slots.items():
                        if value and str(value).strip():
                            final_result = str(value)
                            break
                    else:
                        final_result = "검색을 완료했지만 관련 정보를 찾지 못했습니다."

                logger.info(f"🎯 [최종답변] Quick Synthesis 결과: {final_result}")

                return {
                    **state,
                    "final_result": final_result,
                    "result_confidence": 0.6,
                    "step_times": self.update_step_time(state, "quick_synthesis", timer.duration),
                    "messages": state.get("messages", []) + [AIMessage(content=final_result)]
                }

            except Exception as e:
                return self.create_error_state(state, e, "quick_synthesis")

    async def tot_synthesis_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Tree of Thoughts 합성 노드 - 여러 후보 중 최선 선택"""
        with NodeTimer("ToT 합성") as timer:
            try:
                slots = state.get("slots", {})
                candidates = []

                # 각 슬롯 결과를 후보로 생성
                for key, value in slots.items():
                    if value and str(value).strip():
                        candidates.append({
                            "source": key,
                            "content": str(value),
                            "confidence": self._estimate_confidence(key, value)
                        })

                if not candidates:
                    return await self.quick_synthesis_node(state)

                # 최고 신뢰도 후보 선택
                best_candidate = max(candidates, key=lambda c: c["confidence"])

                # 후보들을 조합한 종합 답변 생성
                combined_result = await self._combine_candidates(
                    candidates,
                    self.get_user_message(state)
                )

                logger.info(f"✅ ToT 합성 완료: {len(candidates)}개 후보 중 선택")
                logger.info(f"🎯 [최종답변] ToT Synthesis 결과: {combined_result}")

                return {
                    **state,
                    "final_result": combined_result,
                    "result_confidence": best_candidate["confidence"],
                    "step_times": self.update_step_time(state, "tot_synthesis", timer.duration),
                    "messages": state.get("messages", []) + [AIMessage(content=combined_result)],
                    "tot_candidates": candidates,
                    "best_candidate": best_candidate
                }

            except Exception as e:
                return self.create_error_state(state, e, "tot_synthesis")

    def _estimate_confidence(self, source: str, content: Any) -> float:
        """결과 신뢰도 추정"""
        if "sql" in source.lower():
            return 0.9  # SQL 결과는 높은 신뢰도
        elif "dept_mapping" in source.lower():
            return 0.8  # 학과 매핑도 높은 신뢰도
        elif "faiss" in source.lower():
            return 0.7  # 벡터 검색은 중간 신뢰도
        else:
            return 0.5  # 기타는 낮은 신뢰도

    async def _combine_candidates(self, candidates: list, user_query: str) -> str:
        """후보들을 조합하여 종합 답변 생성"""
        try:
            # 간단한 조합 로직 (나중에 LLM으로 개선 가능)
            primary = candidates[0]["content"] if candidates else ""

            if len(candidates) > 1:
                secondary_info = []
                for candidate in candidates[1:]:
                    if candidate["content"] != primary:
                        secondary_info.append(candidate["content"][:100])

                if secondary_info:
                    primary += "\n\n추가 참고 정보:\n" + "\n".join(secondary_info)

            return primary

        except Exception as e:
            logger.error(f"후보 조합 중 오류: {e}")
            return candidates[0]["content"] if candidates else "결과 조합 중 오류가 발생했습니다."