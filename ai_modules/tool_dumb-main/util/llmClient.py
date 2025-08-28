# ai_modules/tool_dumb-main/util/llmClient.py

from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

class LlmClient():
    
    def __init__(self):
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"

    def call_llm(self, messages: list):
        """
        [수정됨]
        메시지 리스트를 인자로 직접 받아서 OpenAI API를 호출합니다.
        """
        return self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.5
        )