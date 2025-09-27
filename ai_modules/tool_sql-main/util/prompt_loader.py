"""
프롬프트 로더 유틸리티
"""
import os
from pathlib import Path

class PromptLoader:
    """프롬프트 파일 로더"""
    
    def __init__(self):
        self.prompts_dir = Path(__file__).parent.parent / "prompts"
    
    def load_sql_system_prompt(self) -> str:
        """SQL 시스템 프롬프트 로드"""
        prompt_file = self.prompts_dir / "sql_system_prompt.txt"
        
        if not prompt_file.exists():
            raise FileNotFoundError(f"프롬프트 파일을 찾을 수 없습니다: {prompt_file}")
        
        with open(prompt_file, 'r', encoding='utf-8') as f:
            return f.read().strip()
    
    def load_sanitize_prompt(self) -> str:
        """세니타이징 프롬프트 로드"""
        prompt_file = self.prompts_dir / "sanitize_prompt.txt"
        
        if not prompt_file.exists():
            raise FileNotFoundError(f"프롬프트 파일을 찾을 수 없습니다: {prompt_file}")
        
        with open(prompt_file, 'r', encoding='utf-8') as f:
            return f.read().strip()
    
    def list_prompts(self) -> list:
        """사용 가능한 프롬프트 파일 목록"""
        if not self.prompts_dir.exists():
            return []
        
        return [f.name for f in self.prompts_dir.glob("*.txt")]
