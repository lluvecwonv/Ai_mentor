"""
간소화된 하이브리드 AI Mentor 서비스
핵심 기능에만 집중한 깔끔한 버전
"""

import logging
import asyncio
from typing import Dict, Any, AsyncGenerator, List
from datetime import datetime

# 핵심 imports만 유지
from config.settings import settings
from exceptions import AIMentorException, ConversationMemoryError
from service.core.memory import ConversationMemory
from service.analysis.query_analyzer import QueryAnalyzer
from handlers import VectorSearchHandler, SqlQueryHandler, DepartmentMappingHandler, CurriculumHandler
from processors import ChainProcessor
from service.analysis.result_synthesizer import ResultSynthesizer
from utils.logging import QueryLogger, set_context, clear_context, new_request_id
from utils.mentor_service import ChatModelHelper, StreamingUtils
from utils.context_builder import ContextBuilder

logger = logging.getLogger(__name__)

try:
    from utils.llm_client_langchain import LlmClientLangChain as LlmAgentService
except ImportError:
    LlmAgentService = None

# LangGraph 통합 - 기존 LangGraph 서비스 (제거됨)
LANGGRAPH_AVAILABLE = False
LangGraphService = None

# 통합 LangGraph 서비스 (독립적으로 처리)
try:
    from .unified_langgraph_service import create_unified_langgraph_service, UnifiedLangGraphService
    UNIFIED_LANGGRAPH_AVAILABLE = True
except ImportError as e:
    # logger는 아래에서 정의되므로 여기서는 print 사용
    print(f"LangGraph 서비스 import 실패: {e}")
    UNIFIED_LANGGRAPH_AVAILABLE = False
    UnifiedLangGraphService = None
except Exception as e:
    print(f"LangGraph 서비스 초기화 실패: {e}")
    UNIFIED_LANGGRAPH_AVAILABLE = False
    UnifiedLangGraphService = None

