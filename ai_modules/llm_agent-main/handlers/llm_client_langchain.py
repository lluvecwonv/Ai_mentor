"""
LangChain 기반 LLM Client - 최적화된 버전
기존 LlmClient와 동일한 인터페이스를 제공하되, 내부적으로 LangChain 사용
중복 코드 제거 및 성능 최적화 완료
"""
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from dotenv import load_dotenv
import os
import json
import time
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")


def _to_openai_content(content: Any) -> str:
    """OpenAI 호환 content 형태로 정규화"""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, (list, dict)):
        if isinstance(content, dict) and "text" in content:
            return content["text"]
        return json.dumps(content, ensure_ascii=False)
    return str(content)


class LlmClientLangChain:
    """LangChain 기반 LLM Client - 최적화된 버전"""

    def __init__(self, model: str = "gpt-4o", temperature: float = 0):
        self.model = model
        self.llm = ChatOpenAI(
            openai_api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=4000  # 긴 커리큘럼 응답을 위해 증가
        )

        # 성능 측정
        self.call_count = 0
        self.total_time = 0.0

        logger.debug(f"LangChain LLM Client 초기화 완료 (모델: {model})")

    def _convert_messages(self, messages: List[Dict[str, Any]]) -> List:
        """OpenAI 메시지를 LangChain 메시지로 변환"""
        langchain_messages = []

        for msg in messages:
            role = msg.get("role", "user")
            content = _to_openai_content(msg.get("content", ""))

            if role == "system":
                langchain_messages.append(SystemMessage(content=content))
            elif role == "user":
                langchain_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                langchain_messages.append(AIMessage(content=content))
            else:
                langchain_messages.append(HumanMessage(content=content))

        return langchain_messages

    def _invoke_llm(self, messages: List[Dict[str, Any]], model: str = None,
                   json_mode: bool = False) -> str:
        """LLM 호출 공통 로직 - 중복 코드 제거"""
        start_time = time.time()
        self.call_count += 1

        try:
            # 메시지 변환
            langchain_messages = self._convert_messages(messages)

            # LLM 인스턴스 결정
            current_llm = self.llm
            if model and model != self.model:
                current_llm = ChatOpenAI(
                    openai_api_key=api_key,
                    model=model,
                    temperature=0,
                    max_tokens=4000  # 긴 응답을 위해 증가
                )

            # JSON 모드 처리
            if json_mode:
                current_llm = current_llm.bind(response_format={"type": "json_object"})

            # LLM 호출
            response = current_llm.invoke(langchain_messages)

            # 성능 측정
            processing_time = time.time() - start_time
            self.total_time += processing_time

            logger.debug(f"LLM 호출 완료: {processing_time:.3f}초 (모델: {model or self.model})")
            return response.content

        except Exception as e:
            processing_time = time.time() - start_time
            self.total_time += processing_time
            logger.error(f"LLM 호출 실패: {e}")
            raise e

    def call_llm(self, messages: List[Dict[str, Any]], json_mode: bool = False) -> str:
        """메시지 리스트를 받아 LLM을 호출 (JSON 모드 지원)"""
        return self._invoke_llm(messages, json_mode=json_mode)

    async def chat_completion_json(self, messages: List[Dict[str, Any]], model: str = None) -> str:
        """JSON 모드로 chat completion 수행 (async)"""
        return self._invoke_llm(messages, model, json_mode=True)

    def chat_completion(self, messages: List[Dict[str, Any]], model: str = None) -> str:
        """간단한 채팅 완성 (모델 변경 지원)"""
        return self._invoke_llm(messages, model=model)

    async def run_chain(self, chain_type: str, user_message: str, context: str = None, **kwargs) -> str:
        """체인 실행 - 기존 인터페이스 호환"""
        messages = []

        if chain_type == "basic":
            # 기본 체인: 사용자 메시지만
            messages = [{"role": "user", "content": user_message}]

        elif chain_type == "context":
            # 컨텍스트 포함 체인: 시스템 메시지 + 사용자 메시지
            if context:
                messages = [
                    {"role": "system", "content": f"다음 정보를 참고하여 답변하세요:\n\n{context}"},
                    {"role": "user", "content": user_message}
                ]
            else:
                messages = [{"role": "user", "content": user_message}]

        elif chain_type == "context_only":
            # 컨텍스트만 체인: 히스토리 없이 컨텍스트만 사용
            if context:
                messages = [
                    {"role": "system", "content": f"제공된 정보만을 바탕으로 정확히 답변하세요:\n\n{context}"},
                    {"role": "user", "content": user_message}
                ]
            else:
                messages = [{"role": "user", "content": user_message}]

        elif chain_type in ["analysis", "parallel"]:
            # 분석/병렬 체인: 기본 체인과 동일하게 처리
            messages = [{"role": "user", "content": user_message}]

        else:
            # 알 수 없는 체인 타입: 기본 처리
            logger.warning(f"알 수 없는 체인 타입: {chain_type}, 기본 처리 사용")
            messages = [{"role": "user", "content": user_message}]

        return self._invoke_llm(messages)


    def get_performance_stats(self) -> Dict[str, Any]:
        """성능 통계 반환"""
        avg_time = self.total_time / max(self.call_count, 1)
        return {
            "total_calls": self.call_count,
            "total_time": self.total_time,
            "avg_time_per_call": avg_time,
            "client_type": "LangChain_Optimized",
            "model": self.model
        }