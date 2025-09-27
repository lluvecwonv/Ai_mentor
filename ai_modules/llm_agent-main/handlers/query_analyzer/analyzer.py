import logging
from typing import Dict, Any
from utils.prompt_loader import load_prompt
from utils.json_utils import extract_json_block, to_router_decision
    # LLM 호출
import asyncio
logger = logging.getLogger(__name__)



async def analyze_routing_async(llm_client, query: str, contextual_prompt: str = None, history_context: str = None) -> Dict[str, Any]:
    """라우팅 분석 - 간단 버전"""

    # 프롬프트 구성
    router_prompt = load_prompt('router_prompt').replace('{query}', query)

    # 히스토리 컨텍스트 추가
    if history_context:
        router_prompt = router_prompt.replace('{query}',
            f"\n\n### 이전 대화:\n{history_context}\n\n### 현재 질문:\n{query}")

    # 추가 컨텍스트
    if contextual_prompt:
        router_prompt = f"{contextual_prompt}\n\n{router_prompt}"

    response = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: llm_client.chat_completion(
            messages=[{"role": "user", "content": router_prompt}],
            model="gpt-4o-mini"
        )
    )

    data = extract_json_block(response) or {}
    decision = to_router_decision(data)

    logger.info(f"🎯 라우팅 결정: {decision.get('complexity')}")
    return decision


async def expand_query_async(llm_client, query: str, history_context: str = None) -> Dict[str, Any]:
    """쿼리 확장 - 간단 버전"""

    # 프롬프트 구성
    expansion_prompt = load_prompt('query_reasoning_prompt').replace('{query}', query)

    # 히스토리 컨텍스트 추가
    if history_context:
        expansion_prompt = expansion_prompt.replace('{query}',
            f"\n\n### 이전 대화:\n{history_context}\n\n### 현재 질문:\n{query}")

    response = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: llm_client.chat_completion(
            messages=[{"role": "user", "content": expansion_prompt}],
            model="gpt-4o-mini"
        )
    )

    # 결과 파싱
    expansion_data = extract_json_block(response) or {}

    return {
        "expansion_context": expansion_data.get("expansion_context", ""),
        "expansion_keywords": expansion_data.get("expansion_keywords", ""),
        "expansion_augmentation": expansion_data.get("expansion_augmentation", ""),
        "decision_question_type": expansion_data.get("decision_question_type", ""),
        "decision_data_source": expansion_data.get("decision_data_source", "")
    }


def combine_expansion_with_query(original_query: str, expansion_result: Dict[str, Any]) -> str:
        """확장된 컨텍스트와 키워드를 원본 쿼리와 조합하여 향상된 쿼리 생성"""
        expansion_context = expansion_result.get("expansion_context", "").strip()
        expansion_keywords = expansion_result.get("expansion_keywords", "").strip()

        # 조합할 요소들 수집
        enhancement_parts = []

        # 확장 컨텍스트가 있으면 추가
        if expansion_context:
            enhancement_parts.append(f"배경정보: {expansion_context}")

        # 확장 키워드가 있으면 추가
        if expansion_keywords:
            # 키워드를 개별적으로 분리
            keywords_list = [kw.strip() for kw in expansion_keywords.split(',') if kw.strip()]
            if keywords_list:
                enhancement_parts.append(f"관련키워드: {', '.join(keywords_list)}")

        # 향상된 쿼리 구성
        if enhancement_parts:
            enhanced_query = f"{original_query}\n\n[확장정보] {' | '.join(enhancement_parts)}"
            logger.info(f"🔗 [쿼리조합] 원본: '{original_query}'")
            return enhanced_query
        else:
            logger.info("🔗 [쿼리조합] 확장정보 없음, 원본 쿼리 사용")
            return original_query
