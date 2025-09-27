"""
간단한 쿼리 라우터 - 직접 핸들러 호출 방식 (맥락 분석 통합)
"""

import logging
from typing import Dict, Any, List
from utils.json_utils import to_router_decision
# LangGraph 전용 모드로 간소화
from handlers.curriculum_handler import CurriculumHandler

logger = logging.getLogger(__name__)

class Router:
    """간단한 라우터 - 핸들러 직접 호출 (맥락 분석 통합)"""

    def __init__(self, vector_processor=None, sql_processor=None, mapping_processor=None, llm_processor=None):
        self.vector_processor = vector_processor
        self.sql_processor = sql_processor
        self.mapping_processor = mapping_processor
        self.llm_processor = llm_processor
        # LangGraph 전용 모드로 간소화
        self.curriculum_handler = CurriculumHandler()

    async def process(self, query_analysis: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """분석 결과에 따라 바로 실행"""
        logger.info(f"🚨 라우터 처리 시작: complexity={query_analysis.get('complexity', 'NONE')}")
        complexity = query_analysis.get('complexity', 'medium')

        # plan 우선, 없으면 pipeline도 허용 (호환)
        pipeline = query_analysis.get('plan') or query_analysis.get('pipeline') or []

        # 규칙 강화: 복수 에이전트가 명시된 plan/pipeline이면 heavy로 승격
        if complexity == 'medium' and isinstance(pipeline, list) and len(pipeline) > 1:
            logger.info("중간 복잡도이지만 다단계 플랜 감지 → heavy로 승격")
            complexity = 'heavy'

        # 🔍 모든 복잡도에서 맥락 분석 수행 (heavy에서만 하던 것을 모든 레벨로 확장)
        user_msg = data.get("user_message", "")
        session_id = data.get("session_id", "default")
        conversation_memory = data.get("conversation_memory")
        history_context = ""
        context_analysis = None

        if conversation_memory:
            try:
                recent_exchanges = conversation_memory.get_recent_exchanges(
                    session_id=session_id,
                    limit=3  # 맥락 분석을 위해 3개까지 확인
                )

                if recent_exchanges and self.context_analyzer:
                    # 맥락 분석 수행
                    context_analysis = await self.context_analyzer.analyze_context_relevance(
                        current_query=user_msg,
                        history=recent_exchanges
                    )

                    logger.info(f"🔍 [맥락분석] 결과: {context_analysis.get('context_type', 'unknown')}")
                    logger.info(f"📚 [맥락분석] 히스토리 필요: {context_analysis.get('needs_history', False)}")
                    logger.info(f"💭 [맥락분석] 이유: {context_analysis.get('reasoning', 'N/A')}")

                    # 맥락 분석 결과에 따라 히스토리 포함 여부 결정
                    if self.context_analyzer.should_include_history(context_analysis):
                        # 히스토리가 필요한 경우에만 포함
                        history_messages = []
                        for exchange in recent_exchanges[-2:]:  # 최근 2개만
                            if exchange.get('user_message'):
                                history_messages.append(f"사용자: {exchange['user_message']}")
                            if exchange.get('ai_response'):
                                history_messages.append(f"어시스턴트: {exchange['ai_response']}")

                        history_context = "\n".join(history_messages)
                        logger.info(f"✅ [연속대화] 히스토리 포함: {len(history_context)} 문자")
                    else:
                        # 사용자 메시지 정규화 (줄바꿈 제거)
                        clean_user_msg = user_msg.replace('\n', ' ').replace('\r', ' ').strip()
                        logger.info(f"🎯 [독립질문] 히스토리 제외: '{clean_user_msg[:50]}...'")
                else:
                    logger.info("📭 [맥락분석] 이전 대화 없음")

            except Exception as e:
                logger.warning(f"⚠️ [맥락분석] 오류: {e}")
                # 오류 시 안전하게 독립적 처리
                context_analysis = {
                    "needs_history": False,
                    "context_type": "independent",
                    "reasoning": f"분석 오류로 인한 기본 처리: {str(e)}"
                }

        # 히스토리 컨텍스트를 data에 추가 (독립적인 질문이 아닌 경우만)
        if history_context and context_analysis.get("needs_history", False):
            data = {**data, "history_context": history_context, "context_analysis": context_analysis}

        def _map_owner_hint_to_sequence(owner_hint: str) -> List[str]:
            hint = (owner_hint or '').upper()
            parts = [p.strip() for p in hint.split('+')] if '+' in hint else ([hint] if hint else [])
            seq: List[str] = []
            for p in parts:
                if 'SQL' in p:
                    seq.append('SQL-Agent')
                elif 'FAISS' in p:
                    seq.append('FAISS-Search-Agent')
                elif 'DEPARTMENT' in p:
                    seq.append('Department-Mapping-Agent')
                elif 'LLM' in p:
                    seq.append('LLM-Fallback-Agent')
            return seq or ['LLM-Fallback-Agent']

        # 🧪 임시 테스트: Heavy 모드 강제 실행
        if "데이터베이스" in data.get("user_message", "") and "벡터" in data.get("user_message", ""):
            logger.info("🧪 테스트: Heavy 모드 강제 실행")
            complexity = 'heavy'
            # plan 강제 생성
            query_analysis['plan'] = [
                {"step": 1, "agent": "Department-Mapping-Agent", "goal": "학과 정보 조회"},
                {"step": 2, "agent": "FAISS-Search-Agent", "goal": "벡터 검색 수행"}
            ]

        # light -> LLM만
        if complexity == 'light':
            logger.info("💡 Light 복잡도 - LLM 직접 처리")
            llm_result = await self.llm_processor.process(data)
            return {"final_result": llm_result, "processing_type": "llm_only"}

        # medium -> 단일 에이전트
        if complexity == 'medium':
            logger.info("🔧 Medium 복잡도 - 단일 에이전트 처리")
            agent = ''
            if isinstance(pipeline, list) and pipeline:
                # 정상 플랜이면 첫 agent 사용
                first = pipeline[0] if isinstance(pipeline[0], dict) else {}
                agent = first.get('agent', '')
            if not agent:
                # 플랜이 없으면 owner_hint로 단일 에이전트 결정
                owner_hint = str(query_analysis.get('owner_hint', ''))
                seq = _map_owner_hint_to_sequence(owner_hint)
                agent = seq[0] if seq else 'LLM-Fallback-Agent'

            if agent == 'FAISS-Search-Agent':
                # 벡터 검색 + LLM
                vector_result = await self.vector_processor.process(data)
                data_with_context = {**data, "search_context": vector_result}
                llm_result = await self.llm_processor.process(data_with_context)
                return {"final_result": llm_result, "processing_type": "vector_focused", "contexts": {"vector": vector_result}}

            elif agent == 'SQL-Agent':
                # SQL + LLM
                sql_result = await self.sql_processor.process(data)
                data_with_context = {**data, "sql_context": sql_result}
                llm_result = await self.llm_processor.process(data_with_context)
                return {"final_result": llm_result, "processing_type": "sql_focused", "contexts": {"sql": sql_result}}

            elif agent == 'Department-Mapping-Agent':
                # 학과 매핑 + LLM
                mapping_result = await self.mapping_processor.process(data)
                data_with_context = {**data, "mapping_context": mapping_result}
                llm_result = await self.llm_processor.process(data_with_context)
                return {"final_result": llm_result, "processing_type": "mapping_focused", "contexts": {"mapping": mapping_result}}

            elif agent == 'Curriculum-Agent':
                # 커리큘럼 생성
                logger.info("🎓 커리큘럼 에이전트 처리 시작")
                try:
                    user_message = data.get("user_message", "")
                    session_id = data.get("session_id", "default")

                    curriculum_result = await self.curriculum_handler.handle(
                        user_message=user_message,
                        query_analysis=query_analysis,
                        session_id=session_id,
                        query=user_message
                    )

                    logger.info(f"✅ 커리큘럼 처리 완료: {len(curriculum_result)}자")
                    return {
                        "final_result": curriculum_result,
                        "processing_type": "curriculum_focused",
                        "contexts": {"curriculum": curriculum_result}
                    }

                except Exception as e:
                    logger.error(f"❌ 커리큘럼 처리 실패: {e}")
                    # 실패 시 LLM 폴백
                    llm_result = await self.llm_processor.process(data)
                    return {"final_result": llm_result, "processing_type": "curriculum_focused"}

            else:
                # LLM 폴백
                llm_result = await self.llm_processor.process(data)
                return {"final_result": llm_result, "processing_type": "llm_fallback"}

        # heavy -> ToT
        if complexity == 'heavy':
            logger.info(f"⚡ Heavy 복잡도 감지 - ToT 실행 시작: {query_analysis.get('owner_hint')}")
            try:
                from service.core.tot_service import ToTCoreService, Message
                user_msg = data.get("user_message", "")
                session_id = data.get("session_id", "default")
                conversation_memory = data.get("conversation_memory")

                logger.info(f"🎯 ToT 입력: user_msg='{user_msg[:50]}...', session_id={session_id}")

                # ToT에 processor들과 conversation_memory 전달
                tot = ToTCoreService(
                    vector_processor=self.vector_processor,
                    sql_processor=self.sql_processor,
                    mapping_processor=self.mapping_processor,
                    llm_processor=self.llm_processor,
                    session_id=session_id,
                    conversation_memory=conversation_memory
                )

                router_decision = to_router_decision(query_analysis or {})
                logger.info(f"📋 ToT에 전달할 라우터 결정: {router_decision}")

                # query_analysis에서 확장 키워드 정보를 context로 전달 (맥락 분석 결과 포함)
                context = {
                    "expanded_queries": query_analysis.get("expanded_queries"),
                    "expansion_keywords": query_analysis.get("expansion_keywords"),
                    "expansion_context": query_analysis.get("expansion_context"),
                    "analysis": query_analysis,
                    "history_context": history_context,
                    "context_analysis": context_analysis
                }

                # LLM이 추출한 학과 정보를 context에 전달
                entities = query_analysis.get("entities", {})
                extracted_dept = entities.get("department") if entities else None

                if extracted_dept:
                    context["extracted_department"] = extracted_dept
                    logger.info(f"🏫 ToT context에 추출된 학과 전달: {extracted_dept}")

                result = tot.run_agent(
                    [Message(role="user", content=user_msg)],
                    session_id=session_id,
                    router_decision=router_decision,
                    context=context
                )
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                logger.info(f"✅ ToT 실행 완료: content 길이={len(content)}")

                # ToT 결과 처리
                if not isinstance(result, dict):
                    result = {"choices": [{"message": {"content": str(result)}}]}

                result["processing_type"] = "tot"
                result["final_result"] = content
                result["tot_context"] = context

                # ToT 완료 후 ConversationMemory에 결과 저장
                if conversation_memory and content:
                    conversation_memory.add_exchange(
                        session_id=session_id,
                        user_message=user_msg,
                        assistant_response=content
                    )
                    logger.info(f"💾 ToT 결과를 ConversationMemory에 저장 완료")

                return result
            except Exception as e:
                logger.error(f"❌ ToT 실행 실패: {e}")
                import traceback
                logger.error(f"ToT 스택 트레이스: {traceback.format_exc()}")
                llm_result = await self.llm_processor.process(data)
                return {"final_result": llm_result, "processing_type": "llm_fallback"}

        # ToT에서 처리되지 않은 경우 - LLM 폴백으로 처리
        logger.info(f"📝 ToT 미처리 케이스 - LLM 폴백: complexity={complexity}")
        llm_result = await self.llm_processor.process(data)
        return {"final_result": llm_result, "processing_type": "tot_fallback"}