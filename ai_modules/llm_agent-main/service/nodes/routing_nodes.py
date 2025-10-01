import logging
from typing import Dict, Any
from .base_node import BaseNode, NodeTimer
from .utils import extract_last_question, extract_history_context
from .route.utils import generate_initial_feedback, generate_routing_feedback

logger = logging.getLogger(__name__)

class RoutingNodes(BaseNode):
    """라우팅 관련 노드들"""

    def __init__(self, query_analyzer, conversation_memory=None, llm_client=None):
        self.query_analyzer = query_analyzer
        self.conversation_memory = conversation_memory
        self.llm_client = llm_client

    async def router_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """라우터 노드 - 복잡도 분석 및 라우팅"""
        with NodeTimer("Router") as timer:
            session_id = state.get("session_id", "default")
            user_message = self.get_user_message(state)
            is_continuation = state.get("is_continuation", False)
            reconstructed_query = state.get("query", "")

            # 🔥 핵심 수정: 연속대화 여부에 따라 다르게 처리
            if is_continuation and reconstructed_query and reconstructed_query.strip():
                # 연속대화 → 재구성된 쿼리 사용
                query_for_analysis = reconstructed_query
                logger.info(f"🔄 연속대화 (재구성 쿼리 사용): '{query_for_analysis}'")
            else:
                # 새로운 질문 → 마지막 질문만 추출
                clean_message = extract_last_question(user_message)

                # Follow-up 질문 생성 요청이나 빈 문자열인 경우 처리 중단
                if not clean_message or not clean_message.strip():
                    logger.info("🚫 처리할 질문이 없음 - LLM_FALLBACK으로 라우팅")
                    return {
                        **state,
                        "route": "light",
                        "complexity": "light",
                        "owner_hint": "LLM_FALLBACK",
                        "routing_reason": "빈 질문 또는 Follow-up 생성 요청",
                        "plan": [],
                        "expanded_query": "",
                        "keywords": "",
                        "step_times": self.update_step_time(state, "router", 0.001)
                    }

                query_for_analysis = clean_message
                logger.info(f"🆕 새로운 질문 (마지막 질문 추출): '{query_for_analysis}'")

            # 즉시 피드백 메시지 전송 (분석 전)
            initial_msg = generate_initial_feedback(query_for_analysis)
            logger.info(f"🔔 즉시 피드백: '{initial_msg}' | callback존재: {state.get('stream_callback') is not None}")
            if initial_msg and state.get("stream_callback"):
                await state["stream_callback"](initial_msg)

            # 히스토리 컨텍스트 추출
            history_context = extract_history_context(user_message)

            # 쿼리 분석 (히스토리 컨텍스트 포함)
            analysis_result = await self.query_analyzer.analyze_query_parallel(
                query_for_analysis.strip(),
                session_id=session_id,
                is_reconstructed=is_continuation,
                history_context=history_context
            )

            complexity = analysis_result.get('complexity', 'medium')
            plan = analysis_result.get('plan', []) or []

            # 복잡도 승격 (다단계 plan이면 heavy로)
            if complexity == 'medium' and len(plan) > 1:
                complexity = 'heavy'

            logger.info(f"✅ 라우팅: {complexity}")

            # 중간 피드백 메시지 생성 및 스트리밍
            feedback_msg = generate_routing_feedback(
                complexity,
                analysis_result.get('owner_hint', ''),
                analysis_result.get('category', ''),
                query_for_analysis
            )

            if feedback_msg and state.get("stream_callback"):
                await state["stream_callback"](feedback_msg)

            # 🔥 messages도 업데이트하여 get_user_message()가 올바른 쿼리를 반환하도록 함
            from langchain_core.messages import HumanMessage
            updated_messages = [HumanMessage(content=query_for_analysis)]

            return {
                **state,
                "messages": updated_messages,  # messages 업데이트 (get_user_message가 이것을 사용)
                "route": complexity,
                "complexity": complexity,
                "owner_hint": analysis_result.get('owner_hint', ''),
                "routing_reason": analysis_result.get('reasoning', ''),
                "plan": plan,
                "user_message": query_for_analysis,  # 재구성된 쿼리를 user_message로 저장
                "query_for_handlers": query_for_analysis,  # 핸들러들이 사용할 쿼리 (재구성된 쿼리)
                "expanded_query": analysis_result.get('enhanced_query', query_for_analysis),  # 확장된 쿼리
                "enhanced_query": analysis_result.get('enhanced_query', query_for_analysis),  # 핸들러 호환성을 위해 추가
                "keywords": analysis_result.get('expansion_keywords', ''),
                "step_times": self.update_step_time(state, "router", timer.duration)
            }

    async def light_validator_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Light 검증 노드 - LLM으로 일반 대화인지 재확인"""
        with NodeTimer("LightValidator") as timer:
            query = state.get("user_message", self.get_user_message(state))

            if not self.llm_client:
                logger.error("❌ LLM Client가 없음 - Light 검증 건너뛰기 (기본 통과)")
                return {
                    **state,
                    "light_validation_passed": True,
                    "validation_reason": "LLM Client 없음",
                    "step_times": self.update_step_time(state, "light_validator", timer.duration)
                }

            try:
                # LLM으로 검증
                validation_result = await self.llm_client.validate_light_query(query)

                is_general_chat = validation_result.get("is_general_chat", False)
                reason = validation_result.get("reason", "")

                logger.info(f"🔍 [Light 검증] query='{query}' | is_general_chat={is_general_chat} | reason={reason}")

                # 🔥 핵심 수정: is_general_chat=True면 거절 (validation_passed=False)
                # 일반 대화(학업과 무관)는 거부해야 함
                validation_passed = not is_general_chat

                logger.info(f"{'✅' if validation_passed else '❌'} Light 검증 결과: {'통과 (학업 관련)' if validation_passed else '거절 (일반 대화)'}")

                return {
                    **state,
                    "light_validation_passed": validation_passed,
                    "validation_reason": reason,
                    "step_times": self.update_step_time(state, "light_validator", timer.duration)
                }

            except Exception as e:
                logger.error(f"❌ Light 검증 실패: {e} → 기본 통과")
                return {
                    **state,
                    "light_validation_passed": True,
                    "validation_reason": f"검증 오류: {str(e)}",
                    "step_times": self.update_step_time(state, "light_validator", timer.duration)
                }
