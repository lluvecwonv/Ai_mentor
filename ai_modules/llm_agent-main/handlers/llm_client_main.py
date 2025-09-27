from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
import os
import asyncio

class LlmClient:
    def __init__(self, model: str = "gpt-4o"):
        self.llm = ChatOpenAI(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            model=model,
            temperature=0,
            max_tokens=4000
        )
    
    async def chat(self, message: str, context: str = None, json_mode: bool = False) -> str:
        """채팅 응답 생성"""
        # 메시지 구성
        messages = []
        if context:
            messages.append(SystemMessage(content=context))
        messages.append(HumanMessage(content=message))
        
        # JSON 모드 설정
        llm = self.llm.bind(response_format={"type": "json_object"}) if json_mode else self.llm
    
        response = await asyncio.get_event_loop().run_in_executor(
            None, llm.invoke, messages
        )
        return response.content

    def chat_completion(self, messages, model: str = None, **kwargs) -> str:
        """OpenAI 스타일 chat completion - chat 메서드를 동기로 래핑"""
        user_content = ""
        system_content = None

        for msg in messages:
            if msg.get("role") == "system":
                system_content = msg.get("content", "")
            elif msg.get("role") == "user":
                user_content = msg.get("content", "")

        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.chat(user_content, system_content))
            loop.close()
            return result
        except Exception as e:
            return f"Error in chat_completion: {str(e)}"