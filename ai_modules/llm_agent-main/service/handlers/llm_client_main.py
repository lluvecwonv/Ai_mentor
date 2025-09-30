from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
import os
import asyncio

class LlmClient:
    def __init__(self, model: str = "gpt-4o", max_tokens: int = 4000):
        self.model = model
        self.max_tokens = max_tokens
        self.llm = ChatOpenAI(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            model=model,
            temperature=0,
            max_tokens=max_tokens
        )

    @classmethod
    def create_with_config(cls, model: str, max_tokens: int):
        """특정 설정으로 새로운 LlmClient 인스턴스 생성"""
        return cls(model=model, max_tokens=max_tokens)

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

    async def chat_stream(self, message: str, context: str = None):
        """스트리밍 채팅 응답 생성"""
        messages = []
        if context:
            messages.append(SystemMessage(content=context))
        messages.append(HumanMessage(content=message))
        
        # 🔥 LangChain astream 사용
        async for chunk in self.llm.astream(messages):
            if hasattr(chunk, 'content') and chunk.content:
                yield chunk.content

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