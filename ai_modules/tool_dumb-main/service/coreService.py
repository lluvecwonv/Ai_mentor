# ai_modules/tool_dumb-main/service/coreService.py

from util.llmClient import LlmClient
from typing import List

class CoreService():

    def __init__(self):
        self.llmClient = LlmClient()
        
    def execute(self, messages: List):

        system_prompt = """
You are a helpful AI assistant with a memory. Your primary task is to answer the user's final question.

Follow these steps to find the answer:
1.  **Memory First:** Carefully read the entire conversation history provided below. If the answer to the user's question is present in the previous messages (e.g., the user's name, a previous topic), you MUST use that information for your answer.
2.  **General Knowledge Second:** If the answer cannot be found in the conversation history, use your general knowledge to provide a helpful response.

Your final answer must always be in **Korean**.
    """

        # Pydantic 모델 객체 리스트를 딕셔너리 리스트로 변환
        message_dicts = [msg.dict() for msg in messages]

        # 시스템 프롬프트를 맨 앞에 추가
        request_messages = [
            {"role": "system", "content": system_prompt},
            *message_dicts
        ]

        # 수정된 LlmClient의 call_llm 함수 호출
        return self.llmClient.call_llm(request_messages)