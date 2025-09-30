import os
import json
import logging
import networkx as nx
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)

# 디렉토리 설정
BASE_DIR = Path(__file__).resolve().parent
RESULT_DIR = BASE_DIR / "result"
QUERY_DIR = RESULT_DIR / "query_datetime"
SELECT_DIR = RESULT_DIR / "selected_by_llm"

# 디렉토리 생성
QUERY_DIR.mkdir(parents=True, exist_ok=True)
SELECT_DIR.mkdir(parents=True, exist_ok=True)


def load_txt(file_path: str) -> str:
    """텍스트 파일 로드"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def get_llm_client(model: str = "gpt-4o-mini", temperature: float = 0.1, max_tokens: int = None) -> ChatOpenAI:
    """LangChain LLM 클라이언트 생성"""
    kwargs = {
        "model": model,
        "temperature": temperature,
        "openai_api_key": os.getenv("OPENAI_API_KEY")
    }
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    return ChatOpenAI(**kwargs)


def query_expansion(client, query: str, load_path: str) -> str:
    """쿼리 확장"""
    prompt_template = load_txt(load_path)
    formatted_prompt = prompt_template.replace("{input_query}", query)

    llm = get_llm_client("gpt-4o-mini")

    messages = [
        SystemMessage(content="당신은 교육 전문가입니다. 사용자의 쿼리를 확장하여 더 나은 검색 결과를 제공하세요."),
        HumanMessage(content=formatted_prompt)
    ]

    response = llm.invoke(messages)
    response_text = response.content

    # 결과 저장
    timestamp = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
    save_path = QUERY_DIR / f"{timestamp}.json"
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump({"query": query, "response": response_text}, f, ensure_ascii=False, indent=2)

    return response_text


def llm_select_departments(query: str, candidate_depts: List[Dict], target_count: int) -> List[Dict]:
    """LLM을 사용한 학과 선택"""
    if len(candidate_depts) <= target_count:
        return candidate_depts

    llm = get_llm_client()

    dept_info = "\n".join([
        f"{i+1}. {dept['department_name']} (점수: {dept['score']:.3f})"
        for i, dept in enumerate(candidate_depts)
    ])

    system_prompt = """당신은 교육 전문가입니다.
사용자의 쿼리와 가장 관련성이 높은 학과들을 선택해주세요.
반드시 JSON 형식으로 응답해주세요: {"selected_departments": [학과명1, 학과명2, ...]}"""

    user_prompt = f"""
쿼리: "{query}"

후보 학과들:
{dept_info}

위 후보 중에서 쿼리와 가장 관련성이 높은 {target_count}개 학과를 선택해주세요.
"""

    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        response = llm.invoke(messages)
        result = json.loads(response.content)
        selected_names = result.get("selected_departments", [])

        # 선택된 학과 정보 반환
        selected_depts = []
        for name in selected_names:
            for dept in candidate_depts:
                if dept["department_name"] == name:
                    selected_depts.append(dept)
                    break

        return selected_depts[:target_count]

    except Exception as e:
        logger.warning(f"LLM 학과 선택 실패, 상위 점수 기준으로 선택: {e}")
        return candidate_depts[:target_count]


def create_prerequisite(client, class_info: List[Dict[str, Any]], load_path: str) -> str:
    """선수과목 관계 생성"""
    prompt_template = load_txt(load_path)
    class_info_str = json.dumps(class_info, ensure_ascii=False, indent=2)
    formatted_prompt = prompt_template.replace("{class_info}", class_info_str)

    llm = get_llm_client()

    system_prompt = """당신은 교육과정 전문가입니다.
과목 정보를 분석하여 논리적인 선수과목 구조를 제안해주세요."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=formatted_prompt)
    ]

    response = llm.invoke(messages)
    return response.content


def get_course_relationship(course1: Dict, course2: Dict, query: str = None) -> str:
    """두 과목 간의 관계 분석"""
    llm = get_llm_client()

    query_context = f"사용자 관심 분야: {query}" if query else "특별한 관심 분야 없음"

    prompt = f"""
두 대학 과목의 관계를 분석해주세요.

{query_context}

### 과목 1
- 이름: {course1.get('class_name', '')}
- 학과: {course1.get('department', '')}
- 학년: {course1.get('student_grade', '')}학년
- 학기: {course1.get('semester', '')}학기
- 설명: {course1.get('description', '')}

### 과목 2
- 이름: {course2.get('class_name', '')}
- 학과: {course2.get('department', '')}
- 학년: {course2.get('student_grade', '')}학년
- 학기: {course2.get('semester', '')}학기
- 설명: {course2.get('description', '')}

다음 중 하나로만 답변하세요:
- "Prerequisite": 과목1이 과목2의 선수과목
- "Complementary": 서로 보완적 관계
- "Unrelated": 관련 없음

답변: """

    try:
        messages = [
            SystemMessage(content="당신은 교육과정 전문가입니다."),
            HumanMessage(content=prompt)
        ]

        response = llm.invoke(messages)
        relation = response.content.strip()

        logger.info(f"과목 관계 분석: {relation}")
        return relation

    except Exception as e:
        logger.error(f"과목 관계 분석 실패: {e}")
        return "Unrelated"


