"""
라우팅 관련 노드들
복잡도 분석 및 경로 결정
"""

import logging
from typing import Dict, Any, Literal
from .base_node import BaseNode, NodeTimer

logger = logging.getLogger(__name__)


class RoutingNodes(BaseNode):
    """라우팅 관련 노드들"""

    def __init__(self, query_analyzer, openai_client=None):
        self.query_analyzer = query_analyzer

    async def router_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """라우터 노드 - 복잡도 분석 및 라우팅"""
        with NodeTimer("Router") as timer:
            try:
                logger.info("🎬 [ROUTER] 라우터 노드 시작")
                logger.info("🔧 [DEBUG] 1단계: get_user_message 호출 전")
                user_message = self.get_user_message(state)
                logger.info("🔧 [DEBUG] 2단계: get_user_message 호출 완료")

                session_id = state.get("session_id", "default")
                logger.info(f"🎬 [ROUTER] 사용자 메시지: '{user_message}...'")
                logger.info(f"🎬 [ROUTER] 세션 ID: {session_id}")

                # 메시지 전처리 (여러 줄이면 마지막 줄만 사용)
                lines = user_message.strip().split('\n')
                if len(lines) > 1:
                    clean_user_message = lines[-1].strip()
                    logger.info(f"🎯 [메시지처리] 최신 질문만 처리: '{clean_user_message}'")
                else:
                    clean_user_message = user_message
                    logger.info(f"🎯 [메시지처리] 단일 질문 처리")

                # 맥락 분석 제거로 인한 기본값 설정
                context_analysis = None

                # 쿼리 분석 (깔끔한 메시지로)
                logger.info("🧠 QueryAnalyzer 호출 시작")
                analysis_result = await self.query_analyzer.analyze_query_parallel(
                    clean_user_message,  # 히스토리 없는 깔끔한 질문만
                    session_id=session_id
                )
                logger.info("🧠 QueryAnalyzer 호출 완료")

                complexity = analysis_result.get('complexity', 'medium')
                plan = analysis_result.get('plan', [])
                logger.info(f"🔍 [DEBUG] plan 타입: {type(plan)}, 값: {plan}")
                # plan이 None인 경우 빈 리스트로 처리
                if plan is None:
                    logger.info("🔧 plan이 None이므로 빈 리스트로 변경")
                    plan = []
                # QueryAnalyzer는 'enhanced_query'와 'expansion_keywords'를 반환
                expanded_query = analysis_result.get('enhanced_query', analysis_result.get('expanded_query', user_message))
                keywords = analysis_result.get('expansion_keywords', analysis_result.get('keywords', ''))

                # 쿼리 분석 결과 로깅
                logger.info(f"📊 [Router] 쿼리 분석 완료:")
                logger.info(f"   - 원본 쿼리: {user_message}")
                logger.info(f"   - 확장 쿼리: {expanded_query}")
                logger.info(f"   - 키워드: {keywords}")
                logger.info(f"   - 복잡도: {complexity}")
                logger.info(f"   - 계획: {len(plan) if plan else 0} 단계")

                # 복잡도 승격 로직
                if complexity == 'medium' and isinstance(plan, list) and len(plan) > 1:
                    logger.info("중간 복잡도이지만 다단계 플랜 감지 → heavy로 승격")
                    complexity = 'heavy'

                logger.info(f"✅ 라우팅 완료: {complexity} ({len(plan) if plan else 0} 단계 계획)")

                return {
                    **state,
                    "route": complexity,
                    "complexity": complexity,
                    "routing_reason": analysis_result.get('reasoning', ''),
                    "plan": plan,
                    "plan_confidence": analysis_result.get('confidence', 0.7),
                    "expanded_query": expanded_query,
                    "keywords": keywords,
                    "clean_user_message": clean_user_message,  # 맥락 분석 후 정리된 메시지
                    "context_analysis": context_analysis,  # 맥락 분석 결과
                    "needs_history": context_analysis.get('needs_history', False) if context_analysis else False,
                    "step_times": self.update_step_time(state, "router", timer.duration)
                }

            except Exception as e:
                logger.error(f"❌ 라우터 노드 실패: {e}")
                import traceback
                logger.error(f"❌ 상세 스택 트레이스:\n{traceback.format_exc()}")

                # 예외 발생 시에도 기본 분석은 시도 (plan 정보 보존을 위해)
                try:
                    logger.warning(f"🔧 예외 복구: QueryAnalyzer 최소 실행 시도")
                    user_message = self.get_user_message(state)
                    session_id = state.get("session_id", "default")

                    analysis_result = await self.query_analyzer.analyze_query_parallel(
                        user_message,
                        session_id=session_id
                    )

                    complexity = analysis_result.get('complexity', 'medium')
                    plan = analysis_result.get('plan', [])
                    expanded_query = analysis_result.get('enhanced_query', analysis_result.get('expanded_query', user_message))
                    keywords = analysis_result.get('expansion_keywords', analysis_result.get('keywords', ''))

                    logger.warning(f"🔧 예외 복구 성공: complexity={complexity}, plan_steps={len(plan) if plan else 0}")

                    return {
                        **state,
                        "route": complexity,
                        "complexity": complexity,
                        "routing_reason": f"예외 복구: {analysis_result.get('reasoning', str(e))}",
                        "plan": plan,
                        "plan_confidence": analysis_result.get('confidence', 0.5),
                        "expanded_query": expanded_query,
                        "keywords": keywords,
                        "clean_user_message": user_message,
                        "last_error": str(e),
                        "retry_count": state.get("retry_count", 0) + 1,
                        "step_times": self.update_step_time(state, "router", 0)
                    }
                except Exception as e2:
                    logger.error(f"❌ 예외 복구도 실패: {e2}")

                return {
                    **state,
                    "last_error": str(e),
                    "retry_count": state.get("retry_count", 0) + 1,
                    "route": "medium",  # 기본값
                    "complexity": "medium",
                    "plan": [],
                    "routing_reason": f"모든 분석 실패: {str(e)}",
                    "clean_user_message": self.get_user_message(state)
                }

    def route_by_complexity(self, state: Dict[str, Any]) -> str:
        """복잡도에 따른 세부 라우팅"""
        complexity = state.get("route", "medium")
        plan = state.get("plan", [])
        # plan이 None인 경우 빈 리스트로 처리
        if plan is None:
            plan = []

        # Light 복잡도
        if complexity == "light":
            # 인사말 감지
            user_message = self.get_user_message(state)
            if any(greeting in user_message.lower() for greeting in ["안녕", "hello", "hi", "헬로"]):
                logger.info(f"🔀 라우팅: light_greeting")
                return "light_greeting"
            else:
                logger.info(f"🔀 라우팅: light_llm")
                return "light_llm"

        # Medium 복잡도 - plan 기반으로 세부 분기
        elif complexity == "medium":
            logger.critical(f"🔍🔍🔍 MEDIUM 복잡도 진입! plan={plan}, len={len(plan) if plan else 0}")
            if plan and len(plan) > 0:
                first_agent = plan[0].get("agent", "").upper()
                logger.critical(f"🎯🎯🎯 FIRST_AGENT={first_agent}, 원본={plan[0].get('agent', '')}")
                if "SQL" in first_agent:
                    logger.info(f"🔀 라우팅: medium_sql")
                    return "medium_sql"
                elif "FAISS" in first_agent or "SEARCH" in first_agent:
                    logger.info(f"🔀 라우팅: medium_vector")
                    return "medium_vector"
                elif "CURRICULUM" in first_agent:
                    logger.info(f"🔀 라우팅: medium_curriculum")
                    logger.critical(f"🔥🔥🔥 CURRICULUM 매치됨! agent={first_agent}, plan={plan}")
                    return "medium_curriculum"
                else:
                    logger.critical(f"❌❌❌ 매치 실패! first_agent='{first_agent}'")

            # 기본 medium 처리
            logger.info(f"🔀 라우팅: medium_agent")
            logger.critical(f"🟡🟡🟡 기본 MEDIUM_AGENT로 라우팅")
            return "medium_agent"

        # Heavy 복잡도 - 모든 heavy는 순차 실행
        elif complexity == "heavy":
            logger.info(f"🔀 라우팅: heavy_sequential ({len(plan) if plan else 0}개 단계 순차 실행)")
            return "heavy_sequential"

        # 기본값
        logger.warning(f"⚠️ 알 수 없는 복잡도: {complexity}, medium_agent로 폴백")
        return "medium_agent"