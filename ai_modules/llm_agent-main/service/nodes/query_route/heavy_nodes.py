"""
Heavy 복잡도 노드들
복잡한 다단계 처리가 필요한 작업들
"""

import logging
from typing import Dict, Any
from ..base_node import BaseNode, NodeTimer

logger = logging.getLogger(__name__)


class HeavyNodes(BaseNode):
    """Heavy 복잡도 처리 노드들"""

    def __init__(self, sql_handler=None, vector_handler=None, dept_handler=None, curriculum_handler=None, llm_handler=None):
        # 핸들러만 딕셔너리로 관리
        self.handlers = {
            'sql': sql_handler,
            'vector': vector_handler,
            'dept': dept_handler,
            'curriculum': curriculum_handler
        }

    async def heavy_sequential_executor(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Heavy 순차 실행기 - 복잡한 다단계 처리"""
        with NodeTimer("HeavySequential") as timer:
            try:
                user_message = self.get_user_message(state)
                logger.info(f"⚡ [HEAVY_SEQUENTIAL] 복잡한 처리 시작: '{user_message[:50]}...'")

                # 모든 핸들러 실행하고 slots에 저장
                slots = state.get("slots", {}).copy()
                results = await self._execute_all_handlers(user_message, state, slots)

                # 결과 종합
                final_response = self._aggregate_results(results)
                logger.info(f"🎯 [HEAVY] 순차 처리 완료: {len(results)}개 단계 성공")

                return self.add_step_time(state, {
                    "slots": slots,
                    "final_result": final_response,
                    "processing_type": "heavy_sequential",
                    "complexity": "heavy",
                    "steps_completed": len(results),
                    "total_steps": len(self.handlers)
                }, timer)

            except Exception as e:
                logger.error(f"❌ [HEAVY_SEQUENTIAL] 전체 처리 실패: {e}")
                return self.add_step_time(state, {
                    "final_result": "복잡한 처리 중 오류가 발생했습니다.",
                    "processing_type": "error",
                    "error": str(e)
                }, timer)

    async def _execute_all_handlers(self, user_message: str, state: Dict[str, Any], slots: Dict[str, Any]) -> list:
        """모든 핸들러 실행"""
        results = []
        query_analysis = state.get("query_analysis", {})

        for handler_name, handler in self.handlers.items():
            if handler and handler.is_available():
                try:
                    # BaseQueryHandler의 표준 handle 메서드 호출
                    result = await handler.handle(user_message, query_analysis, **state)
                    if result:
                        # 슬롯에 결과 저장 (키는 핸들러명)
                        slots[handler_name] = result
                        # 기존 results 리스트도 유지 (호환성)
                        result_prefix = self._get_result_prefix(handler_name)
                        results.append(f"{result_prefix}: {result}")
                        logger.info(f"✅ [HEAVY] {handler_name} 검색 완료")
                except Exception as e:
                    logger.warning(f"⚠️ [HEAVY] {handler_name} 검색 실패: {e}")
            elif handler:
                logger.warning(f"⚠️ [HEAVY] {handler_name} 핸들러 사용 불가")

        return results

    def _get_result_prefix(self, handler_name: str) -> str:
        """핸들러 이름 기반 결과 접두사 생성"""
        prefixes = {
            'sql': "데이터베이스 검색",
            'vector': "유사도 검색",
            'dept': "학과 정보",
            'curriculum': "커리큘럼 정보"
        }
        return prefixes.get(handler_name, f"{handler_name} 검색")

    def _aggregate_results(self, results: list) -> str:
        """결과 집계"""
        if results:
            return "\n\n".join(results)
        else:
            logger.warning("⚠️ [HEAVY] 모든 단계 실패")
            return "복잡한 처리를 시도했지만 결과를 얻을 수 없었습니다."