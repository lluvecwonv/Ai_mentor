"""
LLM 기반 대화 맥락 분석기 - 이전 대화 히스토리 활용 방식 판단
"""

import logging
import json
from typing import Dict, List, Any
from pathlib import Path
from openai import OpenAI

logger = logging.getLogger(__name__)

class ConversationContextAnalyzer:
    """
    LLM을 사용하여 현재 질문이 이전 대화와 어떻게 연관되는지 분석하는 분석기
    """

    def __init__(self, openai_client: OpenAI):
        self.llm_client = openai_client
        self.prompt_path = Path(__file__).parent.parent / "prompts" / "history_aware_query_analyzer.txt"
        self._load_prompt()
        logger.info("ConversationContextAnalyzer 초기화 완료 (LLM 모드)")

    def _load_prompt(self):
        """프롬프트 파일 로드"""
        try:
            with open(self.prompt_path, 'r', encoding='utf-8') as f:
                self.system_prompt = f.read()
            logger.info("✅ 히스토리 분석 프롬프트 로드 완료")
        except Exception as e:
            logger.error(f"❌ 프롬프트 파일 로드 실패: {e}")
            self.system_prompt = "현재 질문이 이전 대화와 어떻게 연관되는지 분석하세요."

    async def analyze_context_relevance(self, current_query: str, history: List[Dict]) -> Dict[str, Any]:
        """LLM을 사용하여 히스토리 활용 방식 분석"""
        # 히스토리가 없으면 독립적 질문으로 처리
        if not history or len(history) == 0:
            return {
                "history_usage": {
                    "reuse_previous": False,
                    "relationship": "new_search",
                    "context_integration": "이전 대화가 없어 새로운 검색 수행"
                }
            }

        return await self._llm_analyze_history_usage(current_query, history)

    async def _llm_analyze_history_usage(self, current_query: str, history: List[Dict]) -> Dict[str, Any]:
        """LLM으로 히스토리 활용 방식 분석"""
        try:
            # 히스토리 포맷팅
            history_context = self._format_history_for_prompt(history)

            # 프롬프트 구성
            prompt = self.system_prompt.format(
                history_context=history_context,
                current_query=current_query
            )

            logger.info(f"🔍 [ContextAnalyzer] LLM 히스토리 분석 시작: '{current_query}'")

            response = self.llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )

            result_text = response.choices[0].message.content.strip()
            logger.info(f"📝 [ContextAnalyzer] LLM 응답: {result_text}")

            # 강화된 JSON 파싱
            return self._robust_json_parse(result_text)

        except Exception as e:
            logger.error(f"❌ [ContextAnalyzer] LLM 분석 실패: {e}")
            return self._create_fallback_result("LLM 분석 실패")

    def _format_history_for_prompt(self, history: List[Dict]) -> str:
        """히스토리를 프롬프트용으로 포맷팅"""
        formatted_history = []

        for entry in history[-3:]:  # 최근 3개 대화만 사용
            user_query = entry.get('user_query', '')
            ai_response = entry.get('ai_response', '')

            formatted_history.append(f"사용자: {user_query}")
            if ai_response:
                # AI 응답에서 핵심 정보만 추출 (첫 100자)
                response_summary = ai_response[:100] + "..." if len(ai_response) > 100 else ai_response
                formatted_history.append(f"AI: {response_summary}")

        return " | ".join(formatted_history)

    def _robust_json_parse(self, result_text: str) -> Dict[str, Any]:
        """강화된 JSON 파싱 로직 - 다양한 형태의 JSON 응답 처리"""
        import re

        # 1차: 직접 JSON 파싱 시도
        try:
            result = json.loads(result_text)
            logger.info(f"✅ [JSON Parser] 직접 파싱 성공: {result}")
            return result
        except json.JSONDecodeError as e:
            logger.debug(f"⚠️ [JSON Parser] 직접 파싱 실패: {e}")

        # 2차: 코드 블록에서 JSON 추출 시도
        json_patterns = [
            r'```json\s*(\{.*?\})\s*```',  # ```json { ... } ```
            r'```\s*(\{.*?\})\s*```',      # ``` { ... } ```
            r'(\{[^{}]*"history_usage"[^{}]*\})',  # history_usage가 포함된 JSON (간단/안전)
            r'(\{.*?\})',                  # 일반 JSON 객체
        ]

        for i, pattern in enumerate(json_patterns, 1):
            try:
                matches = re.findall(pattern, result_text, re.DOTALL | re.MULTILINE)
                if matches:
                    # 가장 긴 매치를 선택 (더 완전한 JSON일 가능성)
                    json_text = max(matches, key=len).strip()
                    result = json.loads(json_text)
                    logger.debug(f"✅ [JSON Parser] 패턴 {i} 파싱 성공")
                    return result
            except (json.JSONDecodeError, Exception) as e:
                logger.debug(f"⚠️ [JSON Parser] 패턴 {i} 실패: {e}")
                continue

        # 3차: 부분 JSON 복구 시도
        try:
            # "history_usage" 키가 있는지 확인하고 기본 구조 생성
            if "history_usage" in result_text.lower():
                logger.debug("🔧 [JSON Parser] history_usage 키 발견, 부분 복구 시도")

                # 기본 구조로 시작
                fallback_result = {
                    "needs_context": False,
                    "confidence": 0.5,
                    "history_usage": {
                        "reuse_previous": False,
                        "relationship": "parsing_error",
                        "context_integration": "JSON 파싱 오류로 기본값 사용"
                    }
                }

                # 간단한 패턴으로 일부 값 추출 시도
                if "true" in result_text.lower():
                    fallback_result["needs_context"] = True
                    fallback_result["history_usage"]["reuse_previous"] = True

                logger.info("🔧 [JSON Parser] 부분 복구 완료")
                return fallback_result
        except Exception as e:
            logger.debug(f"⚠️ [JSON Parser] 부분 복구 실패: {e}")

        # 4차: 완전한 폴백
        logger.warning("❌ [JSON Parser] 모든 파싱 시도 실패, 안전한 기본값 반환")
        return self._create_fallback_result(f"JSON 파싱 실패: {result_text[:100]}...")

    def _create_fallback_result(self, reason: str) -> Dict[str, Any]:
        """안전한 기본값 반환"""
        return {
            "history_usage": {
                "reuse_previous": False,
                "relationship": "new_search",
                "context_integration": f"분석 실패로 인한 새로운 검색: {reason}"
            }
        }

    def should_include_history(self, analysis_result: Dict[str, Any]) -> bool:
        """분석 결과를 바탕으로 히스토리 포함 여부 결정"""
        history_usage = analysis_result.get("history_usage", {})
        return history_usage.get("reuse_previous", False)
