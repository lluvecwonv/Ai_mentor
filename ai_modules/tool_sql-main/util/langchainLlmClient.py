

from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os

load_dotenv()  # .env 파일 자동 로드

api_key = os.getenv("OPENAI_API_KEY")
db_host = os.getenv("DB_HOST")

class LangchainLlmClient():

    def __init__(self):
        self.model = "gpt-4.1-mini"
        self.api_key = api_key
        self.temperature = 0.05
        self.seed = 42
        self.llm = ChatOpenAI(model = self.model, temperature = self.temperature, seed = self.seed, api_key = self.api_key)

    def get_llm(self):
        """LLM 인스턴스 반환"""
        return self.llm
