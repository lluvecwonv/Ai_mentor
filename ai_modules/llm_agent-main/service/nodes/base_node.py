"""
LangGraph 노드들의 기본 클래스 및 공통 유틸리티
"""

import time
import logging
from typing import Dict, Any, List
from langchain_core.messages import BaseMessage, HumanMessage

logger = logging.getLogger(__name__)


class BaseNode:
    """모든 노드들의 기본 클래스"""

    @staticmethod
    def get_user_message(state: Dict[str, Any]) -> str:
        """상태에서 최신 사용자 메시지 추출"""
        messages = state.get("messages", [])
        for message in reversed(messages):
            if isinstance(message, HumanMessage):
                return message.content
        return state.get("user_query", "")

    @staticmethod
    def update_step_time(state: Dict[str, Any], step_name: str, duration: float) -> Dict[str, float]:
        """단계 실행 시간 업데이트 (Annotated 타입용)"""
        return {step_name: duration}

    @staticmethod
    def update_slots(state: Dict[str, Any], key: str, value: Any) -> Dict[str, Any]:
        """데이터 슬롯 업데이트"""
        slots = state.get("slots", {}).copy()
        slots[key] = value
        return slots

    @staticmethod
    def add_failed_step(state: Dict[str, Any], step_name: str) -> List[str]:
        """실패한 단계 추가"""
        failed_steps = state.get("failed_steps", []).copy()
        if step_name not in failed_steps:
            failed_steps.append(step_name)
        return failed_steps

    @staticmethod
    def create_error_state(state: Dict[str, Any], error: Exception, step_name: str) -> Dict[str, Any]:
        """에러 상태 생성"""
        return {
            **state,
            "last_error": str(error),
            "failed_steps": BaseNode.add_failed_step(state, step_name)
        }


class NodeTimer:
    """노드 실행 시간 측정 컨텍스트 매니저"""

    def __init__(self, node_name: str):
        self.node_name = node_name
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        logger.info(f"⏱️ {self.node_name} 노드 실행 시작")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        if exc_type is None:
            logger.info(f"✅ {self.node_name} 노드 완료 ({duration:.2f}초)")
        else:
            logger.error(f"❌ {self.node_name} 노드 실패 ({duration:.2f}초): {exc_val}")

    @property
    def duration(self):
        return time.time() - self.start_time if self.start_time else 0