
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()  # .env 파일 자동 로드

api_key = os.getenv("OPENAI_API_KEY")
db_host = os.getenv("DB_HOST")

class LlmClient():
    
    def __init__(self):
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"

    # ★★★ 수정한 call_llm 함수 ★★★
    def call_llm(self, messages: list, json_mode: bool = False) -> str:
        """
        메시지 리스트를 직접 받아 LLM을 호출합니다.
        json_mode가 True이면 JSON 응답을 강제합니다.
        """
        extra_args = {}
        if json_mode:
            # JSON 모드는 GPT-4o, GPT-3.5-Turbo 최신 모델에서 지원됩니다.
            extra_args["response_format"] = {"type": "json_object"}
            
        return self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **extra_args
        )
    
    def chat(self, user_prompt: str, stream: bool = False):
        system_prompt = """
You are a professional translator.
Translate only the Korean text into clear, idiomatic English.
Preserve all existing markdown syntax (including image links) unchanged.
Do not add explanations or alter formatting beyond the translation.
"""

        return self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            stream=stream
        )