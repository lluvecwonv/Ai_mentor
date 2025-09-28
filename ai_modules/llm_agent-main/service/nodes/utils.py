"""
노드 유틸리티 함수들
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def format_vector_search_result(result: Dict[str, Any]) -> str:
    """Vector Search 결과를 상세 정보로 포맷팅"""
    if not result or result.get('agent_type') != 'vector_search':
        return result.get('display', str(result.get('result', '')))

    vector_results = result.get('result', [])
    if not vector_results:
        return result.get('display', '검색 결과가 없습니다.')

    detailed_info = []
    for item in vector_results:
        info = f"**{item.get('name', '')}**"
        if item.get('department'):
            info += f"\n- 학과: {item.get('department')}"
        if item.get('professor'):
            info += f"\n- 교수: {item.get('professor')}"
        if item.get('credits'):
            info += f"\n- 학점: {item.get('credits')}학점"
        if item.get('schedule'):
            info += f"\n- 시간표: {item.get('schedule')}"
        if item.get('location'):
            info += f"\n- 강의실: {item.get('location')}"
        if item.get('delivery_mode'):
            info += f"\n- 수업방식: {item.get('delivery_mode')}"
        if item.get('gpt_description'):
            info += f"\n- 설명: {item.get('gpt_description')[:200]}..."
        detailed_info.append(info)

    return "\n\n".join(detailed_info)


def process_agent_results(agent_results: List[Dict[str, Any]], agent_names: List[str]) -> tuple[List[str], List[Dict[str, Any]]]:
    """에이전트 결과들을 처리하고 포맷팅된 결과와 이전 결과 리스트를 반환"""
    results = []
    previous_results = []

    for agent_name, result in zip(agent_names, agent_results):
        if result and result.get("success", True):
            # Vector Search 결과 상세 정보 처리
            display_text = format_vector_search_result(result)
            results.append(f"[{agent_name}] {display_text}")
            previous_results.append(result)
            logger.info(f"✅ [HEAVY] {agent_name} 결과 추가됨: {display_text[:100]}...")
        else:
            logger.warning(f"❌ [HEAVY] {agent_name} 결과 제외됨: success={result.get('success') if result else 'None'}")

    return results, previous_results