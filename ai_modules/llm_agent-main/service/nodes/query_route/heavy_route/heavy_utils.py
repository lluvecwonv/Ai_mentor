"""
Heavy 노드 유틸리티 함수들
컨텍스트 구성 및 쿼리 개선 로직
"""

from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


def build_context(previous_results: List[Dict[str, Any]]) -> Dict[str, Any]:

    context = {
        "department": None,
        "courses": [],
        "sql_results": [],
        "curriculum_info": None,
        "step_count": len(previous_results)
    }

    for result in previous_results:
        agent_type = result.get("agent_type", "")
        result_data = result.get("result", "")

        if agent_type == "department_mapping":
            context["department"] = result_data
        elif agent_type == "vector_search":
            if isinstance(result_data, list):
                context["courses"] = result_data[:5]  # 상위 5개만
            else:
                context["courses"] = []
        elif agent_type == "sql_query":
            context["sql_results"].append(result_data)
        elif agent_type == "curriculum":
            context["curriculum_info"] = result_data

    return context


def enhance_query(agent_name: str, user_message: str, context: Dict[str, Any]) -> str:

    if agent_name == "Department-Mapping-Agent":
        return user_message  # 첫 번째 단계

    dept = context.get("department")
    courses = context.get("courses", [])

    if agent_name == "FAISS-Search-Agent":
        # 학과명이 있으면 쿼리에 포함하여 더 정확한 검색
        if dept:
            return f"{dept} {user_message}"
        return user_message

    elif agent_name == "SQL-Agent":
        # 이전 결과들을 참고 정보로 추가
        context_parts = []
        if dept:
            context_parts.append(f"학과: {dept}")
        if courses:
            course_names = [c.get("name", "") for c in courses[:3] if c.get("name")]
            if course_names:
                context_parts.append(f"관련 과목: {', '.join(course_names)}")

        if context_parts:
            return f"{user_message} (참고: {' | '.join(context_parts)})"
        return user_message

    elif agent_name == "Curriculum-Agent":
        # 모든 이전 결과 활용
        context_parts = []
        if dept:
            context_parts.append(f"학과: {dept}")
        if courses:
            context_parts.append(f"과목 수: {len(courses)}")
        if context.get("sql_results"):
            context_parts.append("DB 조회 완료")

        if context_parts:
            return f"{user_message} (이전 분석: {' | '.join(context_parts)})"
        return user_message

    elif agent_name == "LLM-Fallback-Agent":
        # LLM 폴백: 모든 컨텍스트 활용
        context_summary = []
        if dept:
            context_summary.append(dept)
        if courses:
            context_summary.append(f"{len(courses)}개 과목")

        if context_summary:
            return f"{user_message} (컨텍스트: {' '.join(context_summary)})"
        return user_message

    return user_message



def log_execution_info(agent_name: str, user_message: str, enhanced_query: str, context: Dict[str, Any]) -> None:
    """실행 정보 로깅

    Args:
        agent_name: 에이전트 이름
        user_message: 원본 메시지
        enhanced_query: 개선된 쿼리
        context: 컨텍스트 정보
    """
    logger.info(f"[HEAVY] {agent_name} 실행")
    logger.info(f"[HEAVY] Original: {user_message}")
    if user_message != enhanced_query:
        logger.info(f"[HEAVY] Enhanced: {enhanced_query}")
    logger.info(f"[HEAVY] Context: {context}")