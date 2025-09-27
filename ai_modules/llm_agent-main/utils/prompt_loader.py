"""
Prompt loading utilities
"""
from pathlib import Path

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
    prompt_path = current_dir / "handlers" / "prompts" / f"{prompt_name}.txt"  # 경로 수정

    if not prompt_path.exists():
        raise FileNotFoundError(f"프롬프트 파일을 찾을 수 없습니다: {prompt_path}")

    return prompt_path.read_text(encoding='utf-8').strip()