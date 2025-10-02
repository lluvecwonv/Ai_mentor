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
            # ✅ router에서 재구성된 쿼리 사용 (연속대화 처리 완료됨)
            user_message = state.get("user_message") or state.get("query_for_handlers") or state.get("query", "")

            # 원본 메시지는 로깅용으로만 (get_user_message는 state["messages"]에서 가져옴)
            original_from_messages = self.get_user_message(state)

            # state에서 분석된 정보들 가져오기
            expanded_query = state.get("expanded_query", user_message)
            enhanced_query = state.get("enhanced_query", user_message)  # enhanced_query도 가져옴
            keywords = state.get("keywords", "")
            plan = state.get("plan", [])
            entities = state.get("entities", {})
            analysis = state.get("analysis", {})

            logger.info(f"🔍 [{handler_type.upper()}] 메시지 원본: '{original_from_messages[:100]}...' → 실제 사용: '{user_message}'")

            # query_analysis 딕셔너리로 분석 정보 전달
            query_analysis = {
                "enhanced_query": enhanced_query or expanded_query,  # enhanced_query 우선 사용
                "expanded_query": expanded_query,
                "keywords": keywords,
                "plan": plan,
                "entities": entities,
                "analysis": analysis
            }

            result = await handler.handle(
                user_message=user_message,  # 재구성된 쿼리 전달
                query_analysis=query_analysis,
                state=state
            )

            # handle 메서드 결과 처리 - utils 함수 사용
            if isinstance(result, dict) and result.get('agent_type') == 'vector_search':
                from ..utils import format_vector_search_result
                response = format_vector_search_result(result)
            elif isinstance(result, dict) and result.get('agent_type') == 'curriculum':
                # Curriculum 결과에서 display 또는 result 추출
                display = result.get('display', '')
                result_text = result.get('result', '')
                logger.info(f"📊 [CURRICULUM] display 길이: {len(display)}, result 길이: {len(result_text)}")
                logger.info(f"📊 [CURRICULUM] display 포함 여부 - 'data:image': {'data:image' in display}")
                response = display or result_text or str(result)
            else:
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