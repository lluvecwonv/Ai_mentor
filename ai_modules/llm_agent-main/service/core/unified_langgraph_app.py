"""
통합 LangGraph 아키텍처
Light/Medium/Heavy 복잡도를 모두 처리하는 단일 그래프
"""

from __future__ import annotations
import logging
import time
import asyncio
from typing import Dict, Any, List, Literal
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# 기존 컴포넌트들 import
from processors.router import Router
from handlers import (
    VectorSearchHandler,
    SqlQueryHandler,
    DepartmentMappingHandler,
    CurriculumHandler
)
from service.analysis.result_synthesizer import ResultSynthesizer
from service.analysis.query_analyzer import QueryAnalyzer
from service.core.memory import ConversationMemory

# LangGraph 상태 import
from .langgraph_state import UnifiedMentorState, get_user_message, add_step_time
from service.nodes import NodeManager

# 단일 LLM 클라이언트 사용 (단순화)
from utils.llm_client_langchain import LlmClientLangChain as LlmClientLangChainAdvanced

logger = logging.getLogger(__name__)

class UnifiedLangGraphApp:
    """통합 LangGraph 애플리케이션"""

    def __init__(self, conversation_memory: ConversationMemory = None):
        """
        통합 그래프 초기화

        Args:
            conversation_memory: 대화 메모리 (기존 시스템과 공유)
        """
        logger.info("🏗️ 통합 LangGraph 아키텍처 초기화 시작")

        # 기존 컴포넌트들 초기화
        self.query_analyzer = QueryAnalyzer()
        self.conversation_memory = conversation_memory

        # 핸들러들 초기화
        self.vector_handler = VectorSearchHandler()
        self.sql_handler = SqlQueryHandler()
        self.dept_handler = DepartmentMappingHandler()
        self.curriculum_handler = CurriculumHandler()

        # LLM 핸들러 초기화 (단순화)
        self.llm_handler = LlmClientLangChainAdvanced()

        # 결과 합성기
        self.result_synthesizer = ResultSynthesizer(self.llm_handler)

        # OpenAI 클라이언트 생성
        from openai import OpenAI
        from config.settings import settings
        openai_client = OpenAI(api_key=settings.openai_api_key)

        # NodeManager 초기화
        self.node_manager = NodeManager(
            query_analyzer=self.query_analyzer,
            llm_handler=self.llm_handler,
            sql_handler=self.sql_handler,
            vector_handler=self.vector_handler,
            dept_handler=self.dept_handler,
            curriculum_handler=self.curriculum_handler,
            result_synthesizer=self.result_synthesizer,
            openai_client=openai_client
        )

        # 그래프 빌드
        self.graph = self._build_unified_graph()

        logger.info("✅ 통합 LangGraph 아키텍처 초기화 완료")

    def _build_unified_graph(self) -> StateGraph:
        """통합 그래프 구조 생성"""
        logger.info("🔧 통합 그래프 구조 생성")

        graph = StateGraph(UnifiedMentorState)

        # NodeManager로부터 모든 노드들 가져오기
        all_nodes = self.node_manager.get_all_nodes()
        conditional_edges = self.node_manager.get_conditional_edges()

        # 노드들 추가
        for node_name, node_func in all_nodes.items():
            graph.add_node(node_name, node_func)
            logger.debug(f"  노드 추가: {node_name}")

        logger.info(f"✅ {len(all_nodes)}개 노드 추가 완료")

        # 흐름 정의
        graph.add_edge(START, "router")

        # 조건부 엣지들 추가
        for edge_name, edge_func in conditional_edges.items():
            if edge_name == "route_by_complexity":
                # 복잡도별 라우팅
                graph.add_conditional_edges(
                    "router",
                    edge_func,
                    {
                        "light_llm": "light_llm",
                        "light_greeting": "light_greeting",
                        "medium_sql": "medium_sql",
                        "medium_vector": "medium_vector",
                        "medium_curriculum": "medium_curriculum",
                        "medium_agent": "medium_agent",
                        "heavy_sequential": "heavy_sequential"
                    }
                )

        # Light 처리 흐름
        graph.add_edge("light_llm", "synthesis")
        graph.add_edge("light_greeting", "synthesis")

        # Medium 처리 흐름
        graph.add_edge("medium_sql", "synthesis")
        graph.add_edge("medium_vector", "synthesis")
        graph.add_edge("medium_curriculum", "synthesis")
        graph.add_edge("medium_agent", "synthesis")

        # Heavy 처리 흐름 (순차 실행만)

        # Heavy 순차 처리 흐름
        graph.add_edge("heavy_sequential", "synthesis")

        # 합성 및 완료
        graph.add_edge("synthesis", "finalize")
        graph.add_edge("finalize", END)

        compiled_graph = graph.compile()
        logger.info("✅ 통합 그래프 컴파일 완료")

        return compiled_graph

    async def process_query(self, user_message: str, session_id: str = "default") -> Dict[str, Any]:
        """통합 쿼리 처리"""
        logger.info(f"🚀 통합 쿼리 처리 시작: '{user_message[:50]}...'")

        try:
            # 상태 초기화
            initial_state = {
                "messages": [HumanMessage(content=user_message)],
                "session_id": session_id,
                "user_query": user_message,
                "slots": {},
                "step_times": {},
                "retry_count": 0,
                "parallel_tasks": [],
                "processing_type": "unknown",
                "conversation_memory": self.conversation_memory  # 연속대화 분석용
            }

            # 그래프 실행
            result = await self.graph.ainvoke(initial_state)

            return {
                "response": result.get("final_result", "응답을 생성할 수 없습니다"),
                "processing_type": result.get("processing_type", "unknown"),
                "hybrid_info": {
                    "query_analysis": {
                        "complexity": result.get("complexity", "unknown"),
                        "plan": result.get("plan", [])
                    }
                },
                "execution_stats": result.get("execution_stats", {})
            }

        except Exception as e:
            logger.error(f"❌ 통합 쿼리 처리 실패: {e}")
            return {
                "response": "처리 중 오류가 발생했습니다. 다시 시도해주세요.",
                "processing_type": "error",
                "error": str(e)
            }


def create_unified_langgraph_app(conversation_memory: ConversationMemory = None) -> UnifiedLangGraphApp:
    """통합 LangGraph 앱 생성 팩토리"""
    return UnifiedLangGraphApp(conversation_memory)