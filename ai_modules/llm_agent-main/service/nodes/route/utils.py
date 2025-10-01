"""라우팅 노드에서 사용하는 피드백 메시지 생성 유틸리티"""


def generate_initial_feedback(query: str) -> str:
    """질문 접수 즉시 피드백 메시지 생성"""
    query_lower = query.lower()

    # 커리큘럼 관련
    if any(word in query_lower for word in ["커리큘럼", "로드맵", "어떤 수업", "수업 추천"]):
        return "💡 질문을 분석하고 있습니다..."

    # 교수 관련
    if any(word in query_lower for word in ["교수", "강사", "누가 가르"]):
        return "🔍 질문을 분석하고 있습니다..."

    # 과목/수업 관련
    if any(word in query_lower for word in ["과목", "수업", "강의", "들으면"]):
        return "📚 질문을 분석하고 있습니다..."

    # 학과 관련
    if any(word in query_lower for word in ["학과", "전공", "학부"]):
        return "🏫 질문을 분석하고 있습니다..."

    # 기본
    return "🤔 질문을 분석하고 있습니다..."


def generate_routing_feedback(complexity: str, owner_hint: str, category: str, query: str) -> str:
    """라우팅 결과 기반 사용자 피드백 메시지 생성"""

    # Curriculum 관련
    if "CURRICULUM" in owner_hint.upper():
        return "💡 커리큘럼 추천을 준비하고 있습니다."

    # SQL/DB 검색
    if "SQL" in owner_hint.upper() or "DB" in owner_hint.upper():
        if "professor" in category or "교수" in query:
            return "🔍 교수님 정보를 찾고 있습니다..."
        elif "course" in category or "과목" in query or "수업" in query:
            return "📚 관련 수업 정보를 검색하고 있습니다..."
        elif "department" in category or "학과" in query:
            return "🏫 학과 정보를 조회하고 있습니다."

    # Vector/FAISS 검색
    if "VECTOR" in owner_hint.upper() or "FAISS" in owner_hint.upper():
        return "🔎 관련 강의 내용을 찾아보고 있습니다."

    # Department mapping
    if "DEPARTMENT" in owner_hint.upper():
        return "🗺️ 학과 정보를 분석하고 있습니다."

    return ""  # 기본적으로 메시지 없음
