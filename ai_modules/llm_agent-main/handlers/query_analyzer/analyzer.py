import logging
from typing import Dict, Any
from utils.prompt_loader import load_prompt
from utils.json_utils import extract_json_block, to_router_decision
    # LLM 호출
import asyncio
logger = logging.getLogger(__name__)



async def analyze_routing_async(llm_client, query: str, contextual_prompt: str = None, history_context: str = None) -> Dict[str, Any]:
    """라우팅 분석 - 재구성된 질문만 사용 (히스토리 제거)"""

    # 프롬프트 구성 - 재구성된 질문만 사용
    router_prompt = load_prompt('router_prompt').replace('{query}', query)

    # 추가 컨텍스트만 적용 (히스토리 컨텍스트는 라우팅에서 제외)
    if contextual_prompt:
        router_prompt = f"{contextual_prompt}\n\n{router_prompt}"

    response = await llm_client.chat(router_prompt)
    logger.info(f"🔍 [DEBUG] 라우터 응답: {response}")

    data = extract_json_block(response)

    # JSON 파싱 실패 시 재시도
    if not data:
        logger.warning("🔄 JSON 파싱 실패, 재시도 중...")
        retry_prompt = router_prompt + "\n\n**CRITICAL: Your previous response was not valid JSON. Please respond ONLY with JSON starting with { and ending with }.**"
        response = await llm_client.chat(retry_prompt, json_mode=True)
        logger.info(f"🔍 [RETRY] 라우터 재시도 응답: {response}")
        data = extract_json_block(response) or {}

    logger.info(f"🔍 [DEBUG] 추출된 JSON: {data}")
    decision = to_router_decision(data)
    logger.info(f"🔍 [DEBUG] 최종 결정: {decision}")

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

    response = await llm_client.chat(expansion_prompt)

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
