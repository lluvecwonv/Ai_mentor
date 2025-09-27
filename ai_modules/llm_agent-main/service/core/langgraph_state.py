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

class UnifiedMentorState(TypedDict):
    """
    통합 멘토링 상태 정의

    Light/Medium/Heavy 모든 복잡도를 하나의 LangGraph에서 처리:
    - LLM 기반 실행 계획 생성
    - 순차/병렬/하이브리드 실행 지원
    - Tree of Thoughts 패턴 통합
    - 의존성 그래프 처리
    """

    # 🔄 메시지 히스토리 (LangGraph 표준)
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # 🧠 LLM 기반 실행 계획
    execution_plan: Optional[Dict[str, Any]]  # LLM이 생성한 실행 계획
    execution_type: str  # "sequential", "parallel", "hybrid"
    complexity_level: str  # "light", "medium", "heavy"

    # 📊 단계별 실행 관리
    current_step: int  # 현재 실행 중인 단계 번호
    total_steps: int  # 전체 단계 수
    step_results: Dict[str, Any]  # 각 단계의 실행 결과

    # 🔗 의존성 그래프 관리
    dependencies: Dict[str, List[str]]  # step_id -> [dependency_step_ids]
    ready_steps: List[str]  # 실행 준비된 단계들
    completed_steps: List[str]  # 완료된 단계들

    # 🌳 Tree of Thoughts 지원
    result_candidates: List[Dict[str, Any]]  # 여러 실행 경로의 결과 후보들
    candidate_scores: Dict[str, float]  # 각 후보의 LLM 평가 점수
    best_candidate: Optional[Dict[str, Any]]  # LLM이 선택한 최선의 결과

    # 🔍 컨텍스트 정보
    user_query: str  # 원본 사용자 쿼리
    clean_user_message: Optional[str]  # 맥락 분석 후 정리된 메시지
    session_id: str  # 세션 ID
    conversation_context: Optional[str]  # 이전 대화 맥락
    conversation_memory: Optional[Any]  # ConversationMemory 인스턴스
    context_analysis: Optional[Dict[str, Any]]  # 맥락 분석 결과
    needs_history: bool  # 히스토리가 필요한지 여부

    # 📋 중간 데이터 저장소
    data_slots: Dict[str, Any]  # 각 에이전트/단계별 중간 결과
    slots: Annotated[Dict[str, Any], merge_dicts]  # 병렬 노드용 중간 결과 (병합 지원)

    # ⚠️ 에러 처리 및 복구
    last_error: Optional[str]  # 마지막 에러 메시지
    retry_count: int  # 재시도 횟수
    failed_steps: List[str]  # 실패한 단계들

    # 🎯 라우팅 및 제어
    route: Optional[str]  # 현재 처리 경로
    next_action: Optional[str]  # 다음 실행할 액션
    complexity: Optional[str]  # 복잡도 (light/medium/heavy)
    plan: List[Dict[str, Any]]  # 실행 계획
    routing_reason: Optional[str]  # 라우팅 이유
    plan_confidence: float  # 계획 신뢰도
    expanded_query: Optional[str]  # 확장된 쿼리
    keywords: Optional[str]  # 추출된 키워드
    parallel_tasks: List[str]  # 병렬 실행 태스크 목록
    processing_type: Optional[str]  # 처리 타입
    final_result: Optional[str]  # 최종 결과

    # ❓ Human-in-the-loop 지원
    need_more_info: bool  # 추가 정보 필요 여부
    clarification_question: Optional[str]  # 명확화 질문

    # 📈 성능 메트릭
    start_time: Optional[float]  # 처리 시작 시간
    step_times: Annotated[Dict[str, float], merge_dicts]  # 각 단계 실행 시간 (동시 업데이트 지원)
    total_execution_time: float  # 총 실행 시간

    # 🔧 실행 설정
    parallel_limit: int  # 최대 병렬 실행 수
    timeout_seconds: int  # 단계별 타임아웃
    debug_mode: bool  # 디버그 모드

    # 📋 최종 결과
    final_result: Optional[str]  # 최종 합성된 결과
    result_confidence: float  # 결과 신뢰도 (0.0-1.0)


