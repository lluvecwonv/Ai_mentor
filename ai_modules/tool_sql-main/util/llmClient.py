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

    def call_llm(self, system_prompt: str, user_prompt: str) -> str:
        
        return self.client.chat.completions.create(
            model = self.model,
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature = 0
        )