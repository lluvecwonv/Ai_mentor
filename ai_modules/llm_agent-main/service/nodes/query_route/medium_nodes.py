"""
Medium 복잡도 노드들
데이터베이스 검색, 벡터 검색, 커리큘럼 처리 등
"""

import logging
from typing import Dict, Any
from .base_node import BaseNode, NodeTimer

logger = logging.getLogger(__name__)


class MediumNodes(BaseNode):
    """Medium 복잡도 처리 노드들"""

    def __init__(self, sql_handler=None, vector_handler=None, dept_handler=None, curriculum_handler=None):
        self.sql_handler = sql_handler
        self.vector_handler = vector_handler
        self.dept_handler = dept_handler
        self.curriculum_handler = curriculum_handler

    async def medium_agent_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Medium Agent 노드 - 일반적인 에이전트 처리"""
        with NodeTimer("MediumAgent") as timer:
            try:
                user_message = self.get_user_message(state)
                logger.info(f"🤖 [MEDIUM_AGENT] 에이전트 처리: '{user_message[:50]}...'")

                response = f"Medium 복잡도 에이전트 응답: {user_message}"

                return self.add_step_time(state, {
                    "final_result": response,
                    "processing_type": "medium_agent",
                    "complexity": "medium"
                }, timer)

            except Exception as e:
                logger.error(f"❌ [MEDIUM_AGENT] 오류: {e}")
                return self.add_step_time(state, {
                    "final_result": "에이전트 처리 중 오류가 발생했습니다.",
                    "processing_type": "error",
                    "error": str(e)
                }, timer)

    async def medium_sql_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Medium SQL 노드 - 데이터베이스 검색"""
        with NodeTimer("MediumSQL") as timer:
            try:
                user_message = self.get_user_message(state)
                logger.info(f"🗄️ [MEDIUM_SQL] SQL 검색: '{user_message[:50]}...'")

                if self.sql_handler:
                    # 실제 SQL 핸들러 호출
                    result = await self.sql_handler.handle_request(user_message)
                    response = result.get("response", "SQL 검색 결과를 가져올 수 없습니다.")
                else:
                    response = "SQL 핸들러가 초기화되지 않았습니다."

                return self.add_step_time(state, {
                    "final_result": response,
                    "processing_type": "medium_sql",
                    "complexity": "medium"
                }, timer)

            except Exception as e:
                logger.error(f"❌ [MEDIUM_SQL] 오류: {e}")
                return self.add_step_time(state, {
                    "final_result": "데이터베이스 검색 중 오류가 발생했습니다.",
                    "processing_type": "error",
                    "error": str(e)
                }, timer)

    async def medium_vector_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Medium Vector 노드 - 벡터 검색"""
        with NodeTimer("MediumVector") as timer:
            try:
                user_message = self.get_user_message(state)
                logger.info(f"🔍 [MEDIUM_VECTOR] 벡터 검색: '{user_message[:50]}...'")

                if self.vector_handler:
                    # 실제 벡터 핸들러 호출
                    result = await self.vector_handler.handle_request(user_message)
                    response = result.get("response", "벡터 검색 결과를 가져올 수 없습니다.")
                else:
                    response = "벡터 핸들러가 초기화되지 않았습니다."

                return self.add_step_time(state, {
                    "final_result": response,
                    "processing_type": "medium_vector",
                    "complexity": "medium"
                }, timer)

            except Exception as e:
                logger.error(f"❌ [MEDIUM_VECTOR] 오류: {e}")
                return self.add_step_time(state, {
                    "final_result": "벡터 검색 중 오류가 발생했습니다.",
                    "processing_type": "error",
                    "error": str(e)
                }, timer)

    async def medium_curriculum_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Medium 커리큘럼 노드 - 교육과정 처리"""
        with NodeTimer("MediumCurriculum") as timer:
            try:
                user_message = self.get_user_message(state)
                logger.info(f"📚 [MEDIUM_CURRICULUM] 커리큘럼 처리: '{user_message[:50]}...'")

                if self.curriculum_handler:
                    # 실제 커리큘럼 핸들러 호출
                    result = await self.curriculum_handler.handle_request(user_message)
                    response = result.get("response", "커리큘럼 정보를 가져올 수 없습니다.")
                else:
                    response = "커리큘럼 핸들러가 초기화되지 않았습니다."

                return self.add_step_time(state, {
                    "final_result": response,
                    "processing_type": "medium_curriculum",
                    "complexity": "medium"
                }, timer)

            except Exception as e:
                logger.error(f"❌ [MEDIUM_CURRICULUM] 오류: {e}")
                return self.add_step_time(state, {
                    "final_result": "커리큘럼 처리 중 오류가 발생했습니다.",
                    "processing_type": "error",
                    "error": str(e)
                }, timer)