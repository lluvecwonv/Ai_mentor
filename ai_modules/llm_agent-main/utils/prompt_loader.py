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

    # 다중 경로 지원: service/handlers/prompts, handlers/prompts, service/memory/prompts
    possible_paths = [
        current_dir / "service" / "handlers" / "prompts" / f"{prompt_name}.txt",
        current_dir / "handlers" / "prompts" / f"{prompt_name}.txt",
        current_dir / "service" / "memory" / "prompts" / f"{prompt_name}.txt"
    ]

    prompt_path = None
    for path in possible_paths:
        if path.exists():
            prompt_path = path
            break

    if not prompt_path:
        raise FileNotFoundError(f"프롬프트 파일을 찾을 수 없습니다. 확인한 경로: {[str(p) for p in possible_paths]}")

    return prompt_path.read_text(encoding='utf-8').strip()