def analyze_course_relationships(query: str, department_graphs: Dict) -> Dict:
    """학과 간 과목 관계 분석"""
    merged_graph = nx.DiGraph()

    # 모든 학과 그래프 병합
    for dept_name, graph in department_graphs.items():
        for node, data in graph.nodes(data=True):
            merged_graph.add_node(node, **data)
        for source, target in graph.edges():
            merged_graph.add_edge(source, target)

    all_courses = list(merged_graph.nodes(data=True))
    new_edges = []

    # 서로 다른 학과의 과목들만 비교
    for i in range(len(all_courses)):
        for j in range(i + 1, len(all_courses)):
            course1_id, course1_data = all_courses[i]
            course2_id, course2_data = all_courses[j]

            # 같은 학과면 건너뛰기
            if course1_data.get('department') == course2_data.get('department'):
                continue

            # 학년/학기 순서 정렬 (낮은 학년/학기가 선수과목)
            if (course1_data.get("student_grade", 0) > course2_data.get("student_grade", 0) or
                (course1_data.get("student_grade", 0) == course2_data.get("student_grade", 0) and
                 course1_data.get("semester", 0) > course2_data.get("semester", 0))):
                course1_id, course2_id = course2_id, course1_id
                course1_data, course2_data = course2_data, course1_data

            # 연속된 학기인지 확인
            if not is_consecutive_semester(course1_data, course2_data):
                continue

            # 관계 분석
            relation = get_course_relationship(course1_data, course2_data, query)

            if relation in ["Prerequisite", "Complementary"]:
                new_edges.append({"from": course1_id, "to": course2_id})
                merged_graph.add_edge(course1_id, course2_id)

    logger.info(f"새로운 학과 간 관계 {len(new_edges)}개 추가됨")
    return {"merged_graph": merged_graph}


def is_consecutive_semester(course1: Dict, course2: Dict) -> bool:
    """연속된 학기인지 확인"""
    grade1, sem1 = course1.get("student_grade", 0), course1.get("semester", 0)
    grade2, sem2 = course2.get("student_grade", 0), course2.get("semester", 0)

    # 같은 학년의 다음 학기 또는 다음 학년의 첫 학기
    return ((grade1 == grade2 and sem2 == sem1 + 1) or
            (grade2 == grade1 + 1 and sem2 == 1 and sem1 == 2))


def select_courses_by_llm(query: str, departments: List[str], courses: List[Dict]) -> str:
    """LLM을 사용한 과목 선택"""
    llm = get_llm_client("gpt-4o-mini")

    dept_str = ", ".join(departments)
    course_info = json.dumps(courses, ensure_ascii=False, indent=2)

    system_prompt = """당신은 학술 과목 추천 전문가입니다.
사용자의 쿼리에 가장 적합한 과목들을 JSON 형식으로 선택해주세요."""

    user_prompt = f"""
쿼리: "{query}"
관련 학과: {dept_str}

다음 과목들 중에서 쿼리와 가장 관련성이 높은 5-12개 과목을 선택하고
관련성 순으로 정렬해주세요.

과목 정보:
{course_info}

JSON 형식으로 응답해주세요:
{{"result": [선택된 과목들의 배열]}}
"""

    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        response = llm.invoke(messages)
        response_text = response.content

        # 결과 저장
        timestamp = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        save_path = SELECT_DIR / f"{timestamp}.json"
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump({"query": query, "response": response_text}, f, ensure_ascii=False, indent=2)

        return response_text

    except Exception as e:
        logger.error(f"과목 선택 실패: {e}")
        return json.dumps({"result": courses[:10]}, ensure_ascii=False)


# 하위 호환성을 위한 별칭
selected_edge_by_llm = analyze_course_relationships
selected_by_llm = select_courses_by_llm
get_llm_prediction = get_course_relationship
construct_prompt = lambda self, query, dept_names, items: f"Query: {query}, Departments: {dept_names}"