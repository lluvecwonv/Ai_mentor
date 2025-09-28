import logging
from typing import Dict, Any
from ..base_node import BaseNode, NodeTimer
from .heavy_route.heavy_utils import build_context, enhance_query, log_execution_info

logger = logging.getLogger(__name__)


class HeavyNodes(BaseNode):

    def __init__(self, **handlers):
        self.handlers = {k: v for k, v in handlers.items() if v is not None}
        self.agent_mapping = {
            'Department-Mapping-Agent': 'dept',
            'SQL-Agent': 'sql',
            'FAISS-Search-Agent': 'vector',
            'Curriculum-Agent': 'curriculum',
            'LLM-Fallback-Agent': 'llm'
        }

    async def heavy_sequential_executor(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Heavy 순차 실행기"""
        with NodeTimer("HeavySequential") as timer:
            try:
                user_message = self.get_user_message(state)
                plan = state.get("query_analysis", {}).get("plan", [])

                if not plan:
                    logger.warning("[HEAVY] plan 없음 - 재라우팅")
                    return await self._handle_no_plan(state, timer)

                results = []
                previous_results = []

                for step in plan:
                    agent_name = step.get("agent")
                    handler = self.handlers.get(self.agent_mapping.get(agent_name))
                    
                    if not handler:
                        continue

                    # 컨텍스트 구성 및 쿼리 개선 (유틸리티 함수 사용)
                    context = build_context(previous_results)
                    enhanced_query = enhance_query(agent_name, user_message, context)

                    # 실행 정보 로깅
                    log_execution_info(agent_name, user_message, enhanced_query, context)

                    # 핸들러 실행 (컨텍스트 직접 추가)
                    result = await handler.handle(
                        enhanced_query,
                        state.get("query_analysis", {}),
                        **{**state, "previous_context": context}
                    )

                    if result and result.get("success", True):
                        results.append(f"[{agent_name}] {result.get('display', str(result.get('result', '')))}")
                        previous_results.append(result)

                return self.add_step_time(state, {
                    "final_result": "\n\n".join(results) if results else "처리 결과를 얻을 수 없었습니다.",
                    "processing_type": "heavy_sequential",
                    "steps_completed": len(results)
                }, timer)

            except Exception as e:
                logger.error(f"[HEAVY] 처리 실패: {e}")
                return self.add_step_time(state, {
                    "final_result": "처리 중 오류가 발생했습니다.",
                    "processing_type": "error",
                    "error": str(e)
                }, timer)

    async def _handle_no_plan(self, state: Dict[str, Any], timer) -> Dict[str, Any]:
        logger.warning("[HEAVY] plan이 없어서 라우트 노드로 재라우팅하여 쿼리 분석 재실행")

        # 라우트 노드로 다시 보내기 위해 관련 상태 초기화
        if "route" in state:
            del state["route"]
        if "query_analysis" in state:
            del state["query_analysis"]

        return self.add_step_time(state, {
            "processing_type": "reroute",
            "reroute_reason": "no_plan_in_heavy",
            "needs_reroute": True
        }, timer)
        
        