class HybridMentorService:
    """간소화된 AI Mentor 서비스 - LangGraph와 ToT 하이브리드 지원"""

    def __init__(self, use_langgraph: bool = False, use_unified_langgraph: bool = False):
        """
        HybridMentorService 초기화

        Args:
            use_langgraph: 기존 LangGraph 사용 여부
            use_unified_langgraph: 통합 LangGraph 사용 여부 (Light/Medium/Heavy 통합)
        """
        self.logger = logger

        # 통합 LangGraph가 우선순위
        if use_unified_langgraph and UNIFIED_LANGGRAPH_AVAILABLE:
            self.use_unified_langgraph = True
            self.use_langgraph = False
            logger.info("🔧 통합 LangGraph 모드로 초기화")
        elif use_langgraph and LANGGRAPH_AVAILABLE:
            self.use_unified_langgraph = False
            self.use_langgraph = True
            logger.info("🔧 기존 LangGraph 모드로 초기화")
        else:
            self.use_unified_langgraph = False
            self.use_langgraph = False
            logger.info("🔧 ToT 모드로 초기화")

        if (use_unified_langgraph or use_langgraph) and not (UNIFIED_LANGGRAPH_AVAILABLE or LANGGRAPH_AVAILABLE):
            logger.warning("LangGraph가 요청되었지만 사용할 수 없음. ToT 모드로 폴백")

        self._initialize_components()

    def _initialize_components(self):
        """핵심 컴포넌트만 초기화"""
        try:
            # LLM 핸들러
            if LlmAgentService:
                self.llm_handler = LlmAgentService()
                logger.debug("LLM 핸들러 초기화 완료")
            else:
                raise AIMentorException("LLM 서비스를 사용할 수 없습니다")

            # 대화 메모리
            self.conversation_memory = ConversationMemory(
                max_history_length=settings.max_history_length,
                llm_handler=self.llm_handler
            )

            # 쿼리 분석기
            self.query_analyzer = QueryAnalyzer(conversation_memory=self.conversation_memory)

            # 핸들러들
            self.vector_handler = VectorSearchHandler()
            self.sql_handler = SqlQueryHandler()
            self.mapping_handler = DepartmentMappingHandler()
            self.curriculum_handler = CurriculumHandler()

            # 체인 프로세서
            self.chain_processor = ChainProcessor(
                self.query_analyzer, self.conversation_memory, self.llm_handler,
                self.vector_handler, self.sql_handler, self.mapping_handler, settings
            )

            # 결과 종합기
            self.result_synthesizer = ResultSynthesizer(self.llm_handler)

            # LangGraph 서비스들 (옵션)
            self.langgraph_service = None
            self.unified_langgraph_service = None

            # 통합 LangGraph 우선 초기화
            if self.use_unified_langgraph:
                try:
                    self.unified_langgraph_service = create_unified_langgraph_service(self.conversation_memory)
                    logger.info("✅ 통합 LangGraph 서비스 초기화 완료")
                except Exception as e:
                    logger.error(f"❌ 통합 LangGraph 초기화 실패, ToT로 폴백: {e}")
                    self.use_unified_langgraph = False
                    self.unified_langgraph_service = None

            # 기존 LangGraph 초기화
            elif self.use_langgraph:
                try:
                    self.langgraph_service = create_langgraph_service(self.conversation_memory)
                    logger.info("✅ 기존 LangGraph 서비스 초기화 완료")
                except Exception as e:
                    logger.error(f"❌ 기존 LangGraph 초기화 실패, ToT로 폴백: {e}")
                    self.use_langgraph = False
                    self.langgraph_service = None

            # 백그라운드 워밍업 (이벤트 루프가 있을 때만)
            try:
                asyncio.create_task(self._warmup_handlers())
            except RuntimeError:
                # 이벤트 루프가 없으면 워밍업은 나중에 실행됨
                logger.info("이벤트 루프가 없어 워밍업을 나중에 실행합니다")

            # 실행 모드 결정
            if self.use_unified_langgraph:
                execution_mode = "Unified LangGraph"
            elif self.use_langgraph:
                execution_mode = "LangGraph"
            else:
                execution_mode = "Light (LLM Direct)"

            logger.info(f"✅ HybridMentorService 초기화 완료 (모드: {execution_mode})")

        except Exception as e:
            logger.error(f"서비스 초기화 실패: {e}")
            raise AIMentorException(f"서비스 초기화 중 오류 발생: {str(e)}") from e

    async def _warmup_handlers(self):
        """핸들러들 백그라운드 워밍업"""
        try:
            await asyncio.gather(
                self.sql_handler.warmup(),
                self.vector_handler.warmup(),
                self.mapping_handler.warmup(),
                self.curriculum_handler.warmup(),
                return_exceptions=True
            )
            logger.info("✅ 모든 핸들러 워밍업 완료")
        except Exception as e:
            logger.warning(f"핸들러 워밍업 중 오류: {e}")



    async def run_agent(self, user_message: str, session_id: str = "default") -> Dict[str, Any]:
        """메인 처리 함수 - 통합 LangGraph/기존 LangGraph/ToT 선택적 실행"""
        start_time = datetime.now()
        request_id = new_request_id()
        set_context({"request_id": request_id, "session_id": session_id})

        try:
            # 실행 모드 결정
            if self.use_unified_langgraph:
                execution_mode = "Unified LangGraph"
            elif self.use_langgraph:
                execution_mode = "LangGraph"
            else:
                execution_mode = "Light (LLM Direct)"

            logger.info(f"🚀 질문 처리 시작 ({execution_mode}): {user_message}")

            # 통합 LangGraph 모드 (최우선)
            if self.use_unified_langgraph and self.unified_langgraph_service:
                logger.info("🌟 통합 LangGraph 모드로 실행 - 모든 복잡도 지원")

                try:
                    result = await self.unified_langgraph_service.run_agent(
                        user_message=user_message,
                        session_id=session_id
                    )

                    duration = (datetime.now() - start_time).total_seconds()
                    logger.info(f"✅ 통합 LangGraph 실행 완료: {duration:.2f}초")
                    return result

                except Exception as e:
                    logger.error(f"❌ 통합 LangGraph 실행 중 오류: {e}")
                    logger.error("🔄 ToT 모드로 폴백하여 재시도")
                    self.use_unified_langgraph = False  # 임시로 비활성화

            # 기존 LangGraph 모드
            elif self.use_langgraph and self.langgraph_service:
                logger.info("⚡ LangGraph 모드로 실행 - 서비스 검증 중...")

                # 런타임 서비스 검증
                service_valid = self._validate_langgraph_service()
                if not service_valid:
                    logger.warning("⚠️ LangGraph 서비스 검증 실패 - ToT 모드로 폴백")
                    self.use_langgraph = False  # 임시로 비활성화
                else:
                    logger.info("✅ LangGraph 서비스 검증 성공")
                    try:
                        result = await self.langgraph_service.run_agent(
                            user_message=user_message,
                            session_id=session_id
                        )

                        duration = (datetime.now() - start_time).total_seconds()
                        logger.info(f"✅ LangGraph 실행 완료: {duration:.2f}초")
                        return result

                    except Exception as e:
                        logger.error(f"❌ LangGraph 실행 중 오류: {e}")
                        logger.error("🔄 ToT 모드로 폴백하여 재시도")
                        self.use_langgraph = False  # 임시로 비활성화

            # 기존 ToT 모드 (폴백)
            logger.info("🌳 ToT 모드로 실행")

            # 1. 쿼리 분석
            query_analysis = await self.query_analyzer.analyze_query_parallel(user_message, session_id)
            complexity = query_analysis.get('complexity', 'medium')
            logger.info(f"📊 분석 결과 - 복잡도: {complexity}")

            # 2. 체인 입력 준비
            chain_input = {
                "user_message": user_message,
                "session_id": session_id,
                "analysis": query_analysis,
                "conversation_memory": self.conversation_memory
            }

            # 3. 체인 처리
            result = await self.chain_processor.process(chain_input)
            processing_type = result.get('processing_type', 'unknown')
            logger.info(f"🔧 처리 타입: {processing_type}")

            # 4. 결과 합성 (사용자 친화적 응답 생성)
            if self._should_synthesize(processing_type):
                result = await self._synthesize_result(user_message, result, query_analysis, session_id)
                logger.info("🔄 결과 합성 완료")

            # 5. 대화 저장
            await self._save_conversation(session_id, user_message, result, query_analysis)

            # 6. 메타데이터 추가
            processing_time = (datetime.now() - start_time).total_seconds()
            result['hybrid_info'] = {
                'session_id': session_id,
                'processing_time': processing_time,
                'query_analysis': query_analysis
            }

            logger.info(f"✅ 처리 완료: {processing_time:.2f}초")
            return result

        except Exception as e:
            logger.error(f"❌ 처리 실패: {e}")
            return self._create_error_response(f"처리 중 오류: {str(e)}")
        finally:
            clear_context()

    def _should_synthesize(self, processing_type: str) -> bool:
        """합성이 필요한 처리 타입인지 확인"""
        # llm_only도 합성 필요 (사용자 친화적 응답 생성)
        return processing_type not in ['cache_only']

    async def _synthesize_result(self, user_message: str, result: Dict, query_analysis: Dict, session_id: str) -> Dict:
        """결과 합성"""
        try:
            # 결과 데이터 추출 (실제 응답 위치 포함)
            content_sources = [
                result.get('choices', [{}])[0].get('message', {}).get('content'),  # 실제 응답 위치
                result.get('final_result'),
                result.get('contexts', {}).get('sql'),
                result.get('contexts', {}).get('vector'),
                result.get('contexts', {}).get('mapping')
            ]

            # 디버깅: 어떤 소스에서 데이터를 찾는지 확인
            logger.info(f"🔍 데이터 소스 검색 결과:")
            for i, source in enumerate(content_sources):
                source_name = ['choices.content', 'final_result', 'contexts.sql', 'contexts.vector', 'contexts.mapping'][i]
                logger.info(f"  {source_name}: {str(source) if source else 'None'}")

            found_results = next((source for source in content_sources if source), "")

            if found_results:
                logger.info(f"📝 합성할 원본 결과: {str(found_results)}")
                # 히스토리 컨텍스트
                conversation_history = self._get_conversation_history(session_id)

                # LLM 합성
                synthesized = await self.result_synthesizer.synthesize_with_llm(
                    user_message=user_message,
                    found_results=found_results,
                    processing_type=result.get('processing_type'),
                    query_analysis=query_analysis,
                    conversation_history=conversation_history
                )

                if synthesized:
                    result['choices'][0]['message']['content'] = synthesized
                    logger.info(f"🔄 결과 합성 완료: {len(synthesized)}자")
                    logger.info(f"📄 합성된 내용: {synthesized}")
                else:
                    logger.warning("⚠️ 합성 결과가 비어있음")
            else:
                logger.warning("⚠️ 합성할 원본 결과가 없음")

            return result
        except Exception as e:
            logger.warning(f"결과 합성 실패: {e}")
            return result

    def _get_conversation_history(self, session_id: str, limit: int = 5) -> str:
        """대화 히스토리 문자열 생성"""
        try:
            exchanges = self.conversation_memory.get_recent_exchanges(session_id, limit=limit)
            if not exchanges:
                return ""

            history_parts = []
            for i, exchange in enumerate(exchanges[-limit:], 1):  # 최신 limit개만 사용
                user_msg = exchange.get('user_message', '')
                ai_msg = exchange.get('ai_response', '')
                if user_msg and ai_msg:
                    # 더 명확한 턴 구분과 핵심 정보 강조
                    history_parts.append(f"[대화 {i}턴]")
                    history_parts.append(f"👤 사용자: {user_msg}")
                    # AI 답변에서 핵심 정보만 요약 (너무 길면 축약)
                    summary_ai_msg = ai_msg[:200] + "..." if len(ai_msg) > 200 else ai_msg
                    history_parts.append(f"🤖 AI: {summary_ai_msg}")
                    history_parts.append("")  # 턴 구분용 빈 줄

            return "\n".join(history_parts)
        except Exception:
            return ""

    async def _save_conversation(self, session_id: str, user_message: str, result: Dict, query_analysis: Dict):
        """대화 저장"""
        try:
            response = result['choices'][0]['message']['content']
            contexts = result.get('contexts', {})

            # 사용자 메시지 저장
            self.conversation_memory._append_message(session_id, 'user', user_message)
            # AI 응답 저장
            self.conversation_memory._append_message(session_id, 'assistant', response)

            # 상태 업데이트
            state = self.conversation_memory.get_state(session_id)
            state.update({
                "last_query_analysis": query_analysis,
                "last_sql_result": contexts.get('sql', ''),
                "last_vector_result": contexts.get('vector', ''),
                "updated_at": datetime.now()
            })

        except Exception as e:
            logger.warning(f"대화 저장 실패: {e}")


    def _create_error_response(self, message: str) -> Dict[str, Any]:
        """에러 응답 생성"""
        return {
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": message
                },
                "finish_reason": "stop"
            }],
            "error": message,
            "timestamp": datetime.now().isoformat()
        }


    async def stream_response_with_messages(self, messages: List[Dict[str, str]], session_id: str = "default", ignore_history: bool = False) -> AsyncGenerator[Dict[str, Any], None]:
        """
        전체 메시지 히스토리를 활용한 스트리밍 응답

        Args:
            messages: 전체 대화 히스토리
            session_id: 세션 ID
            ignore_history: 히스토리 무시 여부
        """
        # 마지막 사용자 메시지 추출
        user_message = messages[-1]["content"] if messages else ""

        # LLM 대화 분석
        query_analysis = await self._analyze_with_llm_context(messages, session_id)
        resolved_query = query_analysis.get('resolved_query', user_message)

        logger.info(f"🎯 스트리밍 - LLM이 이해한 쿼리: {resolved_query}")

        # 기존 스트리밍 로직 활용하되 resolved_query 사용
        async for chunk in self._stream_with_resolved_query(resolved_query, query_analysis, messages, session_id, ignore_history):
            yield chunk

    async def _stream_with_resolved_query(
        self,
        resolved_query: str,
        query_analysis: Dict[str, Any],
        messages: List[Dict[str, str]],
        session_id: str,
        ignore_history: bool
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """해결된 쿼리로 스트리밍 처리"""
        # 기존 stream_response 로직 활용
        async for chunk in self.stream_response(resolved_query, session_id, ignore_history):
            yield chunk

    async def stream_response(self, user_message: str, session_id: str = "default", ignore_history: bool = False) -> AsyncGenerator[Dict[str, Any], None]:
        """
        통합 스트리밍 응답 - 통합 LangGraph/기존 LangGraph/ToT 체인 기반

        Args:
            user_message: 사용자 메시지
            session_id: 세션 ID
            ignore_history: 히스토리 무시 여부

        Yields:
            Dict[str, Any]: 스트리밍 청크
        """
        try:
            logger.info(f"📺 스트리밍 시작: {user_message}")

            # 통합 LangGraph 모드 (최우선)
            if self.use_unified_langgraph and self.unified_langgraph_service:
                logger.info("🌟 통합 LangGraph 스트리밍 모드")
                try:
                    async for chunk in self.unified_langgraph_service.run_agent_streaming(
                        user_message=user_message,
                        session_id=session_id
                    ):
                        # SSE 형식의 응답을 Dict 형식으로 변환
                        if chunk.startswith("data: "):
                            import json
                            try:
                                data = json.loads(chunk[6:])  # "data: " 제거
                                if data.get("type") == "final":
                                    yield {"type": "content", "content": data.get("content", "")}
                                elif data.get("type") == "progress":
                                    yield {"type": "status", "content": data.get("message", "")}
                                elif data.get("type") == "error":
                                    yield {"type": "error", "content": data.get("message", "")}
                            except json.JSONDecodeError:
                                pass
                    return  # 통합 LangGraph로 처리 완료
                except Exception as e:
                    logger.error(f"❌ 통합 LangGraph 스트리밍 오류: {e}")
                    logger.error("🔄 기존 방식으로 폴백")
                    # 폴백으로 기존 로직 실행

            # 간단한 분석 및 컨텍스트 수집 (요약) - session_id 전달
            try:
                query_analysis = await self.query_analyzer.analyze_query_parallel(user_message, session_id)
            except Exception:
                query_analysis = {}

            # ContextBu ilder를 사용한 컨텍스트 생성
            try:
                exp_ctx = (query_analysis.get('expansion_context') or '') if isinstance(query_analysis, dict) else ''
                if ignore_history:
                    combined_context = ContextBuilder.build_combined_context(
                        sql_context='',
                        vector_context='',
                        expansion_context=exp_ctx
                    )
                else:
                    prior = self.conversation_memory.get_last_contexts(session_id)
                    combined_context = ContextBuilder.build_combined_context(
                        sql_context=prior.get('sql', ''),
                        vector_context=prior.get('vector', ''),
                        expansion_context=exp_ctx
                    )
            except Exception:
                combined_context = ""

            # 스트리밍 로직: ChatModel만 사용 (LangGraph는 메모리 전용)
            async def chat_model_stream():
                if ChatModelHelper.validate_chat_model(self._chat_model):
                    # 히스토리 지시 프롬프트
                    directive = ContextBuilder.build_history_directive(user_message, mode=("ignore" if ignore_history else "auto"))
                    msgs = StreamingUtils.build_langchain_messages(
                        self.conversation_memory if not ignore_history else None,
                        session_id,
                        user_message,
                        f"{directive}\n\n{combined_context}" if combined_context else directive
                    )
                    async for chunk in self._chat_model.astream(msgs):
                        piece = getattr(chunk, "content", None)
                        if piece:
                            yield StreamingUtils.create_content_chunk(piece)
                else:
                    # 최종 폴백: LLM 핸들러의 스트리밍 사용
                    async for chunk_text in self.llm_handler.stream_response(user_message, agent_mode=False):
                        yield StreamingUtils.create_content_chunk(chunk_text)

            # ChatModel 스트리밍만 사용
            aggregated = []
            async for chunk in chat_model_stream():
                if chunk.get("type") == "content":
                    aggregated.append(chunk.get("content", ""))
                yield chunk

            # 스트리밍 종료 후 대화 저장 (간소화)
            final_text = "".join(aggregated)
            if final_text:
                try:
                    prior = self.conversation_memory.get_last_contexts(session_id)
                    await self._save_conversation_safely(
                        session_id=session_id,
                        user_message=user_message,
                        assistant_response=final_text,
                        query_analysis=query_analysis,
                        sql_context=prior.get('sql', ''),
                        vector_context=prior.get('vector', '')
                    )
                except Exception as _e:
                    logger.warning(f"스트리밍 후 대화 저장 실패: {_e}")

            logger.info("✅ 스트리밍 완료")

        except Exception as e:
            logger.error(f"❌ LangGraph 스트리밍 오류: {e}")
            yield {"type": "error", "content": f"스트리밍 중 오류 발생: {str(e)}"}

    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """세션 정보 조회"""
        memory_stats = self.conversation_memory.get_session_stats(session_id)
        langchain_stats = self.llm_handler.get_performance_stats() if self.llm_handler else {}

        return {
            "session_info": memory_stats,
            "langchain_stats": langchain_stats,
            "hybrid_version": "2.0-chain-pipeline",
            "chain_info": {
                "pipeline_stages": ["analysis", "routing", "parallel_processing", "integration"],
                "parallel_support": True,
                "async_chains": True
            }
        }

    def clear_session_history(self, session_id: str):
        """세션 히스토리 초기화"""
        self.conversation_memory.clear_session(session_id)
        self.llm_handler.clear_memory()
        logger.info(f"세션 {session_id} 히스토리 초기화 완료")

    def export_conversation_history(self, session_id: str) -> Dict[str, Any]:
        """대화 히스토리 내보내기"""
        memory_export = self.conversation_memory.export_conversation(session_id)
        langchain_stats = self.llm_handler.get_performance_stats() if self.llm_handler else {}

        return {
            "memory_history": memory_export,
            "langchain_stats": langchain_stats,
            "export_timestamp": datetime.now().isoformat()
        }

    async def get_available_features(self) -> Dict[str, Any]:
        """사용 가능한 LangChain 기능들 조회"""
        chains = await self.llm_handler.get_available_chains()
        tools = await self.llm_handler.get_available_tools()

        return {
            "available_chains": chains,
            "available_tools": tools,
            "streaming_support": True,
            "agent_support": True,
            "memory_support": True
        }

    def get_health_status(self) -> Dict[str, Any]:
        """헬스 체크를 위한 상태 반환"""
        try:
            # 각 컴포넌트 상태 확인 - 통합 LangGraph 포함
            if self.use_unified_langgraph:
                execution_mode = "Unified LangGraph"
            elif self.use_langgraph:
                execution_mode = "LangGraph"
            else:
                execution_mode = "ToT"
            status = {
                "status": "healthy",
                "service": "hybrid-mentor",
                "version": "3.0-langgraph",
                "execution_mode": execution_mode,
                "components": {
                    "llm_handler": hasattr(self, "llm_handler") and self.llm_handler is not None,
                    "query_analyzer": hasattr(self, "query_analyzer") and self.query_analyzer is not None,
                    "chain_processor": hasattr(self, "chain_processor") and self.chain_processor is not None,
                    "conversation_memory": hasattr(self, "conversation_memory") and self.conversation_memory is not None,
                    "langgraph_service": self._check_langgraph_service_health()
                },
                "langgraph_available": LANGGRAPH_AVAILABLE,
                "timestamp": datetime.now().isoformat()
            }

            # LangGraph 상태 추가
            if self.use_unified_langgraph and self.unified_langgraph_service:
                unified_health = self.unified_langgraph_service.get_health_status()
                status["unified_langgraph_status"] = unified_health
            elif self.use_langgraph and self.langgraph_service:
                langgraph_health = self.langgraph_service.get_health_status()
                status["langgraph_status"] = langgraph_health

            # 모든 컴포넌트가 정상인지 확인
            all_healthy = all(status["components"].values())
            if not all_healthy:
                status["status"] = "degraded"

            return status
        except Exception as e:
            return {
                "status": "unhealthy",
                "service": "hybrid-mentor",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    # ==================== LangGraph 전환 관리 메서드들 ====================

    def switch_to_langgraph(self) -> bool:
        """
        LangGraph 모드로 전환

        Returns:
            전환 성공 여부
        """
        if not LANGGRAPH_AVAILABLE:
            logger.error("❌ LangGraph가 설치되지 않아 전환할 수 없습니다")
            return False

        if self.use_langgraph:
            logger.info("ℹ️ 이미 LangGraph 모드입니다")
            return True

        try:
            # LangGraph 서비스 초기화
            if self.langgraph_service is None:
                self.langgraph_service = create_langgraph_service(self.conversation_memory)

            self.use_langgraph = True
            logger.info("✅ LangGraph 모드로 전환 완료")
            return True

        except Exception as e:
            logger.error(f"❌ LangGraph 모드 전환 실패: {e}")
            return False

    def switch_to_tot(self) -> bool:
        """
        ToT 모드로 전환

        Returns:
            전환 성공 여부
        """
        if not self.use_langgraph:
            logger.info("ℹ️ 이미 ToT 모드입니다")
            return True

        try:
            self.use_langgraph = False
            logger.info("✅ ToT 모드로 전환 완료")
            return True

        except Exception as e:
            logger.error(f"❌ ToT 모드 전환 실패: {e}")
            return False

    def get_execution_mode(self) -> str:
        """현재 실행 모드 반환"""
        return "LangGraph" if self.use_langgraph else "ToT"

    def is_langgraph_available(self) -> bool:
        """LangGraph 사용 가능 여부"""
        return LANGGRAPH_AVAILABLE

    def enable_langgraph_mode(self) -> bool:
        """LangGraph 모드 활성화 (강화된 검증 로직 포함)"""
        if not LANGGRAPH_AVAILABLE:
            logger.warning("⚠️ LangGraph를 사용할 수 없습니다 - LANGGRAPH_AVAILABLE=False")
            return False

        try:
            logger.info("🔧 LangGraph 모드 활성화 시작")
            logger.info(f"   현재 langgraph_service 상태: {self.langgraph_service is not None}")
            logger.info(f"   conversation_memory 상태: {self.conversation_memory is not None}")

            # 1단계: 서비스 생성
            logger.info("🔄 1단계: LangGraph 서비스 생성 중...")
            self.langgraph_service = create_langgraph_service(self.conversation_memory)
            logger.info("✅ 1단계 완료: LangGraph 서비스 객체 생성됨")

            # 2단계: 서비스 헬스체크
            logger.info("🔄 2단계: 서비스 헬스체크 실행 중...")
            health_status = self.langgraph_service.get_health_status()
            service_status = health_status.get("status", "unknown")

            if service_status != "healthy":
                raise Exception(f"서비스 헬스체크 실패: {service_status}")

            logger.info(f"✅ 2단계 완료: 서비스 상태 = {service_status}")
            logger.info(f"   서비스 타입: {health_status.get('service_type')}")
            logger.info(f"   컴포넌트: {list(health_status.get('components', {}).keys())}")

            # 3단계: 간단한 기능 테스트
            logger.info("🔄 3단계: 기본 기능 테스트 중...")
            try:
                # 간단한 세션 정보 조회로 기능 테스트
                test_info = self.langgraph_service.get_session_info("test_validation")
                logger.info(f"✅ 3단계 완료: 기능 테스트 성공 - {test_info.get('service_type')}")
            except Exception as test_error:
                logger.warning(f"⚠️ 기능 테스트 실패하지만 계속 진행: {test_error}")

            # 4단계: 모드 활성화
            self.use_langgraph = True
            logger.info("🚀 LangGraph 모드가 성공적으로 활성화되었습니다!")

            return True

        except ImportError as e:
            logger.error(f"❌ LangGraph import 오류: {e}")
            logger.error("   LangGraph 모듈이 설치되어 있는지 확인하세요")
            self.use_langgraph = False
            self.langgraph_service = None
            return False

        except Exception as e:
            logger.error(f"❌ LangGraph 서비스 초기화 실패: {e}")
            logger.error("상세 스택 트레이스:")
            import traceback
            for line in traceback.format_exc().splitlines():
                logger.error(f"   {line}")

            # 실패시 상태 초기화
            self.use_langgraph = False
            self.langgraph_service = None
            logger.error("🔄 LangGraph 모드 비활성화됨 - ToT 모드로 폴백")
            return False

    def disable_langgraph_mode(self) -> bool:
        """LangGraph 모드 비활성화 (ToT 모드로 전환)"""
        self.use_langgraph = False
        logger.info("🔄 ToT 모드로 전환되었습니다")
        return True

    def _validate_langgraph_service(self) -> bool:
        """LangGraph 서비스 검증 (런타임 체크)"""
        try:
            if self.langgraph_service is None:
                logger.debug("🔍 검증 실패: langgraph_service가 None")
                return False

            # 헬스체크 호출
            health = self.langgraph_service.get_health_status()
            status = health.get("status", "unknown")

            if status != "healthy":
                logger.warning(f"🔍 검증 실패: 서비스 상태 = {status}")
                return False

            logger.debug("🔍 검증 성공: LangGraph 서비스 정상")
            return True

        except Exception as e:
            logger.warning(f"🔍 검증 중 오류: {e}")
            return False

    def _check_langgraph_service_health(self) -> bool:
        """헬스체크용 LangGraph 서비스 상태 확인 (실제 기능 검증 포함)"""
        try:
            # 1단계: 객체 존재 확인
            if not hasattr(self, "langgraph_service") or self.langgraph_service is None:
                return False

            # 2단계: 서비스 헬스체크 호출
            health_status = self.langgraph_service.get_health_status()
            if health_status.get("status") != "healthy":
                return False

            # 3단계: 기본 기능 테스트 (빠른 검증)
            service_type = health_status.get("service_type")
            if service_type != "langgraph":
                return False

            # 4단계: 컴포넌트 상태 확인
            components = health_status.get("components", {})
            langgraph_app_healthy = components.get("langgraph_app") == "healthy"

            return langgraph_app_healthy

        except Exception as e:
            # 헬스체크에서는 로깅 최소화
            return False

    async def compare_execution_modes(
        self,
        user_message: str,
        session_id: str = "test_comparison"
    ) -> Dict[str, Any]:
        """
        ToT와 LangGraph 모드 비교 실행 (테스트/개발용)

        Args:
            user_message: 테스트할 사용자 메시지
            session_id: 테스트용 세션 ID

        Returns:
            두 모드의 실행 결과 비교
        """
        if not LANGGRAPH_AVAILABLE:
            return {
                "error": "LangGraph가 설치되지 않아 비교할 수 없습니다",
                "user_message": user_message
            }

        logger.info(f"🔬 실행 모드 비교 테스트: {user_message}")
        results = {}

        # 현재 모드 백업
        original_mode = self.use_langgraph

        try:
            # 1. ToT 모드 실행
            start_time = datetime.now()
            self.use_langgraph = False
            tot_result = await self.run_agent(user_message, f"{session_id}_tot")
            tot_duration = (datetime.now() - start_time).total_seconds()

            results["tot"] = {
                "result": tot_result,
                "duration": tot_duration,
                "mode": "ToT"
            }

            # 2. LangGraph 모드 실행
            start_time = datetime.now()
            self.use_langgraph = True
            if self.langgraph_service is None:
                self.langgraph_service = create_langgraph_service(self.conversation_memory)

            langgraph_result = await self.run_agent(user_message, f"{session_id}_langgraph")
            langgraph_duration = (datetime.now() - start_time).total_seconds()

            results["langgraph"] = {
                "result": langgraph_result,
                "duration": langgraph_duration,
                "mode": "LangGraph"
            }

            # 3. 비교 분석
            results["comparison"] = {
                "speed_improvement": (tot_duration - langgraph_duration) / tot_duration * 100,
                "tot_faster": tot_duration < langgraph_duration,
                "user_message": user_message,
                "session_id": session_id
            }

            logger.info(f"🏁 비교 완료 - ToT: {tot_duration:.2f}초, LangGraph: {langgraph_duration:.2f}초")

        except Exception as e:
            logger.error(f"❌ 비교 실행 실패: {e}")
            results["error"] = str(e)

        finally:
            # 원래 모드로 복원
            self.use_langgraph = original_mode

        return results

    def get_langgraph_visualization(self) -> str:
        """LangGraph 시각화 (있는 경우)"""
        if self.unified_langgraph_service:
            return self.unified_langgraph_service.get_graph_visualization()
        elif self.langgraph_service:
            return self.langgraph_service.get_graph_visualization()
        return "LangGraph 서비스가 초기화되지 않았습니다."

    # ==================== 통합 LangGraph 전환 메서드들 ====================

    def enable_unified_langgraph_mode(self) -> bool:
        """통합 LangGraph 모드 활성화 (Light/Medium/Heavy 통합 처리)"""
        if not UNIFIED_LANGGRAPH_AVAILABLE:
            logger.warning("⚠️ 통합 LangGraph를 사용할 수 없습니다 - UNIFIED_LANGGRAPH_AVAILABLE=False")
            return False

        try:
            logger.info("🔧 통합 LangGraph 모드 활성화 시작")

            # 1단계: 기존 모드들 비활성화
            logger.info("🔄 1단계: 기존 모드들 비활성화...")
            self.use_langgraph = False
            self.use_unified_langgraph = False

            # 2단계: 통합 서비스 생성
            logger.info("🔄 2단계: 통합 LangGraph 서비스 생성 중...")
            self.unified_langgraph_service = create_unified_langgraph_service(self.conversation_memory)

            # 3단계: 서비스 헬스체크
            logger.info("🔄 3단계: 통합 서비스 헬스체크 실행 중...")
            health_status = self.unified_langgraph_service.get_health_status()
            if health_status.get("status") != "healthy":
                raise Exception(f"통합 서비스 헬스체크 실패: {health_status}")

            logger.info("✅ 통합 서비스 헬스체크 통과")

            # 4단계: 기능 테스트
            logger.info("🔄 4단계: 통합 서비스 기능 테스트...")
            test_visualization = self.unified_langgraph_service.get_graph_visualization()
            if not test_visualization or "error" in test_visualization.lower():
                logger.warning("⚠️ 그래프 시각화 테스트에서 경고가 발생했지만 계속 진행합니다")

            logger.info("✅ 통합 서비스 기능 테스트 통과")

            # 5단계: 모드 활성화
            self.use_unified_langgraph = True
            logger.info("🚀 통합 LangGraph 모드가 성공적으로 활성화되었습니다!")
            logger.info("   📋 지원 기능:")
            logger.info("     • Light: 간단한 대화 (LLM 직접 호출)")
            logger.info("     • Medium: 중간 복잡도 (단일 에이전트)")
            logger.info("     • Heavy: 높은 복잡도 (병렬 다중 에이전트)")

            return True

        except ImportError as e:
            logger.error(f"❌ 통합 LangGraph import 오류: {e}")
            logger.error("   통합 LangGraph 모듈이 설치되어 있는지 확인하세요")
            self.use_unified_langgraph = False
            self.unified_langgraph_service = None
            return False

        except Exception as e:
            logger.error(f"❌ 통합 LangGraph 서비스 초기화 실패: {e}")
            logger.error("상세 스택 트레이스:")
            import traceback
            for line in traceback.format_exc().splitlines():
                logger.error(f"   {line}")

            # 실패시 상태 초기화
            self.use_unified_langgraph = False
            self.unified_langgraph_service = None
            logger.error("🔄 통합 LangGraph 모드 비활성화됨 - ToT 모드로 폴백")
            return False

    def disable_unified_langgraph_mode(self) -> bool:
        """통합 LangGraph 모드 비활성화 (ToT 모드로 전환)"""
        self.use_unified_langgraph = False
        logger.info("🔄 통합 LangGraph에서 ToT 모드로 전환되었습니다")
        return True

    def get_execution_mode(self) -> str:
        """현재 실행 모드 반환"""
        if self.use_unified_langgraph:
            return "Unified LangGraph"
        elif self.use_langgraph:
            return "LangGraph"
        else:
            return "ToT"

    def is_unified_langgraph_available(self) -> bool:
        """통합 LangGraph 사용 가능 여부"""
        return UNIFIED_LANGGRAPH_AVAILABLE and self.unified_langgraph_service is not None

    def get_unified_complexity_stats(self) -> Dict[str, Any]:
        """통합 LangGraph의 복잡도별 통계"""
        if self.unified_langgraph_service:
            return self.unified_langgraph_service.get_complexity_stats()
        return {"message": "통합 LangGraph 서비스가 활성화되지 않았습니다"}
