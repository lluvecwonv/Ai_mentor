"""
유틸리티 노드들
완료, 에러 처리, 헬스체크 등 공통 기능들
"""

import logging
from typing import Dict, Any
from datetime import datetime
from .base_node import BaseNode, NodeTimer

logger = logging.getLogger(__name__)


class UtilityNodes(BaseNode):
    """유틸리티 노드들"""

    def __init__(self):
        pass

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