"""
LangGraph 애플리케이션
복잡도별 처리를 위한 그래프 구조
"""

import logging
from typing import Dict, Any
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END

# 핵심 컴포넌트만 import
from handlers import (
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
        """
        통합 그래프 초기화

        Args:
            conversation_memory: 대화 메모리 (기존 시스템과 공유)
        """
        logger.info("🏗️ 통합 LangGraph 아키텍처 초기화 시작")

        # 메모리 설정
        self.conversation_memory = conversation_memory

        # LLM 핸들러 생성 (통합 사용)
        self.llm_handler = LlmClient()

        # 히스토리 분석기 초기화 (llm_handler 전달)
        self.context_analyzer = ConversationContextAnalyzer(self.llm_handler)

        # NodeManager 초기화
        self.node_manager = NodeManager(
            query_analyzer=QueryAnalyzer(),
            llm_handler=self.llm_handler,  # 같은 인스턴스 사용
            sql_handler=SqlQueryHandler(),
            vector_handler=VectorSearchHandler(),
            dept_handler=DepartmentMappingHandler(),
            curriculum_handler=CurriculumHandler(),
            result_synthesizer=ResultSynthesizer(self.llm_handler)  # 같은 인스턴스 사용
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
                        "light": "light",
                        "medium_sql": "medium_sql",
                        "medium_vector": "medium_vector",
                        "medium_curriculum": "medium_curriculum",
                        "heavy_sequential": "heavy_sequential"
                    }
                )

        # 모든 처리 노드 → synthesis → finalize → END
        for node in ["light", "medium_sql", "medium_vector", "medium_curriculum", "heavy_sequential"]:
            graph.add_edge(node, "synthesis")

        graph.add_edge("synthesis", "finalize")
        graph.add_edge("finalize", END)

        compiled_graph = graph.compile()
        logger.info("✅ 통합 그래프 컴파일 완료")

        return compiled_graph

    async def process_query(self, user_message: str, session_id: str = "default") -> Dict[str, Any]:
        """통합 쿼리 처리 - 히스토리 분석 포함"""
        logger.info(f"🚀 통합 쿼리 처리 시작: '{user_message[:50]}...'")

        # 히스토리 분석 수행 (context_analyzer에 완전 위임)
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

        # 그래프 실행
        result = await self.graph.ainvoke(initial_state)

        # 응답 생성
        response = result.get("final_result", "응답을 생성할 수 없습니다")

        # 메모리에 대화 저장 (다음 턴을 위해)
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


