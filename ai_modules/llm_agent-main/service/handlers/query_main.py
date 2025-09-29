from __future__ import annotations

import logging
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
        self.llm_client = LlmClient(max_tokens=256)
        self.conversation_memory = conversation_memory

    async def analyze_query_parallel(self, query: str, session_id: str = "default", contextual_prompt: str = None, is_reconstructed: bool = False, history_context: str = None) -> Dict[str, Any]:
        """쿼리를 병렬로 분석하여 라우팅 및 확장 정보 생성"""

        # 1. 쿼리 확장 (히스토리 컨텍스트 포함)
        expansion_result = await expand_query_async(self.llm_client, query, history_context)
        logger.info(f"🔗 쿼리 확장 완료: '{query}' (히스토리 컨텍스트: {bool(history_context)})")

        # 2. 확장된 정보와 원본 쿼리 결합
        enhanced_query = combine_expansion_with_query(query, expansion_result)
        logger.info(f"🔗 확장 정보가 조합된 향상된 쿼리: '{enhanced_query}'")

        # 3. 라우팅 분석 수행 (히스토리 컨텍스트 포함)
        analysis_result = await analyze_routing_async(self.llm_client, enhanced_query, contextual_prompt, history_context)
        logger.info(f"🔍 라우팅 분석 완료: complexity={analysis_result.get('complexity')}")

        # 4. 결과 병합 및 반환
        combined_result = {
            **analysis_result,
            **expansion_result,
            "original_query": query,
            "enhanced_query": enhanced_query,
            "analysis_method": "parallel_v3_enhanced",
            "analyzer_type": "LangChain_Parallel",
            "has_context": bool(contextual_prompt),
            "is_reconstructed": is_reconstructed
        }

        logger.info(f"✅ 쿼리 분석 완료: complexity={combined_result.get('complexity')}")

        return combined_result