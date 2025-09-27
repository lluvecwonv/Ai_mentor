"""
진짜 LangGraph 형식 대화 상태 관리 (ConversationMemory)
세션별 대화 히스토리와 컨텍스트(SQL/벡터), 캐시, 통계를 관리합니다.

LangGraph StateGraph 기반:
- MessagesState: LangGraph 표준 상태 정의
- StateGraph: 노드와 엣지를 통한 대화 플로우
- Checkpointer: 세션별 상태 저장/복원
"""

import logging
from typing import Dict, List, Any, Optional, TypedDict
try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated
from datetime import datetime
import re
import json
try:
    # LangGraph 필수 imports
    from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
    from langchain_core.chat_history import BaseChatMessageHistory
    from langgraph.graph import StateGraph, MessagesState, START, END
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.graph.message import add_messages
    LANGGRAPH_AVAILABLE = True
except Exception:  # pragma: no cover
    # 폴백 정의
    BaseMessage = Any
    def add_messages(left: List[Any], right: List[Any]) -> List[Any]:
        """폴백 add_messages 함수"""
        return left + right

    class HumanMessage:
        def __init__(self, content: str):
            self.content = content
    class AIMessage:
        def __init__(self, content: str):
            self.content = content
    class SystemMessage:
        def __init__(self, content: str):
            self.content = content
    class BaseChatMessageHistory:
        @property
        def messages(self):
            return []
        def add_message(self, message: Any) -> None:
            pass
        def clear(self) -> None:
            pass
    class MessagesState(TypedDict):
        messages: Annotated[List[BaseMessage], add_messages]
    LANGGRAPH_AVAILABLE = False

# LangChain Memory backends (optional)
try:  # pragma: no cover
    from langchain_community.chat_message_histories import (
        SQLChatMessageHistory,
        ChatMessageHistory as LCInMemoryHistory,
    )
    LANGCHAIN_MEMORY_AVAILABLE = True
except Exception:  # pragma: no cover
    SQLChatMessageHistory = None  # type: ignore
    LCInMemoryHistory = None  # type: ignore
    LANGCHAIN_MEMORY_AVAILABLE = False

logger = logging.getLogger(__name__)

# LangGraph 확장 상태 정의
class AIMentorState(MessagesState):
    """AI Mentor용 확장 상태 - LangGraph MessagesState 기반"""
    session_id: str
    current_topic: Optional[str]
    last_sql_result: str
    last_vector_result: str
    query_analysis: Optional[Dict[str, Any]]
    search_results: Optional[List[Dict]]
    entity_cache: Dict[str, Dict[str, Any]]
    metadata: Dict[str, Any]

class ConversationState(TypedDict):
    """대화 상태 타입 정의"""
    session_id: str
    conversation_history: List[Dict[str, Any]]  # 전체 대화 히스토리
    last_search_results: Optional[List[Dict]]   # 최근 검색 결과
    current_topic: Optional[str]                # 현재 주제
    last_query_analysis: Optional[Dict]         # 최근 쿼리 분석 결과
    metadata: Dict[str, Any]                    # 추가 메타데이터
    created_at: datetime
    updated_at: datetime
    last_sql_result: str                        # 최근 SQL 결과(원문)
    last_vector_result: str                     # 최근 벡터 검색 결과(원문)
    entity_cache: Dict[str, Dict[str, Dict[str, Any]]]  # {'professors':{key:{data,updated_at}}, 'courses':{...}, 'departments':{...}}

