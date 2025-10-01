"""
노드 유틸리티 함수들
"""

import logging
import re
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


def extract_last_question(user_message: str) -> str:
    """여러 질문 중 마지막 질문만 추출"""

    # Follow-up 질문 생성 요청 필터링
    if "### Task:" in user_message and "follow-up questions" in user_message:
        logger.info("🚫 Follow-up 질문 생성 요청 무시")
        return ""

    # 히스토리에서 마지막 USER 질문 추출
    if '<chat_history>' in user_message:
        # USER: 패턴으로 마지막 질문 찾기
        user_pattern = r'USER:\s*([^\n]+)'
        matches = re.findall(user_pattern, user_message)
        if matches:
            last_user_question = matches[-1].strip()
            logger.info(f"🔍 히스토리에서 마지막 USER 질문 추출: '{last_user_question}'")
            return last_user_question

    # 히스토리 태그 제거 (기존 로직 유지)
    if '</chat_history>' in user_message:
        parts = user_message.split('</chat_history>')
        if len(parts) > 1:
            clean_message = parts[-1].strip()
            # 빈 문자열이면 원본 사용
            if not clean_message:
                logger.warning("⚠️ 히스토리 태그 제거 후 빈 문자열 → 원본 사용")
                return user_message
            logger.info(f"🔀 히스토리 태그 제거: '{clean_message}'")
            user_message = clean_message

    # 물음표로 구분된 복합 질문 처리 (새로운 로직)
    if '?' in user_message:
        # 물음표로 분리된 질문들 찾기
        questions = [q.strip() + '?' for q in user_message.split('?') if q.strip()]
        if len(questions) > 1:
            # 마지막 질문이 시스템 태그가 아닌지만 확인 (길이 제한 없음)
            last_q = questions[-1].replace('?', '').strip()
            if not last_q.startswith('</') and not last_q.startswith('['):
                logger.info(f"🔀 물음표로 구분된 복합 질문에서 마지막 질문만 사용: '{questions[-1]}'")
                return questions[-1]

    # 여러 줄인 경우 마지막 라인만 사용
    lines = [line.strip() for line in user_message.split('\n') if line.strip()]
    if len(lines) > 1:
        last_question = lines[-1]
        # 시스템 태그가 아닌 실제 질문인지만 확인 (길이 제한 없음)
        if (not last_question.startswith('</') and
            not last_question.startswith('[') and
            not last_question.startswith('USER:') and
            not last_question.startswith('AI:')):
            logger.info(f"🔀 여러 줄 질문에서 마지막 질문만 사용: '{last_question}'")
            return last_question

    return user_message


def extract_history_context(user_message: str) -> str:
    """채팅 히스토리에서 컨텍스트 추출"""
    if '<chat_history>' in user_message and '</chat_history>' in user_message:
        start = user_message.find('<chat_history>')
        end = user_message.find('</chat_history>')
        if start != -1 and end != -1:
            history_content = user_message[start + len('<chat_history>'):end].strip()
            logger.info(f"🔍 히스토리 컨텍스트 추출: {len(history_content)}자")
            return history_content
    return ""