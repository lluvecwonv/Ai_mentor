import logging
from typing import Dict, Any, Literal
from .base_node import BaseNode, NodeTimer

logger = logging.getLogger(__name__)


class RoutingNodes(BaseNode):
    """라우팅 관련 노드들"""

    def __init__(self, query_analyzer):
        self.query_analyzer = query_analyzer

    async def router_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """라우터 노드 - 복잡도 분석 및 라우팅"""
        with NodeTimer("Router") as timer:

            user_message = self.get_user_message(state)
            session_id = state.get("session_id", "default")

            # 연속대화 판단 및 재구성된 쿼리 사용
            is_continuation = state.get("is_continuation", False)
            if is_continuation:
                query_for_analysis = state.get("reconstructed_query", user_message)
                logger.info(f"🔄 연속대화: '{user_message}' → '{query_for_analysis}'")
            else:
                query_for_analysis = user_message
                logger.info(f"🆕 새로운 대화: '{user_message}'")

            # 쿼리 분석 - 연속대화일 경우 재구성된 쿼리 사용
            analysis_result = await self.query_analyzer.analyze_query_parallel(
                query_for_analysis.strip(),
                session_id=session_id,
                is_reconstructed=is_continuation
            )

            complexity = analysis_result.get('complexity', 'medium')
            plan = analysis_result.get('plan', []) or []
            # QueryAnalyzer 결과 추출
            expanded_query = analysis_result.get('enhanced_query', user_message)
            keywords = analysis_result.get('expansion_keywords', '')

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
                "expanded_query": expanded_query,
                "keywords": keywords,
                "step_times": self.update_step_time(state, "router", timer.duration)
            }
