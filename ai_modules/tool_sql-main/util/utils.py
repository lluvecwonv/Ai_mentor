import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def remove_markdown(result: str) -> str:
    """마크다운 제거"""
    logger.debug("🔗 [체인 2/3] 마크다운 제거 시작")

    if not result:
        return result

    cleaned = result.replace("```sql", "").replace("```", "").strip()

    logger.debug("🔗 [체인 2/3] 마크다운 제거 완료")
    return cleaned

def format_result(result: list) -> str:
    """DB 결과를 보기 좋게 포맷팅"""
    if not result:
        return "결과가 없습니다."
    
    if len(result) == 1 and len(result[0]) == 1:
        # 단일 값인 경우
        value = list(result[0].values())[0]
        return f"결과: {value}"
    
    # 여러 행인 경우
    formatted = f"총 {len(result)}개 결과:\n"
    for i, row in enumerate(result, 1):
        formatted += f"{i}. {row}\n"
    
    return formatted


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