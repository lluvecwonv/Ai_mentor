"""
Prompt loading utilities
"""
import os
from pathlib import Path

def load_prompt(prompt_name: str) -> str:
    """
    Load prompt from txt file

    Args:
        prompt_name: Name of prompt file (without .txt extension)

    Returns:
        str: Prompt content
    """
    current_dir = Path(__file__).parent.parent
    prompt_path = current_dir / "service" / "prompts" / f"{prompt_name}.txt"

    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    return prompt_path.read_text(encoding='utf-8').strip()