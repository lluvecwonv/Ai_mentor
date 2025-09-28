import ast
import logging
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

def load_prompt(prompt_name: str) -> str:
    """
    로컬 프롬프트 로더

    Args:
        prompt_name: 프롬프트 파일명 (.txt 확장자 제외)

    Returns:
        str: 프롬프트 내용

    Raises:
        FileNotFoundError: 프롬프트 파일을 찾을 수 없는 경우
    """
    current_dir = Path(__file__).parent.parent
    prompt_path = current_dir / "prompts" / f"{prompt_name}.txt"

    if not prompt_path.exists():
        raise FileNotFoundError(f"프롬프트 파일을 찾을 수 없습니다: {prompt_path}")

    return prompt_path.read_text(encoding='utf-8').strip()

def generate_embedding(text: str, llm_client) -> Optional[np.ndarray]:
    """텍스트를 OpenAI 임베딩으로 변환"""
    try:
        response = llm_client.embeddings.create(
            model="text-embedding-ada-002",
            input=text,
            encoding_format="float"
        )
        return np.array(response.data[0].embedding, dtype=np.float32)
    except Exception as e:
        logger.error(f"임베딩 생성 실패: {e}")
        return None

def extract_sql_from_response(response_text: str) -> str:
    """LLM 응답에서 SQL 쿼리 추출 (SQL 형식)"""
    try:
        # ```sql ... ``` 블록에서 SQL 추출
        if "```sql" in response_text:
            start = response_text.find("```sql") + 6
            end = response_text.find("```", start)
            if end != -1:
                sql = response_text[start:end].strip()
                return sql if sql else None

        # SELECT로 시작하는 SQL 찾기
        if "SELECT" in response_text.upper():
            lines = response_text.split('\n')
            sql_lines = []
            in_sql = False

            for line in lines:
                if "SELECT" in line.upper():
                    in_sql = True
                if in_sql:
                    sql_lines.append(line)
                    if ";" in line:
                        break

            if sql_lines:
                return '\n'.join(sql_lines).strip()

        # 빈 응답이면 None 반환
        return None

    except Exception as e:
        logger.error(f"SQL 추출 실패: {e}")
        return None

def prepare_vectors(courses: List[Dict]) -> tuple:
    """벡터 데이터 준비"""
    vectors = []
    metadata = []

    for course in courses:
        try:
            vector_str = course.get('vector', '[]')
            if not vector_str or vector_str == '[]':
                continue

            vector = ast.literal_eval(vector_str)
            vector_array = np.array(vector, dtype=np.float32)

            # 정규화
            norm = np.linalg.norm(vector_array)
            if norm > 0:
                vector_array = vector_array / norm

            vectors.append(vector_array)
            metadata.append({
                'id': course['id'],
                'name': course['name'],
                'department': course.get('department_name', course.get('department_full_name', course.get('department', ''))),
                'professor': course.get('professor', '정보없음'),
                'credits': course.get('credits', 0),
                'schedule': course.get('schedule', '정보없음'),
                'location': course.get('location', '정보없음'),
                'delivery_mode': course.get('delivery_mode', '정보없음'),
                'gpt_description': course.get('gpt_description', ''),
            })
        except Exception as e:
            logger.warning(f"벡터 파싱 실패: {course.get('name', 'Unknown')} - {e}")
            continue

    return vectors, metadata