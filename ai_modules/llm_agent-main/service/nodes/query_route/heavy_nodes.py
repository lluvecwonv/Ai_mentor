import logging
from typing import Dict, Any
from ..base_node import BaseNode, NodeTimer
from .heavy_route.heavy_utils import build_context, enhance_query, log_execution_info
from ..utils import format_vector_search_result

logger = logging.getLogger(__name__)


class HeavyNodes(BaseNode):

    def __init__(self, **handlers):
        # 핸들러 키 이름을 agent_mapping과 일치하도록 변환
        self.handlers = {}
        if handlers.get('dept_handler'):
            self.handlers['dept'] = handlers['dept_handler']
        if handlers.get('sql_handler'):
            self.handlers['sql'] = handlers['sql_handler']
        if handlers.get('vector_handler'):
            self.handlers['vector'] = handlers['vector_handler']
        if handlers.get('curriculum_handler'):
            self.handlers['curriculum'] = handlers['curriculum_handler']
        if handlers.get('llm_handler'):
            self.handlers['llm'] = handlers['llm_handler']

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

                # plan 정보를 올바른 경로에서 가져오기
                plan = state.get("plan", [])

                # 추가 안전장치: query_analysis에서도 확인
                if not plan:
                    plan = state.get("query_analysis", {}).get("plan", [])

                logger.info(f"🔍 [HEAVY] plan 확인: {plan}")

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

                    logger.info(f"🔍 [HEAVY] {agent_name} 결과: success={result.get('success', 'N/A')}, display='{result.get('display', 'N/A')}'")
                    logger.info(f"🔍 [HEAVY] {agent_name} 전체 결과: {result}")

                    if result and result.get("success", True):
                        # utils.py의 함수 사용
                        display_text = format_vector_search_result(result)
                        results.append(f"[{agent_name}] {display_text}")
                        previous_results.append(result)
                        logger.info(f"✅ [HEAVY] {agent_name} 결과 추가됨: {display_text[:100]}...")
                    else:
                        logger.warning(f"❌ [HEAVY] {agent_name} 결과 제외됨: success={result.get('success') if result else 'None'}")

                final_result = "\n\n".join(results) if results else "처리 결과를 얻을 수 없었습니다."
                logger.info(f"🏁 [HEAVY] 최종 결과: {len(results)}개 항목")
                logger.info(f"🏁 [HEAVY] 최종 내용: {final_result[:200]}...")

                return self.add_step_time(state, {
                    "final_result": final_result,
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
        
        