def create_initial_state(
    user_message: str,
    session_id: str = "default",
    debug_mode: bool = False,
    conversation_context: Optional[str] = None
) -> UnifiedMentorState:
    """
    통합 멘토링 상태 초기화

    Args:
        user_message: 사용자 메시지
        session_id: 세션 ID
        debug_mode: 디버그 모드
        conversation_context: 이전 대화 맥락

    Returns:
        초기화된 UnifiedMentorState
    """
    logger.info(f"🆕 통합 멘토링 상태 생성: session={session_id}, debug={debug_mode}")

    return UnifiedMentorState(
        # 메시지 히스토리
        messages=[HumanMessage(content=user_message)],

        # 실행 계획 (LLM이 생성할 예정)
        execution_plan=None,
        execution_type="unknown",  # planning 단계에서 결정
        complexity_level="unknown",  # planning 단계에서 결정

        # 단계별 실행 관리
        current_step=0,
        total_steps=0,
        step_results={},

        # 의존성 그래프
        dependencies={},
        ready_steps=[],
        completed_steps=[],

        # Tree of Thoughts
        result_candidates=[],
        candidate_scores={},
        best_candidate=None,

        # 컨텍스트
        user_query=user_message,
        clean_user_message=None,  # router에서 설정됨
        session_id=session_id,
        conversation_context=conversation_context,
        conversation_memory=None,  # 런타임에 주입됨
        context_analysis=None,  # router에서 설정됨
        needs_history=False,  # 기본값

        # 데이터 저장소
        data_slots={},

        # 에러 처리
        last_error=None,
        retry_count=0,
        failed_steps=[],

        # 라우팅
        route=None,
        next_action="planning",  # 항상 planning부터 시작

        # Human-in-the-loop
        need_more_info=False,
        clarification_question=None,

        # 성능 메트릭
        start_time=None,
        step_times={},
        total_execution_time=0.0,

        # 실행 설정
        parallel_limit=3,  # 최대 3개 병렬 실행
        timeout_seconds=30,  # 단계별 30초 타임아웃
        debug_mode=debug_mode,

        # 최종 결과
        final_result=None,
        result_confidence=0.0
    )


# 상태 조작 헬퍼 함수들

def get_user_message(state: UnifiedMentorState) -> str:
    """상태에서 최신 사용자 메시지 추출"""
    for message in reversed(state["messages"]):
        if isinstance(message, HumanMessage):
            return message.content
    return state["user_query"]


def add_ai_message(state: UnifiedMentorState, content: str) -> UnifiedMentorState:
    """AI 메시지를 상태에 추가"""
    return {
        **state,
        "messages": state["messages"] + [AIMessage(content=content)]
    }


def update_data_slot(state: UnifiedMentorState, key: str, value: Any) -> UnifiedMentorState:
    """데이터 슬롯 업데이트"""
    new_slots = state["data_slots"].copy()
    new_slots[key] = value
    return {**state, "data_slots": new_slots}


def add_step_result(state: UnifiedMentorState, step_id: str, result: Any) -> UnifiedMentorState:
    """단계 실행 결과 추가"""
    new_results = state["step_results"].copy()
    new_results[step_id] = result
    return {**state, "step_results": new_results}


def mark_step_completed(state: UnifiedMentorState, step_id: str) -> UnifiedMentorState:
    """단계 완료 처리"""
    completed = state["completed_steps"].copy()
    if step_id not in completed:
        completed.append(step_id)
    return {**state, "completed_steps": completed}


def add_step_time(state: UnifiedMentorState, step_name: str, duration: float) -> Dict[str, float]:
    """단계 실행 시간 기록 (Annotated 타입용)"""
    return {step_name: duration}


def increment_retry(state: UnifiedMentorState) -> UnifiedMentorState:
    """재시도 카운트 증가"""
    return {**state, "retry_count": state["retry_count"] + 1}


def add_result_candidate(state: UnifiedMentorState, candidate: Dict[str, Any], score: float) -> UnifiedMentorState:
    """ToT 결과 후보 추가"""
    candidates = state["result_candidates"].copy()
    candidates.append(candidate)

    scores = state["candidate_scores"].copy()
    candidate_id = f"candidate_{len(candidates)}"
    scores[candidate_id] = score

    return {
        **state,
        "result_candidates": candidates,
        "candidate_scores": scores
    }


