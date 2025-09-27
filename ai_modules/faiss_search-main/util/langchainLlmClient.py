"""
LangChain LLM 클라이언트
"""
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from dotenv import load_dotenv
import os

load_dotenv()  # .env 파일 자동 로드

class LangchainLlmClient:

    def __init__(self):
        self.model = "gpt-4o-mini"
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.temperature = 0.1
        self.llm = ChatOpenAI(
            model=self.model,
            temperature=self.temperature,
            api_key=self.api_key
        )
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-ada-002",
            api_key=self.api_key
        )

    def get_llm(self):
        """LLM 인스턴스 반환"""
        return self.llm

    def get_embeddings(self):
        """임베딩 모델 반환"""
        return self.embeddings