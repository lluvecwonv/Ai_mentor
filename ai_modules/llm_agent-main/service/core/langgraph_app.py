import logging
import asyncio
from typing import Dict, Any
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage

# 핵심 컴포넌트만 import
from ..handlers import (
    VectorSearchHandler,
    SqlQueryHandler,
    DepartmentMappingHandler,
    CurriculumHandler,
    QueryAnalyzer,
    ResultSynthesizer,
    LlmClient
)
from ..memory.memory import ConversationMemory
from ..memory.context_analyzer import ConversationContextAnalyzer
from .langgraph_state import GraphState, create_initial_state
from ..nodes import NodeManager


logger = logging.getLogger(__name__)

class LangGraphApp:
    """LangGraph 애플리케이션"""

    def __init__(self, conversation_memory: ConversationMemory = None):
        logger.info("🏗️ 통합 LangGraph 아키텍처 초기화 시작")

        # 메모리 설정
        self.conversation_memory = conversation_memory

        # LLM 핸들러 생성 (통합 사용)
        self.llm_handler = LlmClient(max_tokens=10000)

        # 히스토리 분석기 초기화 (llm_handler 전달)
        self.context_analyzer = ConversationContextAnalyzer(self.llm_handler)

        # NodeManager 초기화
        self.node_manager = NodeManager(
            query_analyzer=QueryAnalyzer(conversation_memory=self.conversation_memory),
            llm_handler=self.llm_handler,  # 같은 인스턴스 사용
            sql_handler=SqlQueryHandler(),
            vector_handler=VectorSearchHandler(),
            dept_handler=DepartmentMappingHandler(),
            curriculum_handler=CurriculumHandler(),
            result_synthesizer=ResultSynthesizer(self.llm_handler),  # 같은 인스턴스 사용
            conversation_memory=self.conversation_memory,  # 메모리 전달
            llm_client=self.llm_handler  # Light 검증용 LLM Client
        )

        # 그래프 빌드
        self.graph = self.build_graph()

        logger.info("✅ 통합 LangGraph 아키텍처 초기화 완료")

    def build_graph(self) -> StateGraph:
        """그래프 구조 생성"""
        logger.info("🔧 그래프 구조 생성")

        graph = StateGraph(GraphState)

        # NodeManager로부터 모든 노드들 가져오기
        all_nodes = self.node_manager.get_all_nodes()
        conditional_edges = self.node_manager.get_conditional_edges()

        # 노드들 추가
        for node_name, node_func in all_nodes.items():
            graph.add_node(node_name, node_func)

        logger.info(f"✅ {len(all_nodes)}개 노드 추가 완료")

        # 흐름 정의
        graph.add_edge(START, "router")

        # 조건부 엣지들 추가
        for edge_name, edge_func in conditional_edges.items():
            if edge_name == "route_by_complexity":
                graph.add_conditional_edges(
                    "router",
                    edge_func,
                    {
                        "light": "rejection",  # 🔥 light 라우팅되면 바로 거절
                        "medium_sql": "medium_sql",
                        "medium_vector": "medium_vector",
                        "medium_curriculum": "medium_curriculum",
                        "medium_department": "medium_department",
                        "heavy_sequential": "heavy_sequential"
                    }
                )

        # rejection → END (거절 메시지 반환 후 종료)
        graph.add_edge("rejection", END)

        # 모든 처리 노드 → synthesis → finalize → END
        for node in ["medium_sql", "medium_vector",  "medium_department", "heavy_sequential"]:
            graph.add_edge(node, "synthesis")

        graph.add_edge("synthesis", "finalize")
        graph.add_edge("finalize", END)

        compiled_graph = graph.compile()
        logger.info("✅ 통합 그래프 컴파일 완료")

        return compiled_graph

    async def _prepare_query_state(self, user_message: str, session_id: str, stream_callback=None):
        """공통 쿼리 준비 로직 - Follow-up 차단, 히스토리 분석, 쿼리 결정"""
        # Follow-up 질문 생성 요청 차단
        follow_up_patterns = [
            "### Task:",
            "follow-up questions",
            "follow-up prompts",
            "Suggest 3-5 relevant",
            "continue or deepen the discussion"
        ]

        if any(pattern in user_message for pattern in follow_up_patterns):
            logger.warning("🚫 Follow-up 질문 생성 요청 차단")
            return None

        # 히스토리 분석 수행
        default_result = {
            "is_continuation": False,
            "query": user_message,
            "history_usage": {
                "reuse_previous": False,
                "relationship": "new_search"
            }
        }

        if not self.context_analyzer or not self.conversation_memory:
            logger.info("컨텍스트 분석기 또는 메모리가 없습니다. 기본값 반환")
            history_analysis = default_result
        else:
            history_analysis = await self.context_analyzer.analyze_session_context(
                user_message,
                self.conversation_memory,
                session_id
            )

        # 상태 초기화
        initial_state = create_initial_state(user_message, session_id)
        initial_state["conversation_memory"] = self.conversation_memory
        initial_state["is_continuation"] = history_analysis.get("is_continuation", False)
        initial_state["history_usage"] = history_analysis.get("history_usage", {})

        # 스트리밍 콜백 설정
        if stream_callback:
            initial_state["stream_callback"] = stream_callback
        else:
            async def stream_callback_dummy(msg: str):
                logger.info(f"📤 피드백 메시지 (non-streaming): {msg}")
            initial_state["stream_callback"] = stream_callback_dummy

        # 쿼리 결정 로직
        is_continuation = history_analysis.get("is_continuation", False)
        if is_continuation:
            # ✅ 연속대화: reconstructed_query 사용
            query_to_use = history_analysis.get("reconstructed_query", user_message)
            logger.info(f"🔄 연속대화 감지: '{user_message}' → '{query_to_use}'")
        else:
            # ✅ 새로운 질문: 마지막 질문만 추출
            from service.nodes.utils import extract_last_question
            query_to_use = extract_last_question(user_message)
            logger.info(f"🆕 새로운 질문 (마지막 질문 추출): '{query_to_use}'")

        # 🔥 state["query"], user_message, messages 모두 업데이트하여 모든 노드가 올바른 쿼리를 사용하도록 함
        initial_state["query"] = query_to_use
        initial_state["user_message"] = query_to_use
        initial_state["query_for_handlers"] = query_to_use
        initial_state["messages"] = [HumanMessage(content=query_to_use)]

        return initial_state

    async def process_query(self, user_message: str, session_id: str = "default") -> Dict[str, Any]:
        """비스트리밍 쿼리 처리"""
        logger.info(f"🚀 통합 쿼리 처리 시작: '{user_message}...'")

        # 공통 준비 로직
        initial_state = await self._prepare_query_state(user_message, session_id)

        if initial_state is None:
            return {
                "response": "Follow-up 질문 생성 요청은 처리하지 않습니다.",
                "complexity": "blocked",
                "is_continuation": False,
                "history_usage": {}
            }

        # 그래프 실행
        result = await self.graph.ainvoke(initial_state)

        # 응답 생성
        response = result.get("final_result", "응답을 생성할 수 없습니다")

        # 메모리에 대화 저장
        if self.conversation_memory:
            self.conversation_memory.add_exchange(
                session_id=session_id,
                user_message=user_message,
                assistant_response=response
            )
            logger.info(f"💾 대화 저장 완료: session_id={session_id}")

        return {
            "response": response,
            "complexity": result.get("complexity", "unknown"),
            "is_continuation": result.get("is_continuation", False),
            "history_usage": result.get("history_usage", {})
        }

    async def process_query_stream(self, user_message: str, session_id: str = "default"):
        """스트리밍 쿼리 처리"""
        logger.info(f"🚀 스트리밍 쿼리 처리 시작: '{user_message}...'")

        # 스트리밍 콜백 큐 설정
        feedback_queue = []

        async def stream_callback(msg: str):
            feedback_queue.append(msg)

        # 공통 준비 로직
        initial_state = await self._prepare_query_state(user_message, session_id, stream_callback)

        if initial_state is None:
            return

        # 그래프를 스트리밍으로 실행하면서 각 노드마다 피드백 확인
        final_state = None
        async for event in self.graph.astream(initial_state):
            # 노드 실행 후 새로운 피드백이 있으면 즉시 yield (문단 구분)
            while feedback_queue:
                feedback_msg = feedback_queue.pop(0)
                yield feedback_msg + "\n\n"
                await asyncio.sleep(0.01)

            # 마지막 상태 저장
            if event:
                for node_name, node_state in event.items():
                    if node_state:
                        final_state = node_state

        # 남은 피드백 메시지 처리
        while feedback_queue:
            feedback_msg = feedback_queue.pop(0)
            yield feedback_msg + "\n\n"
            await asyncio.sleep(0.01)

        # final_result가 있으면 그대로 스트리밍
        final_result = final_state.get("final_result", "") if final_state else ""

        if final_result:
            # 결과를 한 글자씩 스트리밍 (시뮬레이션)
            for char in final_result:
                yield char
                await asyncio.sleep(0.01)  # 스트리밍 효과

            # 메모리에 저장
            if self.conversation_memory:
                self.conversation_memory.add_exchange(
                    session_id=session_id,
                    user_message=user_message,
                    assistant_response=final_result
                )
                logger.info(f"💾 대화 저장 완료: session_id={session_id}")
        else:
            yield "응답을 생성할 수 없습니다."