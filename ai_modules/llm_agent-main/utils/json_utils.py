import json
import re
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# JSON 패턴 정규식
_JSON_RE = re.compile(r"\{[\s\S]*\}")

def extract_json_block(text: str) -> Optional[Dict[str, Any]]:
    """
    텍스트에서 JSON 블록 추출 (연속된 JSON 처리 개선)
    여러 JSON이 있을 경우 가장 적합한 것을 선택

    Args:
        text: JSON이 포함된 텍스트

    Returns:
        Optional[Dict[str, Any]]: 파싱된 JSON 객체 또는 None
    """
    logger.debug(f"JSON 블록 추출 시도: {len(text or '')}자 텍스트")

    if not text:
        return None

    # 모든 JSON 객체 추출
    json_objects = []
    text = text.strip()
    
    # bracket counting으로 모든 완전한 JSON 추출
    brace_count = 0
    in_string = False
    escape_next = False
    start_idx = -1

    for i, char in enumerate(text):
        if escape_next:
            escape_next = False
            continue

        if char == '\\' and in_string:
            escape_next = True
            continue

        if char == '"' and not escape_next:
            in_string = not in_string
            continue

        if not in_string:
            if char == '{':
                if brace_count == 0:
                    start_idx = i  # JSON 시작점
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_idx != -1:
                    # 완전한 JSON 객체 추출
                    json_text = text[start_idx:i+1]
                    try:
                        parsed = json.loads(json_text)
                        json_objects.append(parsed)
                        logger.debug(f"🔧 JSON 객체 추출: {len(json_text)}자, {len(parsed)}개 필드")
                    except json.JSONDecodeError as e:
                        logger.warning(f"JSON 파싱 실패: {e}")
                    start_idx = -1

    # JSON 객체가 없으면 기존 방식으로 fallback
    if not json_objects:
        logger.warning("완전한 JSON 객체를 찾을 수 없음, 정규식 방식으로 fallback")
        m = _JSON_RE.search(text)
        if not m:
            logger.warning("JSON 패턴을 찾을 수 없음")
            return None

        try:
            result = json.loads(m.group())
            logger.debug(f"정규식 JSON 파싱 성공: {len(result)}개 필드")
            return result
        except Exception as e:
            logger.warning(f"JSON 파싱 실패, 수정 시도: {e}")
            # 후행 쉼표 등 수정 시도
            patched = re.sub(r",\s*([}\]])", r"\\1", m.group())
            try:
                result = json.loads(patched)
                logger.debug(f"수정된 JSON 파싱 성공: {len(result)}개 필드")
                return result
            except Exception as e2:
                logger.error(f"JSON 수정 후에도 파싱 실패: {e2}")
                return None

    # 여러 JSON 중 가장 적합한 것 선택
    logger.info(f"🔍 {len(json_objects)}개 JSON 객체 발견, 최적 선택 중...")
    
    # 우선순위: heavy > medium > light (복잡도가 높을수록 우선)
    complexity_priority = {'heavy': 3, 'medium': 2, 'light': 1}
    
    best_json = None
    best_score = -1
    
    for i, obj in enumerate(json_objects):
        score = 0
        complexity = obj.get('complexity', 'medium')
        score += complexity_priority.get(complexity, 1)
        
        # plan이 있으면 추가 점수
        if obj.get('plan') and len(obj.get('plan', [])) > 0:
            score += 2
            
        # owner_hint가 있으면 추가 점수
        if obj.get('owner_hint'):
            score += 1
            
        logger.debug(f"🔍 JSON #{i+1}: complexity={complexity}, score={score}")
        
        if score > best_score:
            best_score = score
            best_json = obj

    if best_json:
        logger.info(f"✅ 최적 JSON 선택: complexity={best_json.get('complexity')}, score={best_score}")
        return best_json
    else:
        logger.warning("적합한 JSON을 찾을 수 없음")
        return json_objects[0] if json_objects else None


def to_router_decision(data: Dict[str, Any]) -> Dict[str, Any]:
    """라우팅 결정 - plan 정보 보존"""

    logger.info(f"🔍 [to_router_decision] 입력 데이터: {data}")

    complexity = data.get('complexity', 'medium')

    # 간단한 힌트 매핑
    hint_map = {
        'sql': 'SQL_QUERY',
        'search': 'FAISS_SEARCH',
        'faiss': 'FAISS_SEARCH',
        'curriculum': 'CURRICULUM_PLAN'
    }

    # plan 정보 우선 추출
    plans = data.get('plan', data.get('pipeline', []))
    logger.info(f"🔍 [to_router_decision] 추출된 plans: {plans}")

    owner_hint = data.get('owner_hint', 'LLM_FALLBACK')
    if not owner_hint or owner_hint == 'LLM_FALLBACK':
        # 첫 번째 에이전트에서 추론
        if plans:
            agent = plans[0].get('agent', '').lower()
            for key, hint in hint_map.items():
                if key in agent:
                    owner_hint = hint
                    break

    result = {
        'complexity': complexity,
        'is_complex': complexity in ('medium', 'heavy'),
        'category': data.get('category', complexity),
        'owner_hint': owner_hint,
        'plan': plans,  # plan 정보 보존
        'reasoning': data.get('reasoning', '')
    }

    logger.info(f"🔍 [to_router_decision] 결과: {result}")
    return result


def robust_json_parse(response: str) -> Optional[Dict[str, Any]]:
    """간단한 JSON 파싱"""

    # 1단계: 기본 파싱
    try:
        return extract_json_block(response)
    except:
        pass

    # 2단계: 키 따옴표 수정
    try:
        json_match = re.search(r'\{[^{}]*\}', response)
        if json_match:
            json_text = json_match.group()
            # 키에 따옴표 추가
            fixed = re.sub(r'([a-zA-Z_]\w*)\s*:', r'"\1":', json_text)
            return json.loads(fixed)
    except:
        pass

    return None  # 실패시 None 반환


def _to_openai_content(content: Any) -> str:
    """OpenAI 호환 content 형태로 정규화

    Args:
        content: 변환할 컨텐츠 (str, dict, list, None 등)

    Returns:
        str: 정규화된 문자열
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, (list, dict)):
        if isinstance(content, dict) and "text" in content:
            return content["text"]
        return json.dumps(content, ensure_ascii=False)
    return str(content)
