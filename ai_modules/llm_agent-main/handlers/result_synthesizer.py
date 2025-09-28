import logging
from typing import Dict, Any
from utils.prompt_loader import load_prompt

logger = logging.getLogger(__name__)

class ResultSynthesizer:
    def __init__(self, llm_handler):
        self.llm_handler = llm_handler

    async def synthesize_with_llm(self, user_message: str, found_results: str,
                                 processing_type: str, query_analysis: Dict[str, Any],
                                 conversation_history: str = "") -> str:
        """LLM을 사용해서 에이전트가 찾은 결과를 자연스러운 답변으로 종합"""
        try:
            # 프롬프트 로드 및 히스토리 섹션 구성
            synthesis_template = load_prompt("synthesis_prompt")
            history_section = f"### 이전 대화 맥락:\n{conversation_history}\n" if conversation_history else ""
            
            if conversation_history:
                logger.info(f"📚 Synthesis에 히스토리 컨텍스트 추가: {len(conversation_history)}자")

            # 프롬프트 구성
            synthesis_prompt = synthesis_template.format(
                conversation_history=history_section,
                user_message=user_message,
                found_results=found_results,
                processing_type=processing_type
            )

            logger.info(f"🚀 합성 시작: prompt_length={len(synthesis_prompt)}")

            # LLM 호출 방식 결정
            if hasattr(self.llm_handler, 'chat'):
                synthesized = await self.llm_handler.chat(synthesis_prompt)
            else:
                logger.warning("⚠️ 지원되지 않는 핸들러 타입")
                return found_results

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