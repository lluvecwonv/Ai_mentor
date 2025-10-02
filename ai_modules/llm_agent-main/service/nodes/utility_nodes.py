"""
유틸리티 노드들
완료, 에러 처리, 헬스체크 등 공통 기능들
"""

import logging
import random
from typing import Dict, Any
from datetime import datetime
from .base_node import BaseNode, NodeTimer

logger = logging.getLogger(__name__)


class UtilityNodes(BaseNode):
    """유틸리티 노드들"""

    def __init__(self):
        # 다양한 거절 메시지 목록
        self.rejection_messages = [
            "죄송합니다. 전북대학교 학사 정보에 관련된 질문만 답변할 수 있습니다.",
            "아쉽게도 그 질문은 답변하기 어렵습니다. 수업, 교수님, 학과, 커리큘럼 등 학사 관련 질문을 해주세요.",
            "전북대학교 AI 멘토는 학업 및 학사 정보만 안내할 수 있습니다. 다른 질문을 해주시겠어요?",
            "죄송하지만 학사 정보와 관련 없는 질문에는 답변드리기 어렵습니다.",
            "저는 전북대학교 학업 상담 전문 AI입니다. 과목, 교수님, 학과 정보 등에 대해 물어보세요!",
            "그 부분은 제가 도와드리기 어렵네요. 학과 정보나 수강 신청 관련 질문은 언제든 환영입니다!",
            "전북대 학사 정보 외의 질문은 답변이 어렵습니다. 교육과정이나 강좌 추천이 필요하신가요?",
            "학업과 관련된 질문만 답변 가능합니다. 전공, 수업, 학점, 학과 소개 등에 대해 궁금한 점이 있으신가요?",
            "제 역할은 전북대 학사 상담입니다. 수업 정보, 교수님 정보, 학과 안내, 커리큘럼 계획 등을 도와드릴 수 있어요!",
            "그건 제가 답변하기 어려운 주제네요. 대신 학과 추천이나 수업 계획에 대해 도와드릴까요?",
            "학업과 무관한 질문은 답변이 어렵습니다. 학과 정보나 강의 검색이 필요하시면 말씀해 주세요!",
        ]

    async def rejection_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """거절 노드 - Light 검증 실패 시 즉시 응답"""
        with NodeTimer("Rejection") as timer:
            # 랜덤하게 거절 메시지 선택
            rejection_msg = random.choice(self.rejection_messages)
            logger.warning(f"🚫 거절 응답 생성: {rejection_msg}")

            return self.add_step_time(state, {
                "final_result": rejection_msg,
                "status": "rejected"
            }, timer)

    async def finalize_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """최종 완료 노드 - 결과 정리 및 마무리"""
        with NodeTimer("Finalize") as timer:
            try:
                final_result = state.get("final_result", "처리가 완료되었습니다.")
                processing_type = state.get("processing_type", "unknown")

                execution_stats = {
                    "processing_type": processing_type,
                    "total_time": sum(state.get("step_times", {}).values()),
                    "step_count": len(state.get("step_times", {})),
                    "timestamp": datetime.now().isoformat()
                }

                logger.info("✅ 처리 완료")

                return self.add_step_time(state, {
                    "final_result": final_result,
                    "execution_stats": execution_stats,
                    "status": "completed"
                }, timer)

            except Exception as e:
                logger.error(f"❌ [FINALIZE] 오류: {e}")
                return self.add_step_time(state, {
                    "final_result": "최종 처리 중 오류가 발생했습니다.",
                    "error": str(e),
                    "status": "error"
                }, timer)

    async def error_handling_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """에러 처리 노드"""
        with NodeTimer("ErrorHandling") as timer:
            try:
                error_msg = state.get("error", "알 수 없는 오류")
                logger.error(f"🚨 [ERROR_HANDLING] 에러 처리: {error_msg}")

                return self.add_step_time(state, {
                    "final_result": "죄송합니다. 처리 중 문제가 발생했습니다. 다시 시도해 주세요.",
                    "processing_type": "error",
                    "error": error_msg,
                    "status": "error"
                }, timer)

            except Exception as e:
                logger.error(f"❌ [ERROR_HANDLING] 에러 처리 중 추가 오류: {e}")
                return {
                    "final_result": "시스템 오류가 발생했습니다.",
                    "error": str(e),
                    "status": "critical_error"
                }

    async def health_check_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """헬스체크 노드"""
        with NodeTimer("HealthCheck") as timer:
            logger.info("💊 [HEALTH_CHECK] 시스템 상태 확인")

            health_status = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "system": "langgraph_nodes",
                "version": "1.0"
            }

            return self.add_step_time(state, {
                "final_result": "시스템이 정상적으로 작동 중입니다.",
                "health_status": health_status,
                "status": "healthy"
            }, timer)

    async def debug_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """디버그 노드 - 상태 정보 출력"""
        with NodeTimer("Debug") as timer:
            logger.info("🐛 [DEBUG] 디버그 정보 수집")

            debug_info = {
                "state_keys": list(state.keys()),
                "message_count": len(state.get("messages", [])),
                "session_id": state.get("session_id", "unknown"),
                "processing_type": state.get("processing_type", "unknown"),
                "step_times": state.get("step_times", {}),
                "timestamp": datetime.now().isoformat()
            }

            logger.debug(f"🔍 [DEBUG] 상태 정보: {debug_info}")

            return self.add_step_time(state, {
                "final_result": f"디버그 정보: {debug_info}",
                "debug_info": debug_info,
                "status": "debug_complete"
            }, timer)