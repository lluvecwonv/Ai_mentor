"""
Medium 복잡도 노드들
데이터베이스 검색, 벡터 검색, 커리큘럼 처리 등
"""

import logging
from typing import Dict, Any, Optional
from ..base_node import BaseNode, NodeTimer

logger = logging.getLogger(__name__)


class MediumNodes(BaseNode):
    """Medium 복잡도 처리 노드들"""

    def __init__(self, sql_handler=None, vector_handler=None, dept_handler=None, curriculum_handler=None):
        self.sql_handler = sql_handler
        self.vector_handler = vector_handler
        self.dept_handler = dept_handler
        self.curriculum_handler = curriculum_handler

    async def _handle_medium_request(self, state: Dict[str, Any], handler: Optional[Any],
                                    handler_type: str, timer: NodeTimer) -> Dict[str, Any]:
        try:
            user_message = self.get_user_message(state)
            # state에서 분석된 정보들 가져오기
            expanded_query = state.get("expanded_query", user_message)
            keywords = state.get("keywords", "")
            plan = state.get("plan", [])
            entities = state.get("entities", {})
            analysis = state.get("analysis", {})

            # query_analysis 딕셔너리로 분석 정보 전달
            query_analysis = {
                "enhanced_query": expanded_query,
                "keywords": keywords,
                "plan": plan,
                "entities": entities,
                "analysis": analysis
            }

            result = await handler.handle(
                user_message=user_message,
                query_analysis=query_analysis,
                state=state
            )

            # handle 메서드는 문자열을 직접 반환
            response = result if isinstance(result, str) else str(result)

            return self.add_step_time(state, {
                "final_result": response,
                "processing_type": f"medium_{handler_type}",
                "complexity": "medium"
            }, timer)

        except Exception as e:
            logger.error(f"❌ [MEDIUM_{handler_type.upper()}] 오류: {e}")
            return self.add_step_time(state, {
                "final_result": f"{handler_type} 처리 중 오류가 발생했습니다.",
                "processing_type": "error",
                "error": str(e)
            }, timer)


    async def medium_department_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Medium Department 노드 - 학과 매핑 처리"""
        with NodeTimer("MediumDepartment") as timer:
            return await self._handle_medium_request(
                state, self.dept_handler, "department", timer
            )

    async def medium_sql_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Medium SQL 노드 - 데이터베이스 검색"""
        with NodeTimer("MediumSQL") as timer:
            return await self._handle_medium_request(
                state, self.sql_handler, "sql", timer
            )

    async def medium_vector_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Medium Vector 노드 - 벡터 검색"""
        with NodeTimer("MediumVector") as timer:
            return await self._handle_medium_request(
                state, self.vector_handler, "vector", timer
            )

    async def medium_curriculum_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Medium 커리큘럼 노드 - 교육과정 처리"""
        with NodeTimer("MediumCurriculum") as timer:
            return await self._handle_medium_request(
                state, self.curriculum_handler, "curriculum", timer
            )