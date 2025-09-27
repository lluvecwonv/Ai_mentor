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

            # 쿼리 분석
            analysis_result = await self.query_analyzer.analyze_query_parallel(
                user_message.strip(),
                session_id=session_id
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
                "routing_reason": analysis_result.get('reasoning', ''),
                "plan": plan,
                "expanded_query": expanded_query,
                "keywords": keywords,
                "step_times": self.update_step_time(state, "router", timer.duration)
            }
