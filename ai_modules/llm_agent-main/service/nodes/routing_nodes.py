import logging
from typing import Dict, Any
from .base_node import BaseNode, NodeTimer
from .utils import extract_last_question, extract_history_context

logger = logging.getLogger(__name__)

class RoutingNodes(BaseNode):
    """라우팅 관련 노드들"""

    def __init__(self, query_analyzer, conversation_memory=None):
        self.query_analyzer = query_analyzer
        self.conversation_memory = conversation_memory

    async def router_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """라우터 노드 - 복잡도 분석 및 라우팅"""
        with NodeTimer("Router") as timer:
            user_message = self.get_user_message(state)
            session_id = state.get("session_id", "default")

            # 여러 질문 중 마지막 질문만 추출
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

            # 히스토리 컨텍스트 추출
            history_context = extract_history_context(user_message)

            # 연속대화 판단에 따라 쿼리 선택
            is_continuation = state.get("is_continuation", False)
            if is_continuation:
                # 연속대화면 재구성된 쿼리 사용
                query_for_analysis = state.get("query", clean_message)
                logger.info(f"🔄 연속대화: '{clean_message}' → '{query_for_analysis}'")
            else:
                # 새로운 질문이면 원본 쿼리 사용
                query_for_analysis = clean_message
                logger.info(f"🆕 새로운 질문: '{query_for_analysis}'")

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

            return {
                **state,
                "route": complexity,
                "complexity": complexity,
                "owner_hint": analysis_result.get('owner_hint', ''),
                "routing_reason": analysis_result.get('reasoning', ''),
                "plan": plan,
                "user_message": query_for_analysis,  # 원본 메시지 추가
                "expanded_query": analysis_result.get('enhanced_query', query_for_analysis),  # 확장된 쿼리
                "keywords": analysis_result.get('expansion_keywords', ''),
                "step_times": self.update_step_time(state, "router", timer.duration)
            }
