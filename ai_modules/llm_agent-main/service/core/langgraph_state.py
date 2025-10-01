"""
LangGraph용 통합 멘토링 상태 정의
Light/Medium/Heavy를 모두 하나의 LangGraph에서 처리하는 통합 아키텍처
"""

from typing import TypedDict, List, Dict, Any, Optional, Sequence
try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import add_messages
from operator import add
import logging

logger = logging.getLogger(__name__)

def merge_dicts(left: Dict, right: Dict) -> Dict:
    """병렬 노드에서 Dict를 병합하는 함수"""
    if left is None:
        return right
    if right is None:
        return left
    # 두 dict를 병합 (right가 left를 덮어씀)
    return {**left, **right}

class GraphState(TypedDict):
    """통합 멘토링 상태"""

    # 메시지 히스토리
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # 기본 정보
    user_query: str
    session_id: str
    conversation_memory: Optional[Any]

    # 라우팅
    route: Optional[str]
    complexity: Optional[str]
    plan: List[Dict[str, Any]]
    routing_reason: Optional[str]
    expanded_query: Optional[str]
    keywords: Optional[str]

    # 처리 결과
    slots: Annotated[Dict[str, Any], merge_dicts]
    processing_type: Optional[str]
    final_result: Optional[str]

    # 실행 시간
    step_times: Annotated[Dict[str, float], merge_dicts]
    retry_count: int

    # 병렬 태스크
    parallel_tasks: List[str]

    # 스트리밍 콜백
    stream_callback: Optional[Any]


def create_initial_state(
    user_message: str,
    session_id: str = "default"
) -> GraphState:
    """상태 초기화"""
    return GraphState(
        messages=[HumanMessage(content=user_message)],
        user_query=user_message,
        session_id=session_id,
        conversation_memory=None,
        route=None,
        complexity=None,
        plan=[],
        routing_reason=None,
        expanded_query=None,
        keywords=None,
        slots={},
        processing_type=None,
        final_result=None,
        step_times={},
        retry_count=0,
        parallel_tasks=[],
        stream_callback=None
    )


def get_user_message(state: GraphState) -> str:
    """최신 사용자 메시지 추출"""
    for message in reversed(state["messages"]):
        if isinstance(message, HumanMessage):
            return message.content
    return state["user_query"]