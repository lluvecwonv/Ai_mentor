"""
결과 종합기 - 에이전트가 찾은 결과를 LLM이 자연스러운 답변으로 변환
"""

import logging
import asyncio
from typing import Dict, Any
from utils.prompt_loader import load_prompt
from utils.logging import SynthesisLogger

logger = logging.getLogger(__name__)

class ResultSynthesizer:
    """에이전트 결과를 LLM으로 종합하는 클래스"""

    def __init__(self, llm_handler):
        self.llm_handler = llm_handler

    async def synthesize_with_llm(self, user_message: str, found_results: str,
                                 processing_type: str, query_analysis: Dict[str, Any],
                                 conversation_history: str = "") -> str:
        """LLM을 사용해서 에이전트가 찾은 결과를 자연스러운 답변으로 종합 (히스토리 포함)"""
        try:
            # 프롬프트 파일에서 템플릿 로드
            synthesis_template = load_prompt("synthesis_prompt")

            # 히스토리 섹션 구성
            history_section = ""
            if conversation_history:
                history_section = f"### 이전 대화 맥락:\n{conversation_history}\n"
                logger.info(f"📚 Synthesis에 히스토리 컨텍스트 추가: {len(conversation_history)}자")

            # 프롬프트에 실제 값들 대입
            synthesis_prompt = synthesis_template.format(
                conversation_history=history_section,
                user_message=user_message,
                found_results=found_results,
                processing_type=processing_type
            )

            # LLM 호출
            SynthesisLogger.log_synthesis_start(len(synthesis_prompt))

            if self.llm_handler and hasattr(self.llm_handler, 'invoke_simple'):
                # LangChain 방식
                synthesized = await self.llm_handler.invoke_simple(synthesis_prompt)
            elif self.llm_handler and hasattr(self.llm_handler, 'chat_completion'):
                # 기본 chat completion 방식
                messages = [{"role": "user", "content": synthesis_prompt}]
                if asyncio.iscoroutinefunction(self.llm_handler.chat_completion):
                    synthesized = await self.llm_handler.chat_completion(messages)
                else:
                    synthesized = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: self.llm_handler.chat_completion(messages)
                    )
            else:
                SynthesisLogger.log_handler_unavailable()
                return found_results

            if isinstance(synthesized, str) and synthesized.strip():
                SynthesisLogger.log_synthesis_success(len(synthesized))
                return synthesized.strip()
            else:
                SynthesisLogger.log_synthesis_empty()
                return found_results

        except Exception as e:
            SynthesisLogger.log_synthesis_error(e)
            return found_results

    def should_synthesize(self, processing_type: str) -> bool:
        """해당 처리 타입에 대해 LLM 종합이 필요한지 판단"""
        # llm_only, cache_only, curriculum_focused는 종합하지 않음 (이미 완전한 답변 생성됨)
        should_synthesize = processing_type not in ['llm_only', 'cache_only', 'curriculum_focused']
        SynthesisLogger.log_should_synthesize_decision(processing_type, should_synthesize)
        return should_synthesize