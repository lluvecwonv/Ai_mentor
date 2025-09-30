from __future__ import annotations

import logging
import asyncio
from typing import Dict, Any

from .llm_client_main import LlmClient
from .query_analyzer.analyzer import (
    analyze_routing_async,
    expand_query_async,
    combine_expansion_with_query
)

logger = logging.getLogger(__name__)

class QueryAnalyzer:
    """Query 복잡도 분석 및 분류 - LangChain LLM + 규칙 결합 (v3)"""

    def __init__(self, conversation_memory=None):
        self.llm_client = LlmClient(max_tokens=2000)
        self.conversation_memory = conversation_memory

    async def analyze_query_parallel(self, query: str, session_id: str = "default", contextual_prompt: str = None, is_reconstructed: bool = False, history_context: str = None) -> Dict[str, Any]:
        """쿼리 분석 - 라우팅과 확장을 병렬 실행, Light는 확장 결과 무시"""

        # 1. 라우팅 분석과 쿼리 확장을 병렬 실행 (동시에 2개 LLM 호출)
        logger.info(f"🚀 병렬 처리 시작: 라우팅 분석 + 쿼리 확장")

        expansion_task = expand_query_async(self.llm_client, query, history_context)
        routing_task = analyze_routing_async(self.llm_client, query, contextual_prompt, history_context)

        # asyncio.gather로 동시 실행
        expansion_result, analysis_result = await asyncio.gather(
            expansion_task,
            routing_task
        )

        complexity = analysis_result.get('complexity', 'medium')
        logger.info(f"✅ 병렬 처리 완료: complexity={complexity}")


        # 경우 확장 결과 사용
        logger.info(f"🔍 복잡한 질문, 쿼리 확장 결과 사용")
        enhanced_query = combine_expansion_with_query(query, expansion_result)
        logger.info(f"🔗 확장 정보 조합 완료: '{enhanced_query}'")

        # 4. 결과 병합 및 반환
        combined_result = {
            **analysis_result,
            **expansion_result,
            "original_query": query,
            "enhanced_query": enhanced_query,
            "analysis_method": "parallel_v4_true_parallel",
            "analyzer_type": "LangChain_TrueParallel",
            "has_context": bool(contextual_prompt),
            "is_reconstructed": is_reconstructed
        }

        logger.info(f"✅ 쿼리 분석 완료 (병렬+확장): complexity={complexity}")
        return combined_result