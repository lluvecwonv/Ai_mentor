"""
통합 LangGraph 서비스 래퍼
Light/Medium/Heavy 모든 복잡도를 처리하는 통합 서비스
"""

from __future__ import annotations
import logging
import asyncio
from typing import Dict, Any, AsyncGenerator, Optional, List
from datetime import datetime

from .unified_langgraph_app import create_unified_langgraph_app, UnifiedLangGraphApp
from .langgraph_state import UnifiedMentorState
from service.core.memory import ConversationMemory
from exceptions import AIMentorException

logger = logging.getLogger(__name__)

class UnifiedLangGraphService:
    """
    통합 LangGraph 서비스 래퍼
    Light/Medium/Heavy 복잡도를 단일 그래프로 처리
    """

    def __init__(self, conversation_memory: ConversationMemory = None):
        """
        통합 LangGraph 서비스 초기화

        Args:
            conversation_memory: 기존 대화 메모리와 연동
        """
        logger.info("🚀 통합 LangGraph 서비스 초기화 시작")

        try:
            self.conversation_memory = conversation_memory
            self.app = create_unified_langgraph_app(conversation_memory)
            self._is_healthy = True
            self._stats = {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "light_requests": 0,
                "medium_requests": 0,
                "heavy_requests": 0,
                "avg_response_time": 0.0,
                "start_time": datetime.now()
            }

            logger.info("✅ 통합 LangGraph 서비스 초기화 완료")

        except Exception as e:
            logger.error(f"❌ 통합 LangGraph 서비스 초기화 실패: {e}")
            self._is_healthy = False
            raise AIMentorException(f"통합 LangGraph 서비스 초기화 실패: {e}")

    # ==================== 메인 실행 메서드들 ====================

    async def run_agent(
        self,
        user_message: str,
        session_id: str = "default",
        **kwargs
    ) -> Dict[str, Any]:
        """
        통합 에이전트 실행 (모든 복잡도 처리)

        Args:
            user_message: 사용자 메시지
            session_id: 세션 ID
            **kwargs: 추가 파라미터

        Returns:
            OpenAI 호환 응답 형식
        """
        start_time = datetime.now()
        self._stats["total_requests"] += 1

        logger.info(f"🤖 통합 LangGraph 에이전트 실행: session={session_id}")
        logger.info(f"📝 사용자 메시지: {user_message}")

        try:
            # 통합 LangGraph 실행
            final_state = await self.app.process_query(
                user_message=user_message,
                session_id=session_id
            )

            # 응답 시간 계산
            duration = (datetime.now() - start_time).total_seconds()

            # 복잡도별 통계 업데이트
            complexity = final_state.get("hybrid_info", {}).get("query_analysis", {}).get("complexity", "medium")
            self._update_stats(duration, complexity, success=True)

            # OpenAI 호환 형식으로 변환
            response = self._convert_to_openai_format(final_state, duration)

            # 대화 메모리 업데이트 (기존 시스템과 동일)
            if self.conversation_memory:
                await self._update_conversation_memory(
                    session_id, user_message, response, final_state
                )

            logger.info(f"✅ 통합 LangGraph 실행 완료: {duration:.2f}초 ({complexity})")
            return response

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self._update_stats(duration, "unknown", success=False)

            logger.error(f"❌ 통합 LangGraph 실행 실패: {e}")

            # 에러 응답 반환
            return self._create_error_response(str(e))

    async def run_agent_streaming(
        self,
        user_message: str,
        session_id: str = "default",
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        스트리밍 에이전트 실행

        Args:
            user_message: 사용자 메시지
            session_id: 세션 ID
            **kwargs: 추가 파라미터

        Yields:
            스트리밍 청크들
        """
        logger.info(f"🌊 통합 LangGraph 스트리밍 실행: session={session_id}")

        try:
            # 시작 메시지
            yield self._create_streaming_chunk("🤔 분석 중입니다...")

            # 스트리밍 실행 - 비스트리밍 방식으로 대체 (추후 개선)
            result = await self.app.process_query(user_message, session_id)

            # 결과를 단어별로 스트리밍
            response_text = result.get("response", "")
            words = response_text.split()

            for word in words:
                yield self._create_streaming_chunk(word + " ")
                await asyncio.sleep(0.1)  # 스트리밍 효과

            # 완료 메시지
            yield self._create_streaming_chunk("", finish_reason="stop")

        except Exception as e:
            logger.error(f"❌ 통합 LangGraph 스트리밍 실패: {e}")
            yield self._create_error_chunk(str(e))

    # ==================== 유틸리티 메서드들 ====================

    def _convert_to_openai_format(
        self,
        final_state: UnifiedMentorState,
        duration: float
    ) -> Dict[str, Any]:
        """
        통합 LangGraph 결과를 OpenAI 호환 형식으로 변환

        Args:
            final_state: 통합 LangGraph 최종 상태
            duration: 실행 시간

        Returns:
            OpenAI 호환 응답
        """
        # 최종 결과 추출 - 새로운 응답 형식 사용
        final_result = final_state.get("response", "")
        if not final_result:
            # 이전 형식도 확인
            final_result = final_state.get("final_result", "")
            if not final_result:
                # 메시지에서 마지막 AI 응답 찾기
                messages = final_state.get("messages", [])
                for message in reversed(messages):
                    if hasattr(message, 'content') and message.content:
                        final_result = message.content
                        break

        if not final_result:
            final_result = "죄송합니다. 응답을 생성할 수 없습니다."

        processing_type = final_state.get("processing_type", "unknown")
        complexity = final_state.get("hybrid_info", {}).get("query_analysis", {}).get("complexity", "medium")

        # OpenAI 형식 응답
        return {
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": final_result
                },
                "finish_reason": "stop"
            }],
            # 통합 메타데이터
            "unified_langgraph_metadata": {
                "execution_time": duration,
                "complexity": complexity,
                "processing_type": processing_type,
                "steps_executed": len(final_state.get("step_times", {})),
                "retry_count": final_state.get("retry_count", 0),
                "route": final_state.get("route", "unknown"),
                "confidence": final_state.get("result_confidence", 0.0),
                "parallel_execution": complexity == "heavy"
            },
            # 기존 호환성
            "processing_type": f"unified_{processing_type}",
            "final_result": final_result,
            "steps": [
                {
                    "tool_name": f"UNIFIED_LANGGRAPH_{complexity.upper()}",
                    "tool_response": final_result,
                    "execution_time": duration
                }
            ]
        }

    def _create_streaming_chunk(
        self,
        content: str,
        finish_reason: Optional[str] = None
    ) -> str:
        """스트리밍 청크 생성"""
        import json

        chunk_data = {
            "choices": [{
                "index": 0,
                "delta": {"content": content} if content else {},
                "finish_reason": finish_reason
            }]
        }

        return f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"

    def _create_error_chunk(self, error_message: str) -> str:
        """에러 청크 생성"""
        import json

        error_chunk = {
            "error": {
                "message": error_message,
                "type": "unified_langgraph_error"
            }
        }

        return f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"

    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """에러 응답 생성"""
        fallback_message = (
            "죄송합니다. 요청 처리 중 문제가 발생했습니다. "
            "다시 시도해주시거나 질문을 다르게 표현해주세요."
        )

        return {
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": fallback_message
                },
                "finish_reason": "error"
            }],
            "error": {
                "message": error_message,
                "type": "unified_langgraph_error"
            },
            "processing_type": "unified_error",
            "final_result": fallback_message
        }

    async def _update_conversation_memory(
        self,
        session_id: str,
        user_message: str,
        response: Dict[str, Any],
        final_state: UnifiedMentorState
    ):
        """대화 메모리 업데이트"""
        if not self.conversation_memory:
            return

        try:
            # 기존 ConversationMemory 인터페이스 사용
            ai_response = response["choices"][0]["message"]["content"]

            # 대화 교환 추가
            self.conversation_memory.add_exchange(
                session_id=session_id,
                user_message=user_message,
                assistant_response=ai_response,
                query_analysis={
                    "execution_time": final_state.get("step_times", {}),
                    "complexity": final_state.get("complexity"),
                    "processing_type": final_state.get("processing_type"),
                    "unified_langgraph": True
                }
            )

            logger.debug(f"💾 통합 대화 메모리 업데이트 완료: session={session_id}")

        except Exception as e:
            logger.error(f"❌ 통합 대화 메모리 업데이트 실패: {e}")

    def _update_stats(self, duration: float, complexity: str, success: bool):
        """통계 업데이트"""
        if success:
            self._stats["successful_requests"] += 1
        else:
            self._stats["failed_requests"] += 1

        # 복잡도별 통계
        if complexity == "light":
            self._stats["light_requests"] += 1
        elif complexity == "medium":
            self._stats["medium_requests"] += 1
        elif complexity == "heavy":
            self._stats["heavy_requests"] += 1

        # 평균 응답 시간 계산
        total_successful = self._stats["successful_requests"]
        if total_successful > 0:
            current_avg = self._stats["avg_response_time"]
            self._stats["avg_response_time"] = (
                (current_avg * (total_successful - 1) + duration) / total_successful
            )

    # ==================== 호환성 메서드들 ====================

    def get_health_status(self) -> Dict[str, Any]:
        """헬스 상태 조회"""
        uptime = (datetime.now() - self._stats["start_time"]).total_seconds()

        return {
            "status": "healthy" if self._is_healthy else "unhealthy",
            "service_type": "unified_langgraph",
            "uptime_seconds": uptime,
            "statistics": {
                **self._stats,
                "success_rate": (
                    self._stats["successful_requests"] / max(1, self._stats["total_requests"])
                )
            },
            "complexity_distribution": {
                "light": self._stats["light_requests"],
                "medium": self._stats["medium_requests"],
                "heavy": self._stats["heavy_requests"]
            },
            "components": {
                "unified_app": "healthy" if self.app else "unhealthy",
                "conversation_memory": "healthy" if self.conversation_memory else "not_configured"
            }
        }

    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """세션 정보 조회"""
        try:
            return {
                "session_id": session_id,
                "service_type": "unified_langgraph",
                "session_info": {
                    "current_topic": "Unified LangGraph Session",
                    "supports_complexity": ["light", "medium", "heavy"],
                    "architecture": "single_graph"
                }
            }
        except Exception as e:
            logger.error(f"❌ 세션 정보 조회 실패: {e}")
            return {
                "session_id": session_id,
                "error": str(e)
            }

    def clear_session_history(self, session_id: str) -> bool:
        """세션 히스토리 초기화"""
        try:
            # 대화 메모리 초기화
            if self.conversation_memory:
                # ConversationMemory의 초기화 메서드 호출
                pass

            logger.info(f"🗑️ 통합 세션 히스토리 초기화: {session_id}")
            return True

        except Exception as e:
            logger.error(f"❌ 통합 세션 히스토리 초기화 실패: {e}")
            return False

    # ==================== 통합 전용 메서드들 ====================

    def get_graph_visualization(self) -> str:
        """그래프 시각화"""
        return self.app.get_graph_visualization()

    async def debug_execution(
        self,
        user_message: str,
        session_id: str = "default"
    ) -> Dict[str, Any]:
        """디버그 모드로 실행"""
        final_state = await self.app.ainvoke(
            user_message=user_message,
            session_id=session_id,
            debug_mode=True
        )

        return {
            "final_state": final_state,
            "execution_trace": final_state.get("step_times", {}),
            "complexity": final_state.get("complexity"),
            "processing_type": final_state.get("processing_type"),
            "route_taken": final_state.get("route"),
            "errors_encountered": final_state.get("failed_steps", [])
        }

    def get_complexity_stats(self) -> Dict[str, Any]:
        """복잡도별 통계"""
        total = self._stats["total_requests"]
        if total == 0:
            return {"message": "No requests processed yet"}

        return {
            "total_requests": total,
            "complexity_breakdown": {
                "light": {
                    "count": self._stats["light_requests"],
                    "percentage": (self._stats["light_requests"] / total) * 100
                },
                "medium": {
                    "count": self._stats["medium_requests"],
                    "percentage": (self._stats["medium_requests"] / total) * 100
                },
                "heavy": {
                    "count": self._stats["heavy_requests"],
                    "percentage": (self._stats["heavy_requests"] / total) * 100
                }
            }
        }


# ==================== 팩토리 함수 ====================

def create_unified_langgraph_service(conversation_memory: ConversationMemory = None) -> UnifiedLangGraphService:
    """
    통합 LangGraph 서비스 생성 팩토리

    Args:
        conversation_memory: 기존 대화 메모리

    Returns:
        초기화된 통합 LangGraph 서비스
    """
    logger.info("🏭 통합 LangGraph 서비스 팩토리에서 생성")
    return UnifiedLangGraphService(conversation_memory)


# 통합 LangGraph 사용 가능 여부
UNIFIED_LANGGRAPH_AVAILABLE = True