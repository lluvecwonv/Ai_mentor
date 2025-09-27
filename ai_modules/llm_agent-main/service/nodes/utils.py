"""
유틸리티 노드들
최종 정리, 에러 처리 등 보조 기능
"""

import logging
from typing import Dict, Any
from .base_node import BaseNode, NodeTimer

logger = logging.getLogger(__name__)


class UtilityNodes(BaseNode):
    """유틸리티 관련 노드들"""

    def finalize_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """최종 정리 노드"""
        with NodeTimer("통합 최종 정리") as timer:
            try:
                # 실행 통계 계산
                total_duration = sum(state.get("step_times", {}).values())
                step_count = len(state.get("step_times", {}))
                processing_type = state.get("processing_type", "unknown")

                # 성능 메트릭 로깅
                logger.info(f"📊 통합 실행 완료 통계:")
                logger.info(f"   처리 유형: {processing_type}")
                logger.info(f"   총 실행 시간: {total_duration:.2f}초")
                logger.info(f"   실행 단계 수: {step_count}")
                logger.info(f"   재시도 횟수: {state.get('retry_count', 0)}")
                logger.info(f"   결과 길이: {len(state.get('final_result', ''))}")

                return {
                    **state,
                    "step_times": self.update_step_time(state, "finalize", timer.duration),
                    "total_execution_time": total_duration,
                    "execution_stats": {
                        "processing_type": processing_type,
                        "total_duration": total_duration,
                        "step_count": step_count,
                        "retry_count": state.get("retry_count", 0),
                        "result_length": len(state.get("final_result", ""))
                    }
                }

            except Exception as e:
                logger.error(f"❌ 통합 최종 정리 노드 실패: {e}")
                return self.create_error_state(state, e, "finalize")

    def error_handling_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """에러 처리 노드"""
        with NodeTimer("에러 처리") as timer:
            try:
                last_error = state.get("last_error", "알 수 없는 오류")
                retry_count = state.get("retry_count", 0)
                failed_steps = state.get("failed_steps", [])

                logger.error(f"🚨 에러 처리 노드 실행:")
                logger.error(f"   마지막 오류: {last_error}")
                logger.error(f"   재시도 횟수: {retry_count}")
                logger.error(f"   실패한 단계들: {failed_steps}")

                # 에러 상황에 따른 폴백 응답
                if retry_count > 2:
                    error_response = "죄송합니다. 여러 번 시도했지만 처리 중 문제가 계속 발생합니다. 잠시 후 다시 시도해주세요."
                elif "timeout" in last_error.lower():
                    error_response = "처리 시간이 너무 오래 걸려 타임아웃이 발생했습니다. 좀 더 구체적인 질문으로 다시 시도해주세요."
                elif "connection" in last_error.lower():
                    error_response = "서버 연결에 문제가 있습니다. 잠시 후 다시 시도해주세요."
                else:
                    error_response = "처리 중 오류가 발생했습니다. 질문을 다시 확인해주시고, 문제가 계속되면 관리자에게 문의해주세요."

                return {
                    **state,
                    "final_result": error_response,
                    "processing_type": "error_handled",
                    "result_confidence": 0.1,
                    "step_times": self.update_step_time(state, "error_handling", timer.duration)
                }

            except Exception as e:
                # 에러 처리에서도 에러가 발생한 경우
                logger.critical(f"💥 에러 처리 노드에서 추가 오류: {e}")
                return {
                    **state,
                    "final_result": "심각한 시스템 오류가 발생했습니다. 관리자에게 문의해주세요.",
                    "processing_type": "critical_error",
                    "result_confidence": 0.0
                }

    def health_check_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """시스템 상태 확인 노드"""
        with NodeTimer("시스템 상태 확인") as timer:
            try:
                # 시스템 상태 확인
                health_status = {
                    "status": "healthy",
                    "timestamp": timer.start_time,
                    "memory_usage": self._get_memory_usage(),
                    "processing_queue": len(state.get("parallel_tasks", [])),
                    "active_sessions": 1  # 현재 세션
                }

                logger.info("💚 시스템 상태 정상")

                return {
                    **state,
                    "health_status": health_status,
                    "step_times": self.update_step_time(state, "health_check", timer.duration)
                }

            except Exception as e:
                logger.error(f"❌ 시스템 상태 확인 실패: {e}")
                return {
                    **state,
                    "health_status": {"status": "unhealthy", "error": str(e)}
                }

    def _get_memory_usage(self) -> Dict[str, float]:
        """메모리 사용량 체크"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            return {
                "rss_mb": memory_info.rss / 1024 / 1024,  # MB 단위
                "vms_mb": memory_info.vms / 1024 / 1024,
                "percent": process.memory_percent()
            }
        except ImportError:
            return {"message": "psutil 라이브러리가 없어 메모리 정보를 가져올 수 없습니다."}
        except Exception as e:
            return {"error": str(e)}

    def debug_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """디버그 정보 출력 노드"""
        if not state.get("debug_mode", False):
            return state

        logger.debug("🐛 디버그 모드 - 상태 덤프:")
        for key, value in state.items():
            if key in ["messages", "slots"]:
                logger.debug(f"   {key}: {type(value)} (길이: {len(value) if hasattr(value, '__len__') else 'N/A'})")
            else:
                logger.debug(f"   {key}: {value}")

        return state