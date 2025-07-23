
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()  # .env 파일 자동 로드

api_key = os.getenv("OPENAI_API_KEY")
db_host = os.getenv("DB_HOST")

class LlmClient():
    
    def __init__(self):
        
        self.client = OpenAI(
            api_key=api_key,
        )
        self.model = "gpt-4o-mini"

    def call_llm(self, system_prompt: str, user_prompt: str, assistant_prompt: str) -> str:
        
        return self.client.chat.completions.create(
            model = self.model,
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": assistant_prompt},
            ]
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