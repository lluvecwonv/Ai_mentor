from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
import os
import asyncio
import json
import re
import logging

logger = logging.getLogger(__name__)

class LlmClient:
    def __init__(self, model: str = "gpt-4o-mini", max_tokens: int = 4000):
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

    async def validate_light_query(self, query: str) -> dict:
        """
        Light 라우팅 검증 - 질문이 정말 일반 대화인지 확인

        Returns:
            {
                "is_general_chat": bool,
                "reason": str,
                "success": bool
            }
        """
        try:
            # 프롬프트 로드
            prompt_path = os.path.join(
                os.path.dirname(__file__),
                "prompts",
                "light_validator_prompt.txt"
            )

            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_template = f.read()

            # 쿼리 삽입
            prompt = prompt_template.format(query=query)

            # LLM 호출 (JSON 모드)
            response = await self.chat(prompt, json_mode=True)

            logger.info(f"🔍 [Light Validator] LLM 응답: {response}")

            # JSON 파싱
            result = json.loads(response)

            return {
                "is_general_chat": result.get("is_general_chat", False),
                "reason": result.get("reason", ""),
                "success": True
            }

        except json.JSONDecodeError as e:
            logger.error(f"❌ Light Validator JSON 파싱 실패: {e}")
            # 파싱 실패 시 정규식으로 재시도
            try:
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    return {
                        "is_general_chat": result.get("is_general_chat", False),
                        "reason": result.get("reason", ""),
                        "success": True
                    }
            except:
                pass

            # 완전 실패 시 안전하게 통과
            return {
                "is_general_chat": True,
                "reason": "JSON 파싱 실패로 기본 통과",
                "success": False
            }

        except Exception as e:
            logger.error(f"❌ Light Validator 실패: {e}")
            # 에러 시 안전하게 통과
            return {
                "is_general_chat": True,
                "reason": f"검증 실패: {str(e)}",
                "success": False
            }