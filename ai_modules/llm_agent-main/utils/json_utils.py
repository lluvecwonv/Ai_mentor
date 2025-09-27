"""
JSON utility functions
"""
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
    """
    RouterDecision 형태의 dict로 정규화

    입력 JSON에서 최소 필드만 사용하여 라우팅에 필요한 정보만 추립니다.

    Returns keys:
      - complexity, is_complex, category, owner_hint, plan(list of {step, agent, goal}), reasoning
    """
    # 1) 복잡도 판단
    complexity = data.get('complexity', 'medium')
    is_complex = complexity in ('medium', 'heavy')

    # 2) 파이프라인 플랜 정규화 (최대 4단계) - pipeline과 plan 필드 모두 지원
    pipeline = data.get('plan') or data.get('pipeline') or []
    plan: List[Dict[str, Any]] = []
    for i, p in enumerate(pipeline[:4], start=1):
        try:
            plan.append({
                'step': int(i),
                'agent': str(p.get('agent', 'LLM-Fallback-Agent')),
                'goal': str(p.get('why', p.get('goal', '')))
            })
        except Exception as e:
            logger.warning(f"🔶 플랜 단계 파싱 실패 (step {i}): {e}")
            continue

    # 3) 담당 에이전트 힌트 (ActionType 또는 AgentName 둘 다 허용)
    #    - 우선 data.owner_hint 사용
    #    - 없으면 pipeline[0].agent에서 유추하여 표준 토큰으로 정규화
    #    - 그래도 없으면 안전 폴백: LLM_FALLBACK
    def _agent_name_to_hint(agent_name: str) -> str:
        name = (agent_name or '').strip().lower()
        if 'sql' in name:
            return 'SQL_QUERY'
        if 'faiss' in name or 'search' in name:
            return 'FAISS_SEARCH'
        if 'department' in name or 'mapping' in name:
            return 'DEPARTMENT_MAPPING'
        if 'curriculum' in name:
            return 'CURRICULUM_PLAN'
        if 'llm' in name or 'fallback' in name:
            return 'LLM_FALLBACK'
        return ''

    owner_hint = (data.get('owner_hint') or '').strip()
    if not owner_hint:
        if pipeline and isinstance(pipeline, list) and isinstance(pipeline[0], dict):
            # pipeline의 에이전트명을 표준 토큰으로 변환
            inferred = _agent_name_to_hint(pipeline[0].get('agent', ''))
            owner_hint = inferred or 'LLM_FALLBACK'
        else:
            owner_hint = 'LLM_FALLBACK'

    return {
        'complexity': complexity,
        'is_complex': is_complex,
        'category': data.get('category', complexity),
        'owner_hint': owner_hint,
        'plan': plan or None,
        'reasoning': data.get('reasoning', '')
    }


def robust_json_parse(response: str) -> Optional[Dict[str, Any]]:
    """강화된 JSON 파싱 - 다양한 오류 케이스 처리"""
    logger.info(f"🔍 [JSON파싱] 강화된 파싱 시작: {len(response.strip())} 문자")

    try:
        # 방법 1: 기존 extract_json_block 사용
        parsed = extract_json_block(response)
        if parsed is not None:
            logger.info("✅ [JSON파싱] 기본 extract_json_block 성공")
            return parsed
    except Exception as e:
        logger.info(f"⚠️ [JSON파싱] extract_json_block 실패: {e}")

    try:
        # 방법 2: 텍스트 정리 후 직접 파싱
        cleaned_response = response.strip()

        # JSON 패턴 찾기
        json_match = re.search(r'\{[^{}]*\}', cleaned_response)
        if json_match:
            json_text = json_match.group()
            logger.info(f"🔍 [JSON파싱] JSON 패턴 발견: {repr(json_text)}")

            # JSON 키를 올바른 형식으로 표준화
            try:
                # 먼저 원본 JSON 파싱 시도
                json.loads(json_text)
                fixed_json = json_text
                logger.info("🔧 [JSON파싱] 원본 JSON이 이미 올바름")
            except json.JSONDecodeError:
                # 키 따옴표 문제 수정 - 더 정확한 패턴 사용
                # 이미 따옴표가 있는 키는 건드리지 않고, 없는 키만 수정
                fixed_json = re.sub(r'(?<!["\'])([a-zA-Z_][a-zA-Z0-9_]*)\s*(?=:)', r'"\1"', json_text)
                logger.info("🔧 [JSON파싱] 키 따옴표 수정 적용")

            logger.info(f"🔧 [JSON파싱] 수정된 JSON: {repr(fixed_json)}")

            parsed = json.loads(fixed_json)
            logger.info("✅ [JSON파싱] 키 수정 파싱 성공")
            return parsed
    except Exception as e:
        logger.info(f"⚠️ [JSON파싱] 키 수정 파싱 실패: {e}")

    try:
        # 방법 3: 정규식으로 직접 값 추출
        logger.info("🔍 [JSON파싱] 정규식 직접 추출 시도")

        needs_history_match = re.search(r'["\']?needs_history["\']?\s*:\s*(true|false)', response, re.IGNORECASE)
        reasoning_match = re.search(r'["\']?reasoning["\']?\s*:\s*["\']([^"\']+)["\']', response)
        context_type_match = re.search(r'["\']?context_type["\']?\s*:\s*["\']([^"\']+)["\']', response)
        confidence_match = re.search(r'["\']?confidence["\']?\s*:\s*([\d.]+)', response)

        if needs_history_match:
            result = {
                "needs_history": needs_history_match.group(1).lower() == 'true',
                "reasoning": reasoning_match.group(1) if reasoning_match else "정규식 추출",
                "context_type": context_type_match.group(1) if context_type_match else "independent",
                "confidence": float(confidence_match.group(1)) if confidence_match else 0.8
            }
            logger.info("✅ [JSON파싱] 정규식 직접 추출 성공")
            return result
    except Exception as e:
        logger.info(f"⚠️ [JSON파싱] 정규식 직접 추출 실패: {e}")

    # 모든 방법 실패
    logger.error("❌ [JSON파싱] 모든 JSON 파싱 방법 실패")
    return None