class ConversationMemory:
    """진짜 LangGraph 기반 대화 메모리 관리 클래스"""

    def __init__(
        self,
        max_history_length: int = 20,
        llm_handler: Any = None,
        lc_memory_backend: str = "memory",  # "memory" | "sqlite"
        lc_sqlite_path: Optional[str] = None,
    ):
        self.sessions: Dict[str, ConversationState] = {}
        self.max_history_length = max_history_length
        # 외부 LLM 핸들러 주입(선택)
        self.llm_handler = llm_handler

        # LangChain Memory 설정
        self.lc_memory_backend = lc_memory_backend
        self.lc_sqlite_path = lc_sqlite_path or "./conversation_memory.sqlite"
        self._lc_histories: Dict[str, BaseChatMessageHistory] = {}

        # LangGraph StateGraph 초기화
        if LANGGRAPH_AVAILABLE:
            self._init_langgraph()
        else:
            self.graph = None
            self.checkpointer = None

        logger.debug("ConversationMemory 초기화 완료 (LangGraph 지원)")

    # ===== LangChain Memory helpers =====
    def _get_lc_history(self, session_id: str) -> Optional[BaseChatMessageHistory]:
        """세션별 LangChain ChatMessageHistory를 반환 (백엔드에 따라 생성/캐시)."""
        if not LANGCHAIN_MEMORY_AVAILABLE:
            return None

        if session_id in self._lc_histories:
            return self._lc_histories[session_id]

        history: Optional[BaseChatMessageHistory] = None
        try:
            if self.lc_memory_backend == "sqlite" and SQLChatMessageHistory is not None:
                conn = f"sqlite:///{self.lc_sqlite_path}"
                history = SQLChatMessageHistory(session_id=session_id, connection_string=conn)
            elif LCInMemoryHistory is not None:
                history = LCInMemoryHistory()
        except Exception:
            history = None

        if history is not None:
            self._lc_histories[session_id] = history
        return history

    def _init_langgraph(self):
        """LangGraph StateGraph 초기화"""
        try:
            logger.info("LangGraph 초기화 시작...")

            # StateGraph 생성
            self.checkpointer = MemorySaver()
            logger.debug("MemorySaver 생성 완료")

            graph = StateGraph(AIMentorState)
            logger.debug("StateGraph 생성 완료")

            # 노드: 최소 구성(단일 응답 생성 노드)
            graph.add_node("generate_response", self._generate_response_node)
            logger.debug("LangGraph 노드 추가 완료 (generate_response)")

            # 엣지: START → generate_response → END
            graph.add_edge(START, "generate_response")
            graph.add_edge("generate_response", END)
            logger.debug("LangGraph 엣지 추가 완료 (START→generate_response→END)")

            # 그래프 컴파일
            self.graph = graph.compile(checkpointer=self.checkpointer)
            logger.info("✅ LangGraph StateGraph 컴파일 완료!")

        except Exception as e:
            logger.error(f"❌ LangGraph 초기화 실패, 기본 모드로 폴백: {e}")
            logger.error(f"오류 상세: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"스택 트레이스: {traceback.format_exc()}")
            self.graph = None
            self.checkpointer = None

    # LangGraph 노드 함수들 (최소 구성)
    def _build_system_context(self, state: AIMentorState) -> str:
        """분석/캐시 컨텍스트를 하나의 시스템 컨텍스트로 합성"""
        try:
            from utils.context_builder import ContextBuilder
        except Exception:
            return ""

        qa = state.get("query_analysis") or {}
        expansion_ctx = qa.get("expansion_context", "") if isinstance(qa, dict) else ""
        return ContextBuilder.build_combined_context(
            sql_context=state.get("last_sql_result", ""),
            vector_context=state.get("last_vector_result", ""),
            expansion_context=expansion_ctx
        )

    async def _judge_and_refine(self, user_text: str, draft_answer: str) -> str:
        """LLM 기반 최종 검수/정제. 실패 시 draft 반환"""
        if not self.llm_handler:
            return draft_answer

        prompt = f"""
            너는 대학 AI 멘토의 최종 검수 에이전트이다. 아래 질의와 임시 답변을 검토해라.

            검토 기준:
            - 답변이 질의 의도와 일치하는지 판단
            - 사실과 무관한 일반적인 잡설이나 환각 부분 적발
            - 불필요한 장황함을 줄이고 핵심만 남겨 자연스럽게 한국어로 재정리
            - 강의/과목 추천이면 번호 목록과 학과/요약을 간결히 포함
            - 전북대학교 맥락에 맞는 답변으로 정제

            입력 질의: "{user_text}"

            임시 답변:
            {draft_answer}

            반드시 JSON 형식으로만 출력:
            {{
            "is_aligned": true/false,
            "quality_score": 0.0~1.0,
            "issues": ["발견된 문제점들"],
            "final_answer": "한국어로 정리된 최종 답변",
            "notes": "간단 메모"
            }}
            """

        try:
            raw = await self.llm_handler.run_chain("basic", prompt)
            # JSON 블록 추출
            m = re.search(r"\{[\s\S]*\}", str(raw))
            if not m:
                return draft_answer
            data = json.loads(m.group())
            final = data.get("final_answer") or draft_answer
            return str(final)
        except Exception:
            return draft_answer

    async def _generate_response_node(self, state: AIMentorState) -> AIMentorState:
        """응답 생성 노드 - 주입된 LLM 핸들러로 실제 응답 생성 + ResponseJudge 품질 검증"""
        logger.debug("LangGraph: 응답 생성 노드 실행")
        last_message = state["messages"][-1] if state["messages"] else None
        if not last_message:
            logger.warning("LangGraph: 메시지가 없어 응답 생성 불가")
            return state

        user_text = str(getattr(last_message, 'content', ''))
        logger.info(f"🤖 LangGraph 응답 생성 시작: '{user_text[:50]}...'")

        # LLM 핸들러가 없으면 최소 폴백
        if self.llm_handler is None:
            logger.warning("LangGraph: LLM 핸들러 없음, 기본 응답 생성")
            response_content = f"AI 멘토: {user_text}에 대해 답변드리겠습니다."
            state["messages"].append(AIMessage(content=response_content))
            return state

        try:
            # 시스템 컨텍스트 구성
            system_ctx = self._build_system_context(state)
            logger.debug(f"📋 시스템 컨텍스트 구성 완료: {len(system_ctx)}자")

            # LLM으로 초안 응답 생성
            if state.get("last_sql_result") or state.get("last_vector_result"):
                logger.info("🔍 컨텍스트 기반 응답 생성 (SQL/Vector 결과 포함)")
                draft = await self.llm_handler.run_chain("context_only", user_text, context=system_ctx)
            else:
                logger.info("💭 일반 컨텍스트 응답 생성")
                draft = await self.llm_handler.run_chain("context", user_text, context=system_ctx)

            logger.info(f"✅ LLM 초안 생성 완료: {len(str(draft))}자")

            # ResponseJudge로 품질 검증 및 정제
            logger.info("🔍 ResponseJudge 품질 검증 시작")
            final_text = await self._judge_and_refine(user_text, str(draft))

            if final_text != str(draft):
                logger.info("✨ ResponseJudge가 응답을 개선했습니다")
            else:
                logger.info("✅ ResponseJudge 검증 통과 (수정 없음)")

            state["messages"].append(AIMessage(content=str(final_text)))
            logger.info(f"🎯 LangGraph 최종 응답 완료: {len(final_text)}자")
            return state

        except Exception as e:
            logger.error(f"❌ LangGraph 응답 생성 실패: {e}")
            import traceback
            logger.error(f"스택 트레이스: {traceback.format_exc()}")

            # 폴백 응답
            response_content = f"AI 멘토: {user_text}에 대해 답변드리겠습니다."
            state["messages"].append(AIMessage(content=response_content))
            return state
    
    def get_state(self, session_id: str) -> ConversationState:
        """세션 상태 조회"""
        if session_id not in self.sessions:
            self.sessions[session_id] = self._create_new_state(session_id)
        
        return self.sessions[session_id]
    
    def _create_new_state(self, session_id: str) -> ConversationState:
        """새 세션 상태 생성"""
        now = datetime.now()
        return ConversationState(
            session_id=session_id,
            conversation_history=[],
            last_search_results=None,
            current_topic=None,
            last_query_analysis=None,
            metadata={},
            created_at=now,
            updated_at=now,
            last_sql_result="",
            last_vector_result="",
            entity_cache={
                'professors': {},
                'courses': {},
                'departments': {},
                'combos': {}
            }
        )
    
    def add_exchange(self, session_id: str, user_message: str, 
                    assistant_response: str, query_analysis: Dict[str, Any] = None,
                    search_results: List[Dict] = None,
                    sql_context: str = "",
                    vector_context: str = ""):
        """대화 교환 추가"""
        state = self.get_state(session_id)
        
        # 사용자 메시지 추가
        state["conversation_history"].append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        })
        
        # 어시스턴트 응답 추가
        state["conversation_history"].append({
            "role": "assistant", 
            "content": assistant_response,
            "timestamp": datetime.now().isoformat()
        })
        
        # LangChain Memory에도 기록
        lc_hist = self._get_lc_history(session_id)
        try:
            if lc_hist is not None:
                from langchain_core.messages import HumanMessage, AIMessage
                lc_hist.add_message(HumanMessage(content=user_message))
                lc_hist.add_message(AIMessage(content=assistant_response))
        except Exception:
            pass

        # 히스토리 길이 제한
        if len(state["conversation_history"]) > self.max_history_length * 2:  # user + assistant 쌍
            state["conversation_history"] = state["conversation_history"][-self.max_history_length * 2:]
        
        # 메타데이터 업데이트
        if query_analysis:
            state["last_query_analysis"] = query_analysis
            
            # 현재 주제 업데이트
            category = query_analysis.get('category', '')
            owner_hint = query_analysis.get('owner_hint', '')
            if owner_hint:
                state["current_topic"] = f"{category}_{owner_hint}"
        
        # 검색 결과 업데이트
        if search_results:
            state["last_search_results"] = search_results

        # 컨텍스트 캐시 업데이트
        if sql_context:
            state["last_sql_result"] = sql_context
        if vector_context:
            state["last_vector_result"] = vector_context
        
        state["updated_at"] = datetime.now()
        
        logger.info(f"세션 {session_id}에 대화 교환 추가: {len(state['conversation_history'])}개 메시지")

    # 내부용: 단일 메시지 추가 (역호환)
    def update_full_messages(self, session_id: str, messages: List[Dict[str, str]]) -> None:
        """
        전체 메시지 히스토리 업데이트

        Args:
            session_id: 세션 ID
            messages: 전체 대화 히스토리 [{"role": "user/assistant", "content": "..."}]
        """
        if session_id not in self.sessions:
            self.sessions[session_id] = self._create_new_state(session_id)

        session = self.sessions[session_id]

        # 대화 히스토리를 LangGraph 메시지 형식으로 변환
        langchain_messages = []
        for msg in messages:
            if msg["role"] == "user":
                langchain_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                langchain_messages.append(AIMessage(content=msg["content"]))
            elif msg["role"] == "system":
                langchain_messages.append(SystemMessage(content=msg["content"]))

        # 세션 상태 업데이트
        session['conversation_history'] = messages[-self.max_history_length:]
        session['updated_at'] = datetime.now()

        # LLM을 사용하여 대화에서 핵심 엔티티 추출
        if self.llm_handler:
            self._extract_entities_with_llm(session_id, messages)

        logger.debug(f"📝 세션 {session_id}: {len(messages)} 메시지 업데이트 완료")

    def _extract_entities_with_llm(self, session_id: str, messages: List[Dict[str, str]]) -> None:
        """
        LLM을 사용하여 대화에서 엔티티 추출 및 캐싱
        """
        try:
            # 최근 5개 메시지에서 엔티티 추출
            recent_messages = messages[-5:] if len(messages) > 5 else messages

            extraction_prompt = {
                "role": "system",
                "content": """다음 대화에서 언급된 엔티티를 추출하세요.
                JSON 형식으로 응답:
                {
                    "professors": ["교수명1", "교수명2"],
                    "courses": ["과목명1", "과목명2"],
                    "departments": ["학과명1", "학과명2"]
                }"""
            }

            # 동기 호출이라 asyncio 사용
            import asyncio
            loop = asyncio.new_event_loop()
            entities = loop.run_until_complete(
                self.llm_handler.chat_completion_json([extraction_prompt, *recent_messages])
            )
            loop.close()

            if isinstance(entities, str):
                entities = json.loads(entities)

            # 엔티티 캐시 업데이트
            session = self.sessions[session_id]
            session['entity_cache'].update({
                'professors': {name: {'updated_at': datetime.now()} for name in entities.get('professors', [])},
                'courses': {name: {'updated_at': datetime.now()} for name in entities.get('courses', [])},
                'departments': {name: {'updated_at': datetime.now()} for name in entities.get('departments', [])}
            })

            logger.debug(f"📋 엔티티 추출 완료: {entities}")

        except Exception as e:
            logger.warning(f"엔티티 추출 실패 (무시하고 계속): {e}")

    def _append_message(self, session_id: str, role: str, content: str) -> None:
        state = self.get_state(session_id)
        state["conversation_history"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        # LangChain Memory에도 기록
        lc_hist = self._get_lc_history(session_id)
        if lc_hist is not None:
            try:
                from langchain_core.messages import HumanMessage, AIMessage
                if role == 'user':
                    lc_hist.add_message(HumanMessage(content=content))
                else:
                    lc_hist.add_message(AIMessage(content=content))
            except Exception:
                pass
        # 히스토리 길이 제한
        if len(state["conversation_history"]) > self.max_history_length * 2:
            state["conversation_history"] = state["conversation_history"][ - self.max_history_length * 2 : ]
        state["updated_at"] = datetime.now()
    
    def get_recent_context(self, session_id: str, max_turns: int = 5) -> List[Dict[str, str]]:
        """최근 N턴의 대화 맥락 조회"""
        state = self.get_state(session_id)
        history = state["conversation_history"]

        # 최근 max_turns*2개 메시지 (user+assistant 쌍)
        recent_messages = history[-(max_turns * 2):]
        return recent_messages

    def get_recent_exchanges(self, session_id: str, limit: int = 5) -> List[Dict[str, str]]:
        """최근 대화 교환을 사용자-AI 쌍으로 반환"""
        state = self.get_state(session_id)
        history = state["conversation_history"]

        if not history:
            return []

        exchanges = []
        i = 0
        while i < len(history) - 1 and len(exchanges) < limit:
            # 사용자 메시지와 다음 AI 메시지를 찾기
            if (history[i].get("role") == "user" and
                i + 1 < len(history) and
                history[i + 1].get("role") == "assistant"):

                exchange = {
                    "user_message": history[i].get("content", ""),
                    "ai_response": history[i + 1].get("content", ""),
                    "timestamp": history[i].get("timestamp", "")
                }
                exchanges.append(exchange)
                i += 2  # 다음 사용자 메시지로 이동
            else:
                i += 1

        return exchanges[-limit:] if exchanges else []

    # ===== LangGraph/LLM 호환 메시지 헬퍼 =====
    def get_chat_messages(self, session_id: str, max_turns: int = 10) -> List[BaseMessage]:
        """세션 히스토리를 LangChain BaseMessage 리스트로 변환해서 반환

        Args:
            session_id: 세션 ID
            max_turns: 최근 몇 턴(user+assistant 쌍 기준)을 사용할지
        Returns:
            List[BaseMessage]: [HumanMessage/AIMessage ...]
        """
        # 1) LangChain Memory에서 시도
        lc_hist = self._get_lc_history(session_id)
        if lc_hist is not None:
            try:
                msgs = list(lc_hist.messages)
                if max_turns and max_turns > 0:
                    return msgs[-(max_turns * 2):]
                return msgs
            except Exception:
                pass

        # 2) 폴백: 내부 세션 저장소에서 변환
        recent = self.get_recent_context(session_id, max_turns=max_turns)
        messages: List[BaseMessage] = []
        for msg in recent:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            else:
                messages.append(AIMessage(content=content))
        return messages

    def append_chat_turn(self, session_id: str, user_text: str, ai_text: str) -> None:
        """(선택 사용) 한 턴의 사용자/AI 메시지를 히스토리에 추가"""
        self.add_exchange(
            session_id=session_id,
            user_message=user_text,
            assistant_response=ai_text,
            query_analysis=None,
            search_results=None,
            sql_context=self.get_last_contexts(session_id).get("sql", ""),
            vector_context=self.get_last_contexts(session_id).get("vector", "")
        )

    # LangChain RunnableWithMessageHistory 호환 어댑터
    class ConversationMessageHistory(BaseChatMessageHistory):  # type: ignore
        def __init__(self, memory: 'ConversationMemory', session_id: str, max_turns: int = 50):
            self._m = memory
            self._sid = session_id
            self._max = max_turns

        @property
        def messages(self) -> List[BaseMessage]:
            lc = self._m._get_lc_history(self._sid)
            if lc is not None:
                try:
                    msgs = list(lc.messages)
                    return msgs[-(self._max * 2):]
                except Exception:
                    pass
            return self._m.get_chat_messages(self._sid, max_turns=self._max)

        def add_message(self, message: BaseMessage) -> None:  # type: ignore[override]
            try:
                content = getattr(message, 'content', '')
                role = getattr(message, 'type', None) or getattr(message, 'role', '')

                # LangChain Memory에도 기록
                lc = self._m._get_lc_history(self._sid)
                if lc is not None:
                    from langchain_core.messages import HumanMessage, AIMessage
                    if role in ('human', 'user'):
                        lc.add_message(HumanMessage(content=content))
                    else:
                        lc.add_message(AIMessage(content=content))

                # 내부 세션에도 기록
                if role in ('human', 'user'):
                    self._m._append_message(self._sid, 'user', content)
                else:
                    self._m._append_message(self._sid, 'assistant', content)
            except Exception:
                # 안전하게 무시
                pass

        def add_messages(self, messages: List[BaseMessage]) -> None:
            """여러 메시지를 한 번에 추가 (LangChain 새 버전 호환성)"""
            try:
                for message in messages:
                    self.add_message(message)
            except Exception:
                # 안전하게 무시
                pass

        def clear(self) -> None:  # type: ignore[override]
            # LangChain 메모리 초기화
            lc = self._m._get_lc_history(self._sid)
            if lc is not None:
                try:
                    lc.clear()
                except Exception:
                    pass
            # 내부 세션 초기화
            self._m.clear_session(self._sid)

    def get_history_adapter(self, session_id: str, max_turns: int = 50) -> 'ConversationMessageHistory':
        return ConversationMemory.ConversationMessageHistory(self, session_id, max_turns=max_turns)
    
    def get_contextual_prompt(self, session_id: str, current_query: str) -> str:
        """맥락을 포함한 프롬프트 생성 (ContextBuilder 사용)"""
        from utils.context_builder import ContextBuilder

        state = self.get_state(session_id)
        return ContextBuilder.build_contextual_prompt(
            conversation_history=state["conversation_history"],
            search_results=state["last_search_results"],
            current_topic=state["current_topic"],
            current_query=current_query,
            max_turns=3
        )
    
    def clear_session(self, session_id: str):
        """세션 초기화"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"세션 {session_id} 초기화 완료")
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """세션 통계 조회"""
        state = self.get_state(session_id)
        
        return {
            "session_id": session_id,
            "total_messages": len(state["conversation_history"]),
            "current_topic": state["current_topic"],
            "has_search_results": bool(state["last_search_results"]),
            "created_at": state["created_at"].isoformat() if state["created_at"] else None,
            "updated_at": state["updated_at"].isoformat() if state["updated_at"] else None,
            "has_last_sql": bool(state.get("last_sql_result")),
            "has_last_vector": bool(state.get("last_vector_result")),
        }

    def get_last_contexts(self, session_id: str) -> Dict[str, str]:
        state = self.get_state(session_id)
        return {
            "sql": state.get("last_sql_result", ""),
            "vector": state.get("last_vector_result", "")
        }

    def get_cache_summary(self, session_id: str) -> Dict[str, Any]:
        """엔티티 캐시 요약 반환(그대로 반환; 필요시 추후 요약/슬라이스)"""
        state = self.get_state(session_id)
        return state.get("entity_cache", {"professors": {}, "courses": {}, "departments": {}})

    # ===== LangGraph 진짜 사용 메서드들 =====
    async def process_with_langgraph(self, session_id: str, user_message: str, query_analysis: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """LangGraph StateGraph를 사용한 메시지 처리

        Returns:
            str | None: 생성된 응답 텍스트(성공 시) 또는 None(실패/미생성)
        """
        if not self.graph:
            logger.warning("LangGraph 미사용, 기본 처리로 폴백")
            return None
        try:
            prior_msgs = self.get_chat_messages(session_id, max_turns=self.max_history_length)
            initial_state: AIMentorState = {
                "messages": [*prior_msgs, HumanMessage(content=user_message)],
                "session_id": session_id,
                "current_topic": None,
                "last_sql_result": self.get_last_contexts(session_id).get("sql", ""),
                "last_vector_result": self.get_last_contexts(session_id).get("vector", ""),
                "query_analysis": query_analysis or None,
                "search_results": None,
                "entity_cache": {},
                "metadata": {}
            }

            config = {"configurable": {"thread_id": session_id}}
            final_state = await self.graph.ainvoke(initial_state, config=config)

            ai_messages = [msg for msg in final_state["messages"] if isinstance(msg, AIMessage)]
            if ai_messages:
                response = str(ai_messages[-1].content)
                self._update_session_from_langgraph(session_id, final_state)
                return response
            return None
        except Exception as e:
            logger.error(f"LangGraph 처리 실패: {e}")
            return None



    def _update_session_from_langgraph(self, session_id: str, langgraph_state: AIMentorState):
        """LangGraph 상태를 기존 세션 상태에 반영"""
        state = self.get_state(session_id)

        # 메시지 히스토리 업데이트
        for msg in langgraph_state["messages"]:
            if isinstance(msg, HumanMessage):
                state["conversation_history"].append({
                    "role": "user",
                    "content": str(msg.content),
                    "timestamp": datetime.now().isoformat()
                })
            elif isinstance(msg, AIMessage):
                state["conversation_history"].append({
                    "role": "assistant",
                    "content": str(msg.content),
                    "timestamp": datetime.now().isoformat()
                })

        # 기타 상태 업데이트
        if langgraph_state.get("current_topic"):
            state["current_topic"] = langgraph_state["current_topic"]
        if langgraph_state.get("last_sql_result"):
            state["last_sql_result"] = langgraph_state["last_sql_result"]
        if langgraph_state.get("last_vector_result"):
            state["last_vector_result"] = langgraph_state["last_vector_result"]

        state["updated_at"] = datetime.now()
        logger.debug(f"LangGraph 상태를 세션 {session_id}에 반영 완료")

    def _fallback_processing(self, user_message: str) -> str:
        """LangGraph 실패시 폴백 처리"""
        return f"기본 응답: {user_message}에 대해 처리했습니다."

    async def stream_with_langgraph(self, session_id: str, user_message: str, query_analysis: Optional[Dict[str, Any]] = None):
        """LangGraph를 사용한 스트리밍 처리"""
        if not self.graph:
            yield {"type": "content", "content": self._fallback_processing(user_message)}
            return

        try:
            prior_msgs = self.get_chat_messages(session_id, max_turns=self.max_history_length)
            initial_state: AIMentorState = {
                "messages": [*prior_msgs, HumanMessage(content=user_message)],
                "session_id": session_id,
                "current_topic": None,
                "last_sql_result": self.get_last_contexts(session_id).get("sql", ""),
                "last_vector_result": self.get_last_contexts(session_id).get("vector", ""),
                "query_analysis": query_analysis or None,
                "search_results": None,
                "entity_cache": {},
                "metadata": {}
            }

            config = {"configurable": {"thread_id": session_id}}

            # LangGraph 실행 후, 최종 한 번에 스트리밍(정제된 결과)
            async for event in self.graph.astream(initial_state, config=config):
                if not (event and "generate_response" in event):
                    continue
                state = event["generate_response"]
                if not state.get("messages"):
                    continue
                last_msg = state["messages"][-1]
                if not isinstance(last_msg, AIMessage):
                    continue
                text = str(last_msg.content)
                # 청크 스트리밍(가벼운 분할)
                for i in range(0, len(text), 200):
                    yield {"type": "content", "content": text[i:i+200]}
                break

        except Exception as e:
            logger.error(f"LangGraph 스트리밍 실패: {e}")
            yield {"type": "error", "content": f"스트리밍 오류: {str(e)}"}

    # ToT 통합을 위한 추가 메서드들
    def cache_action_result(self, session_id: str, action_type: str, query_key: str, result_data: Any, confidence: float = 0.8):
        """액션 결과 캐시 (ToT 호환)"""
        state = self.get_state(session_id)

        # 캐시 키 생성
        cache_key = f"{action_type}_{hash(query_key) % 10000}"

        # 엔티티 캐시에 저장
        if action_type.lower() in ['sql_query', 'sql']:
            state["last_sql_result"] = str(result_data)
        elif action_type.lower() in ['faiss_search', 'vector_search']:
            state["last_vector_result"] = str(result_data)

        # 범용 캐시에도 저장
        if "action_cache" not in state["metadata"]:
            state["metadata"]["action_cache"] = {}

        state["metadata"]["action_cache"][cache_key] = {
            "data": result_data,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "query_key": query_key
        }

        state["updated_at"] = datetime.now()
        logger.debug(f"액션 결과 캐시 저장: {action_type} -> {cache_key}")

    def get_cached_result(self, session_id: str, action_type: str, query_key: str) -> Optional[Dict[str, Any]]:
        """캐시된 액션 결과 조회 (ToT 호환)"""
        state = self.get_state(session_id)
        cache_key = f"{action_type}_{hash(query_key) % 10000}"

        action_cache = state["metadata"].get("action_cache", {})
        cached_item = action_cache.get(cache_key)

        if cached_item:
            # 캐시 만료 체크 (24시간)
            cached_time = datetime.fromisoformat(cached_item["timestamp"])
            if (datetime.now() - cached_time).total_seconds() < 86400:  # 24시간
                logger.debug(f"캐시 히트: {cache_key}")
                return cached_item
            else:
                # 만료된 캐시 제거
                del action_cache[cache_key]
                logger.debug(f"만료된 캐시 제거: {cache_key}")

        return None

    def add_decision_trace(self, session_id: str, decision: Dict[str, Any]):
        """의사결정 추적 기록 (ToT 호환)"""
        state = self.get_state(session_id)

        if "decision_trace" not in state["metadata"]:
            state["metadata"]["decision_trace"] = []

        decision_with_timestamp = {
            **decision,
            "timestamp": datetime.now().isoformat()
        }

        state["metadata"]["decision_trace"].append(decision_with_timestamp)

        # 최근 100개만 유지
        if len(state["metadata"]["decision_trace"]) > 100:
            state["metadata"]["decision_trace"] = state["metadata"]["decision_trace"][-100:]

        state["updated_at"] = datetime.now()

    def get_session_statistics(self, session_id: str) -> Dict[str, Any]:
        """세션 통계 조회 (ToT 호환)"""
        state = self.get_state(session_id)

        action_cache = state["metadata"].get("action_cache", {})
        decision_trace = state["metadata"].get("decision_trace", [])

        return {
            "session_id": session_id,
            "total_messages": len(state["conversation_history"]),
            "cached_actions": len(action_cache),
            "decisions_made": len(decision_trace),
            "session_duration_minutes": (datetime.now() - state["created_at"]).total_seconds() / 60,
            "last_activity": state["updated_at"].isoformat(),
            "current_topic": state["current_topic"],
            "has_sql_context": bool(state.get("last_sql_result")),
            "has_vector_context": bool(state.get("last_vector_result"))
        }

    def export_conversation(self, session_id: str) -> Dict[str, Any]:
        """대화 전체 내보내기"""
        state = self.get_state(session_id)

        return {
            "session_id": session_id,
            "conversation_history": state["conversation_history"],
            "metadata": state["metadata"],
            "statistics": self.get_session_statistics(session_id),
            "last_contexts": self.get_last_contexts(session_id),
            "exported_at": datetime.now().isoformat()
        }

    # --- Entity cache helpers ---
    def _norm_key(self, key: str) -> str:
        return (key or '').strip().lower()

    def cache_entity(self, session_id: str, kind: str, key: str, data: Any) -> None:
        state = self.get_state(session_id)
        ek = state["entity_cache"].setdefault(kind, {})
        ek[self._norm_key(key)] = {"data": data, "updated_at": datetime.now().isoformat()}
        state["updated_at"] = datetime.now()

    def get_entity(self, session_id: str, kind: str, key: str, ttl_sec: int = 600) -> Any:
        state = self.get_state(session_id)
        ek = state.get("entity_cache", {}).get(kind, {})
        entry = ek.get(self._norm_key(key))
        if not entry:
            return None
        try:
            ts = datetime.fromisoformat(entry.get("updated_at"))
            if (datetime.now() - ts).total_seconds() > ttl_sec:
                # expired
                del ek[self._norm_key(key)]
                return None
        except Exception:
            pass
        return entry.get("data")
    
