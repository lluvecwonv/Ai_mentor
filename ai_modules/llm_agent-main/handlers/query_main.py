
from __future__ import annotations

import logging
from typing import Dict, Any

from .llm_client_langchain import LlmClientLangChain
from .query_analyzer.analyzer import (
    analyze_routing_async,
    expand_query_async,
    combine_expansion_with_query
)

logger = logging.getLogger(__name__)

class QueryAnalyzer:
    """Query 복잡도 분석 및 분류 - LangChain LLM + 규칙 결합 (v3)"""

    def __init__(self, conversation_memory=None):
        self.llm_client = LlmClientLangChain()
        self.conversation_memory = conversation_memory

    async def analyze_query_parallel(self, query: str, session_id: str = "default", contextual_prompt: str = None) -> Dict[str, Any]:

        # 메모리에서 히스토리 컨텍스트 가져오기
        history_context = ""
        if self.conversation_memory:
            history_context = self.conversation_memory.get_recent_context(session_id, max_turns=3)

        # 쿼리 확장
        expansion_result = await expand_query_async(self.llm_client, query, history_context)
        enhanced_query = combine_expansion_with_query(query, expansion_result)
        logger.info(f"🔗 확장 정보가 조합된 향상된 쿼리: '{enhanced_query}'")

        # 향상된 쿼리로 라우팅 분석 수행
        analysis_result = await analyze_routing_async(self.llm_client, enhanced_query, contextual_prompt, history_context)

        # 두 결과를 병합하되, 원본 쿼리도 보존
        combined_result = {
            **analysis_result,
            **expansion_result,
            "original_query": query,  # 원본 쿼리 보존
            "enhanced_query": enhanced_query if 'enhanced_query' in locals() else query,  # 향상된 쿼리
            "analysis_method": "parallel_v3_enhanced",
            "analyzer_type": "LangChain_Parallel",
            "has_context": bool(contextual_prompt),
        }
        return combined_result
