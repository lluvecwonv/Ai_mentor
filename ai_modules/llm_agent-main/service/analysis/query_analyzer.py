"""
Query 복잡도 분석 Agent - LangChain 버전 (v3)
- LLM 리즈닝 + 규칙 결합 라우팅
- 엔티티 추출(과목/학과/행동 의도), 파이프라인 플랜 생성
- 쿼리 확장(expansion_context / expansion_keywords / augmentation 한 줄)

주의: 이 모듈은 LlmClientLangChain(chat_completion)을 사용합니다.
"""
from __future__ import annotations

import logging
from typing import Dict, Any
import asyncio

# LLM 클라이언트 단순화
from utils.llm_client_langchain import LlmClientLangChain as LlmClientLangChainAdvanced

# 유틸리티 임포트
from utils.prompt_loader import load_prompt
from utils.json_utils import extract_json_block, to_router_decision


# 로거 설정
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 콘솔/파일 핸들러 추가 (이미 설정되어 있지 않은 경우)
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    try:
        from pathlib import Path
        logs_dir = Path('/home/dbs0510/AiMentor_edit/ai_modules/llm_agent-main/logs')
        logs_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(str(logs_dir / 'llm-agent.log'), encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as _e:
        logger.warning(f"파일 로깅 설정 실패: {_e}")

"""
데이터 모델(dataclass)은 제거했습니다. 라우팅 결정 정규화는 utils.json_utils.to_router_decision 사용.
"""


class QueryAnalyzer:
    """Query 복잡도 분석 및 분류 - LangChain LLM + 규칙 결합 (v3)"""

    def __init__(self, conversation_memory=None):
        logger.info("QueryAnalyzer 초기화 시작")
        self.llm_client = LlmClientLangChainAdvanced()
        self.conversation_memory = conversation_memory
        logger.debug("LangChain Query Analyzer(v3) 초기화 완료")

    async def analyze_query_parallel(self, query: str, session_id: str = "default", contextual_prompt: str = None) -> Dict[str, Any]:
        """병렬 쿼리 분석 + 확장 - 확장된 컨텍스트를 분석에 활용"""
        _qprev = (query[:200] + '...') if len(query) > 200 else query
        logger.debug(f"병렬 쿼리 분석 시작: '{_qprev}'")

        # 히스토리 컨텍스트 추출
        history_context = self._get_history_context(session_id)
        if history_context:
            logger.info(f"히스토리 컨텍스트 활용: {len(history_context)} 문자")
        else:
            logger.debug("히스토리 컨텍스트 없음")

        # 1단계: 먼저 쿼리 확장을 수행
        try:
            expansion_result = await self._expand_query_async(query, history_context)
            logger.info(f"🔍 쿼리 확장 완료: context='{expansion_result.get('expansion_context', '')[:50]}...', keywords='{expansion_result.get('expansion_keywords', '')}'")

            # 2단계: 확장된 정보를 조합하여 향상된 쿼리 생성
            enhanced_query = self._combine_expansion_with_query(query, expansion_result)
            logger.info(f"🔗 확장 정보가 조합된 향상된 쿼리: '{enhanced_query}'")

            # 3단계: 향상된 쿼리로 라우팅 분석 수행
            analysis_result = await self._analyze_routing_async(enhanced_query, contextual_prompt, history_context)

        except Exception as e:
            logger.error(f"쿼리 분석 중 오류 발생: {e}")
            # 기본값으로 대체
            analysis_result = {
                "decision_question_type": "general",
                "decision_data_source": "llm",
                "complexity": "medium",
                "owner_hint": "llm-agent",
                "plan": ["일반적인 질문으로 처리"],
                "reasoning": "오류로 인한 기본 처리"
            }
            expansion_result = {
                "expansion_context": "",
                "expansion_keywords": ""
            }

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

        logger.info(
            f"📊 향상된 병렬 분석 완료: {analysis_result.get('category')} 복잡도, {analysis_result.get('owner_hint')} 담당"
        )
        return combined_result

    # 동기 분석/직접 응답 생성 메서드는 사용되지 않아 제거했습니다.

    def get_performance_stats(self) -> dict:
        """성능 통계 조회 - 간단한 버전"""
        llm_stats = self.llm_client.get_performance_stats() if hasattr(self.llm_client, 'get_performance_stats') else {}

        # 기존 인터페이스 호환성 유지
        legacy_stats = {
            "analyzer_type": "LangChain_v3",
            "total_analyses": 0,
            "total_analysis_time": 0.0,
            "avg_analysis_time": 0.0,
            "success_rate": 100.0,
            "llm_stats": llm_stats,
        }

        return legacy_stats


    # Parsing & Post-rules는 utils.json_utils.to_router_decision 사용으로 대체했습니다.

    # 동기 expand_query는 사용되지 않아 제거했습니다. 비동기 버전만 유지합니다.

    # -------- 병렬 처리용 비동기 메서드들 ---------
    async def _analyze_routing_async(self, query: str, contextual_prompt: str = None, history_context: str = None) -> Dict[str, Any]:
        """비동기 라우팅 분석 (히스토리 컨텍스트 포함)"""
        _qprev = (query + '...') 
        logger.debug(f"🔍 라우팅 분석 시작: '{_qprev}'")


        # 프롬프트 로드 및 컨텍스트 처리
        router_prompt = load_prompt('router_prompt').replace('{query}', query)

        # 히스토리 컨텍스트 추가
        if history_context:
            history_section = f"\n\n### 이전 대화 맥락:\n{history_context}\n\n### 현재 질문 분석:"
            router_prompt = router_prompt.replace('{query}', f"{history_section}\n사용자 질문: {query}")
            logger.info("📚 히스토리 컨텍스트가 라우팅 분석에 추가됨")

        if contextual_prompt:
            router_prompt = f"{contextual_prompt}\n\n{router_prompt}"
            logger.info("📝 컨텍스트 프롬프트 적용됨")

        logger.debug("🤖 LLM 라우팅 분석 요청 시작")
        # LLM 호출 - 동기/비동기 클라이언트 호환성 처리
        try:
            import asyncio
            if asyncio.iscoroutinefunction(self.llm_client.chat_completion):
                response = await self.llm_client.chat_completion(
                    messages=[{"role": "user", "content": router_prompt}],
                    model="gpt-4o-mini"
                )
            else:
                # 동기 메서드인 경우 별도 스레드에서 실행
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.llm_client.chat_completion(
                        messages=[{"role": "user", "content": router_prompt}],
                        model="gpt-4o-mini"
                    )
                )
        except Exception as e:
            logger.error(f"LLM 호출 실패: {e}")
            raise
        logger.info(f"✅ LLM 라우팅 응답 받음: {len(response)}자")
        logger.info(f"🔍 LLM 원본 응답: {response}")

        # 결과 파싱 및 변환
        data = extract_json_block(response) or {}
        logger.info(f"📊 원본 분석 데이터: {data}")

        decision = to_router_decision(data)
        logger.info(f"🎯 라우팅 결정: complexity={decision.get('complexity')}, agent={decision.get('owner_hint')}")
        logger.info(f"📋 계획: {decision.get('plan', [])}")
        reason = (decision.get('reasoning', '') or '')
        if reason:
            logger.info(f"REASON: {reason}")

        return decision


    async def _expand_query_async(self, query: str, history_context: str = None) -> Dict[str, Any]:
        """비동기 쿼리 확장 (히스토리 컨텍스트 포함)"""
        _qprev = (query + '...') 
        logger.debug(f"🔍 쿼리 확장 시작: '{_qprev}'")

        # 쿼리 확장 프롬프트 로드
        expansion_prompt = load_prompt('query_reasoning_prompt').replace('{query}', query)

        # 히스토리 컨텍스트 추가
        if history_context:
            history_section = f"\n\n### 이전 대화 맥락:\n{history_context}\n\n### 현재 질문 확장:"
            expansion_prompt = expansion_prompt.replace('{query}', f"{history_section}\n사용자 질문: {query}")
            logger.info("📚 히스토리 컨텍스트가 쿼리 확장에 추가됨")
        logger.debug("📝 쿼리 확장 프롬프트 준비 완료")

        logger.debug("🤖 LLM 쿼리 확장 요청 시작")
        # LLM 호출 - 동기/비동기 클라이언트 호환성 처리
        try:
            import asyncio
            if asyncio.iscoroutinefunction(self.llm_client.chat_completion):
                response = await self.llm_client.chat_completion(
                    messages=[{"role": "user", "content": expansion_prompt}],
                    model="gpt-4o-mini"
                )
            else:
                # 동기 메서드인 경우 별도 스레드에서 실행
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.llm_client.chat_completion(
                        messages=[{"role": "user", "content": expansion_prompt}],
                        model="gpt-4o-mini"
                    )
                )
        except Exception as e:
            logger.error(f"LLM 확장 호출 실패: {e}")
            raise
        logger.debug(f"✅ LLM 확장 응답 받음: {len(response)}자")

        # 결과 파싱
        expansion_data = extract_json_block(response) or {}
        logger.debug(f"📊 확장 데이터: context='{expansion_data.get('expansion_context', '')[:50]}...', keywords='{expansion_data.get('expansion_keywords', '')}'")

        # expanded_queries 생성 (벡터 검색용)
        expansion_keywords = expansion_data.get("expansion_keywords", "")
        expanded_queries = None
        if expansion_keywords:
            keywords_list = [k.strip() for k in expansion_keywords.split(',') if k.strip()]
            if keywords_list:
                expanded_queries = [
                    {"text": query, "kind": "base"}  # 원본 쿼리
                ] + [
                    {"text": kw, "kind": "keyword"} for kw in keywords_list
                ]

        result = {
            "expansion_context": expansion_data.get("expansion_context", ""),
            "expansion_keywords": expansion_keywords,
            "expansion_augmentation": expansion_data.get("expansion_augmentation", ""),
            "expanded_queries": expanded_queries,  # 벡터 검색용 확장 쿼리
            "constraints": expansion_data.get("constraints", {}),
            "decision_question_type": expansion_data.get("decision_question_type", ""),
            "decision_data_source": expansion_data.get("decision_data_source", "")
        }
        logger.info(f"🎯 확장 완료: question_type={result.get('decision_question_type')}, data_source={result.get('decision_data_source')}")

        return result

    def _get_history_context(self, session_id: str) -> str:
        """세션의 최근 대화 히스토리를 요약하여 컨텍스트로 반환"""
        if not self.conversation_memory:
            return ""

        try:
            # 최근 5개 대화 교환 가져오기
            recent_exchanges = self.conversation_memory.get_recent_exchanges(session_id, limit=5)
            if not recent_exchanges:
                return ""

            # 히스토리를 요약 형태로 변환
            context_parts = []
            for exchange in recent_exchanges[-3:]:  # 최근 3개만 사용
                user_msg = exchange.get('user_message', '')
                ai_response = exchange.get('ai_response', '')

                if user_msg and ai_response:
                    # 응답을 간단히 요약 (처음 100자만)
                    ai_summary = ai_response[:100] + "..." if len(ai_response) > 100 else ai_response
                    context_parts.append(f"사용자: {user_msg}")
                    context_parts.append(f"AI: {ai_summary}")

            if context_parts:
                history_context = "\n".join(context_parts)
                logger.debug(f"히스토리 컨텍스트 생성: {len(history_context)}자")
                return history_context

        except Exception as e:
            logger.warning(f"히스토리 컨텍스트 추출 실패: {e}")

        return ""

    def _combine_expansion_with_query(self, original_query: str, expansion_result: Dict[str, Any]) -> str:
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
            logger.info(f"🔗 [쿼리조합] 원본: '{original_query[:50]}...' + 확장정보 {len(enhancement_parts)}개")
            return enhanced_query
        else:
            logger.info("🔗 [쿼리조합] 확장정보 없음, 원본 쿼리 사용")
            return original_query
