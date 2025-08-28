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
        return self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.5
        )