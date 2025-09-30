import logging
from typing import Dict, Any
from utils.prompt_loader import load_prompt

logger = logging.getLogger(__name__)

class ResultSynthesizer:
    def __init__(self, llm_handler=None):
        self.llm_handler = llm_handler

    def set_llm_handler(self, llm_handler):
        """llm_handler 설정"""
        self.llm_handler = llm_handler
        logger.info("✅ ResultSynthesizer에 llm_handler 설정 완료")

    async def synthesize_with_llm(self, user_message: str, found_results: str,
                                 processing_type: str) -> str:
        """LLM을 사용해서 에이전트가 찾은 결과를 자연스러운 답변으로 종합 (스트리밍)"""
        try:
            # 프롬프트 로드
            synthesis_template = load_prompt("synthesis_prompt")
            synthesis_prompt = synthesis_template.format(
                user_message=user_message,
                found_results=found_results,
                processing_type=processing_type,
            )

            logger.info(f"🚀 합성 시작 (스트리밍): prompt_length={len(synthesis_prompt)}")

            # 🔥 스트리밍 LLM 호출 - LangChain이 자동으로 이벤트 발생
            if hasattr(self.llm_handler, 'chat_stream'):
                full_response = ""
                async for chunk in self.llm_handler.chat_stream(synthesis_prompt):
                    full_response += chunk

                if full_response.strip():
                    logger.info(f"✅ 합성 성공: result_length={len(full_response)}")
                    return full_response.strip()
                else:
                    logger.warning("⚠️ 합성 결과 비어있음")
                    return found_results
            else:
                logger.warning("⚠️ chat_stream 미지원, 일반 호출 사용")
                synthesized = await self.llm_handler.chat(synthesis_prompt)
                return synthesized.strip() if synthesized.strip() else found_results

        except Exception as e:
            logger.error(f"❌ 합성 오류: {e}")
            return found_results

    async def synthesize_with_llm_stream(self, user_message: str, found_results: str,
                                    processing_type: str):
        """스트리밍 모드로 LLM 합성"""
        try:
            # 프롬프트 로드
            synthesis_template = load_prompt("synthesis_prompt")
            synthesis_prompt = synthesis_template.format(
                user_message=user_message,
                found_results=found_results,
                processing_type=processing_type,
            )
            
            logger.info(f"🚀 스트리밍 합성 시작: prompt_length={len(synthesis_prompt)}")
            
            # 🔥 스트리밍으로 LLM 호출
            if hasattr(self.llm_handler, 'chat_stream'):
                async for chunk in self.llm_handler.chat_stream(synthesis_prompt):
                    yield chunk
            else:
                # fallback: 일반 호출
                result = await self.llm_handler.chat(synthesis_prompt)
                yield result
                
        except Exception as e:
            logger.error(f"❌ 스트리밍 합성 오류: {e}")
            yield found_results

