"""
Heavy 복잡도 노드들
복잡한 다단계 처리가 필요한 작업들
"""

import logging
from typing import Dict, Any
from .base_node import BaseNode, NodeTimer

logger = logging.getLogger(__name__)


class HeavyNodes(BaseNode):
    """Heavy 복잡도 처리 노드들"""

    def __init__(self, sql_handler=None, vector_handler=None, dept_handler=None, curriculum_handler=None, llm_handler=None):
        self.sql_handler = sql_handler
        self.vector_handler = vector_handler
        self.dept_handler = dept_handler
        self.curriculum_handler = curriculum_handler
        self.llm_handler = llm_handler

    async def heavy_sequential_executor(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Heavy 순차 실행기 - 복잡한 다단계 처리"""
        with NodeTimer("HeavySequential") as timer:
            try:
                user_message = self.get_user_message(state)
                logger.info(f"⚡ [HEAVY_SEQUENTIAL] 복잡한 처리 시작: '{user_message[:50]}...'")

                results = []

                # 1단계: SQL 검색
                if self.sql_handler:
                    try:
                        sql_result = await self.sql_handler.handle_request(user_message)
                        if sql_result and sql_result.get("response"):
                            results.append(f"데이터베이스 검색: {sql_result['response']}")
                            logger.info("✅ [HEAVY] SQL 검색 완료")
                    except Exception as e:
                        logger.warning(f"⚠️ [HEAVY] SQL 검색 실패: {e}")

                # 2단계: 벡터 검색
                if self.vector_handler:
                    try:
                        vector_result = await self.vector_handler.handle_request(user_message)
                        if vector_result and vector_result.get("response"):
                            results.append(f"유사도 검색: {vector_result['response']}")
                            logger.info("✅ [HEAVY] 벡터 검색 완료")
                    except Exception as e:
                        logger.warning(f"⚠️ [HEAVY] 벡터 검색 실패: {e}")

                # 3단계: 학과 매핑
                if self.dept_handler:
                    try:
                        dept_result = await self.dept_handler.handle_request(user_message)
                        if dept_result and dept_result.get("response"):
                            results.append(f"학과 정보: {dept_result['response']}")
                            logger.info("✅ [HEAVY] 학과 매핑 완료")
                    except Exception as e:
                        logger.warning(f"⚠️ [HEAVY] 학과 매핑 실패: {e}")

                # 4단계: 커리큘럼 검색
                if self.curriculum_handler:
                    try:
                        curriculum_result = await self.curriculum_handler.handle_request(user_message)
                        if curriculum_result and curriculum_result.get("response"):
                            results.append(f"커리큘럼 정보: {curriculum_result['response']}")
                            logger.info("✅ [HEAVY] 커리큘럼 검색 완료")
                    except Exception as e:
                        logger.warning(f"⚠️ [HEAVY] 커리큘럼 검색 실패: {e}")

                # 결과 종합
                if results:
                    final_response = "\n\n".join(results)
                    logger.info(f"🎯 [HEAVY] 순차 처리 완료: {len(results)}개 단계 성공")
                else:
                    final_response = "복잡한 처리를 시도했지만 결과를 얻을 수 없었습니다."
                    logger.warning("⚠️ [HEAVY] 모든 단계 실패")

                return self.add_step_time(state, {
                    "final_result": final_response,
                    "processing_type": "heavy_sequential",
                    "complexity": "heavy",
                    "steps_completed": len(results),
                    "total_steps": 4
                }, timer)

            except Exception as e:
                logger.error(f"❌ [HEAVY_SEQUENTIAL] 전체 처리 실패: {e}")
                return self.add_step_time(state, {
                    "final_result": "복잡한 처리 중 오류가 발생했습니다.",
                    "processing_type": "error",
                    "error": str(e)
                }, timer)