def get_ready_steps(state: UnifiedMentorState) -> List[str]:
    """실행 준비된 단계들 반환 (의존성이 모두 완료된 단계들)"""
    dependencies = state["dependencies"]
    completed_steps = set(state["completed_steps"])

    ready_steps = []
    for step_id, deps in dependencies.items():
        if step_id not in completed_steps:
            if all(dep in completed_steps for dep in deps):
                ready_steps.append(step_id)

    return ready_steps


def should_continue(state: UnifiedMentorState) -> bool:
    """계속 실행할지 판단"""
    # 최대 재시도 횟수 체크
    if state["retry_count"] > 3:
        logger.warning(f"최대 재시도 횟수 초과: {state['retry_count']}")
        return False

    # 최종 결과가 있으면 종료
    if state["final_result"]:
        return False

    # 추가 정보가 필요하면 human 노드로
    if state["need_more_info"]:
        return True

    # 모든 단계가 완료되면 종료
    if state["total_steps"] > 0 and len(state["completed_steps"]) >= state["total_steps"]:
        return False

    return True


class UnifiedStateUtils:
    """통합 상태 관련 유틸리티 함수들"""

    @staticmethod
    def log_state_transition(state: UnifiedMentorState, from_node: str, to_node: str):
        """상태 전이 로깅"""
        logger.info(f"🔄 상태 전이: {from_node} → {to_node}")
        logger.debug(f"   복잡도: {state.get('complexity_level', 'unknown')}")
        logger.debug(f"   실행 타입: {state.get('execution_type', 'unknown')}")
        logger.debug(f"   현재 단계: {state.get('current_step', 0)}/{state.get('total_steps', 0)}")
        logger.debug(f"   완료된 단계: {len(state.get('completed_steps', []))}")
        logger.debug(f"   재시도: {state.get('retry_count', 0)}")

    @staticmethod
    def get_execution_summary(state: UnifiedMentorState) -> str:
        """실행 요약 생성"""
        completed = len(state.get("completed_steps", []))
        total = state.get("total_steps", 0)
        total_time = sum(state.get("step_times", {}).values())
        retry_count = state.get("retry_count", 0)
        complexity = state.get("complexity_level", "unknown")

        return f"복잡도: {complexity}, 진행: {completed}/{total}, 실행시간: {total_time:.2f}초, 재시도: {retry_count}"

    @staticmethod
    def is_valid_state(state: UnifiedMentorState) -> bool:
        """상태 유효성 검사"""
        required_fields = ["messages", "user_query", "session_id", "execution_type", "complexity_level"]
        return all(field in state for field in required_fields)

    @staticmethod
    def get_progress_percentage(state: UnifiedMentorState) -> float:
        """진행률 계산 (0.0-1.0)"""
        total_steps = state.get("total_steps", 0)
        if total_steps == 0:
            return 0.0

        completed_steps = len(state.get("completed_steps", []))
        return min(completed_steps / total_steps, 1.0)

    @staticmethod
    def estimate_remaining_time(state: UnifiedMentorState) -> float:
        """남은 실행 시간 추정 (초)"""
        step_times = state.get("step_times", {})
        if not step_times:
            return 0.0

        avg_step_time = sum(step_times.values()) / len(step_times)
        completed_steps = len(state.get("completed_steps", []))
        total_steps = state.get("total_steps", 0)

        remaining_steps = max(total_steps - completed_steps, 0)
        return remaining_steps * avg_step_time

    @staticmethod
    def get_best_candidate_by_score(state: UnifiedMentorState) -> Optional[Dict[str, Any]]:
        """점수가 가장 높은 결과 후보 반환"""
        candidates = state.get("result_candidates", [])
        scores = state.get("candidate_scores", {})

        if not candidates or not scores:
            return None

        best_score = -1.0
        best_candidate = None

        for i, candidate in enumerate(candidates):
            candidate_id = f"candidate_{i+1}"
            score = scores.get(candidate_id, 0.0)
            if score > best_score:
                best_score = score
                best_candidate = candidate

        return best_candidate