"""
스트리밍 유틸리티
SSE 이벤트 포맷 및 스트리밍 로직 중앙집중화
"""

from typing import Dict, Any, List, AsyncGenerator, Optional
import logging

logger = logging.getLogger(__name__)

class StreamingUtils:
    """스트리밍 관련 유틸리티"""

    @staticmethod
    def create_content_chunk(content: str) -> Dict[str, str]:
        """컨텐츠 청크 생성"""
        return {"type": "content", "content": content}

    @staticmethod
    def create_error_chunk(error_msg: str) -> Dict[str, str]:
        """에러 청크 생성"""
        return {"type": "error", "content": error_msg}

    @staticmethod
    def create_status_chunk(status: str, message: str = "") -> Dict[str, str]:
        """상태 청크 생성"""
        return {"type": "status", "status": status, "content": message}

    @staticmethod
    async def stream_with_fallback(
        primary_stream_func,
        fallback_stream_func,
        error_context: str = "스트리밍"
    ) -> AsyncGenerator[Dict[str, str], None]:
        """
        주요 스트리밍 실패시 폴백 스트리밍을 사용하는 래퍼

        Args:
            primary_stream_func: 주요 스트리밍 함수 (async generator)
            fallback_stream_func: 폴백 스트리밍 함수 (async generator)
            error_context: 에러 로그용 컨텍스트
        """
        try:
            # 주요 스트리밍 시도
            primary_used = False
            async for chunk in primary_stream_func():
                if chunk.get("type") == "content":
                    primary_used = True
                    yield chunk
                elif chunk.get("type") == "error":
                    logger.warning(f"{error_context} 주요 스트리밍 오류: {chunk.get('content')}")
                    break

            if not primary_used:
                raise Exception(f"{error_context} 주요 스트리밍 데이터 없음")

        except Exception as e:
            logger.warning(f"{error_context} 주요 스트리밍 실패, 폴백 시도: {e}")

            # 폴백 스트리밍 시도
            try:
                async for chunk in fallback_stream_func():
                    yield chunk
            except Exception as fallback_error:
                logger.error(f"{error_context} 폴백 스트리밍도 실패: {fallback_error}")
                yield StreamingUtils.create_error_chunk(f"{error_context} 실패: {str(fallback_error)}")

    @staticmethod
    def build_langchain_messages(
        conversation_memory,
        session_id: str,
        user_message: str,
        system_context: str = "",
        max_turns: int = 10
    ) -> List[Any]:
        """LangChain 메시지 리스트 구성"""
        try:
            msgs = []

            if system_context:
                from langchain.schema import SystemMessage
                msgs.append(SystemMessage(content=system_context))

            # 기존 대화 히스토리 추가
            msgs.extend(conversation_memory.get_chat_messages(session_id, max_turns=max_turns))

            # 현재 사용자 메시지 추가
            from langchain.schema import HumanMessage
            msgs.append(HumanMessage(content=user_message))

            return msgs
        except Exception as e:
            logger.error(f"LangChain 메시지 구성 실패: {e}")
            return []

    @staticmethod
    async def aggregate_and_save(
        streaming_generator,
        conversation_memory,
        session_id: str,
        user_message: str,
        query_analysis: Dict[str, Any],
        prior_contexts: Dict[str, str]
    ) -> AsyncGenerator[Dict[str, str], None]:
        """
        스트리밍 중 텍스트 수집하고 종료 후 대화 저장
        """
        aggregated = []

        try:
            async for chunk in streaming_generator:
                if chunk.get("type") == "content":
                    content = chunk.get("content", "")
                    aggregated.append(content)
                    yield chunk
                else:
                    yield chunk

            # 스트리밍 종료 후 대화 저장
            final_text = "".join(aggregated)
            if final_text and conversation_memory:
                try:
                    await conversation_memory._save_conversation_safely(
                        session_id=session_id,
                        user_message=user_message,
                        assistant_response=final_text,
                        query_analysis=query_analysis,
                        sql_context=prior_contexts.get('sql', ''),
                        vector_context=prior_contexts.get('vector', '')
                    )
                except Exception as save_error:
                    logger.warning(f"스트리밍 후 대화 저장 실패: {save_error}")

        except Exception as e:
            logger.error(f"스트리밍 집계 및 저장 실패: {e}")
            yield StreamingUtils.create_error_chunk(f"스트리밍 처리 오류: {str(e)}")


# 과거 중복된 ChatModelHelper와 관련 편의 함수 제거됨
