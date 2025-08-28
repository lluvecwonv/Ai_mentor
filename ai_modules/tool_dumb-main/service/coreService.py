# ai_modules/tool_dumb-main/service/coreService.py

from util.llmClient import LlmClient
from typing import List

class CoreService():

    def __init__(self):
        self.llmClient = LlmClient()
        
    def execute(self, messages: List):
        """
        [수정됨]
        컨트롤러로부터 받은 messages 리스트에 시스템 프롬프트를 추가하여
        LlmClient에 전달합니다.
        """
        system_prompt = """
            You are a kind and helpful AI assistant. 
            Analyze the entire conversation history provided and answer the user's last question based on the context.
            Your responses must always be in **Korean**.
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