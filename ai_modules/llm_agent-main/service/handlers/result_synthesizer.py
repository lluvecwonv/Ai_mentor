import logging
from typing import Dict, Any
from utils.prompt_loader import load_prompt
from .llm_client_main import LlmClient

logger = logging.getLogger(__name__)

class ResultSynthesizer:
    def __init__(self, llm_handler=None):
        self.llm_handler = llm_handler

    async def synthesize_with_llm(self, user_message: str, found_results: str,
                                 processing_type: str) -> str:
        """LLM을 사용해서 에이전트가 찾은 결과를 자연스러운 답변으로 종합"""
        try:
            # 합성용 LLM 설정 (고품질 합성을 위해 큰 모델 사용)
            synthesis_llm = LlmClient.create_with_config(
                model="gpt-4.1-mini",  # 고품질 합성을 위한 큰 모델
                max_tokens=16000  # 긴 응답을 위한 많은 토큰
            )

            # 프롬프트 로드 및 히스토리 섹션 구성
            synthesis_template = load_prompt("synthesis_prompt")

            # 프롬프트 구성
            synthesis_prompt = synthesis_template.format(
                user_message=user_message,
                found_results=found_results,
                processing_type=processing_type,
            )

            logger.info(f"🚀 합성 시작: prompt_length={len(synthesis_prompt)}")

            # LLM 호출 (synthesis_llm 사용)
            synthesized = await synthesis_llm.chat(synthesis_prompt)

            # 결과 검증 및 반환
            if isinstance(synthesized, str) and synthesized.strip():
                logger.info(f"✅ 합성 성공: result_length={len(synthesized)}")
                return synthesized.strip()
            else:
                logger.warning("⚠️ 합성 결과 비어있음")
                return found_results

        except Exception as e:
            logger.error(f"❌ 합성 오류: {e}")
            return found_results