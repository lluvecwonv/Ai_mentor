"""
LangGraph 노드들 통합 모듈
모든 노드들을 깔끔하게 import할 수 있도록 구성
"""

# Base classes
from .base_node import BaseNode, NodeTimer

# Node categories
from .routing_nodes import RoutingNodes
from .synthesis_nodes import SynthesisNodes
from typing import Dict, Any
# TODO: Add when implemented
# from .light_nodes import LightNodes
# from .medium_nodes import MediumNodes
# from .heavy_nodes import HeavyNodes
# from .utility_nodes import UtilityNodes

# Placeholder classes
class LightNodes:
    def __init__(self, llm_handler=None):
        self.llm_handler = llm_handler

    async def light_llm_node(self, *args, **kwargs):
        """Light LLM 노드"""
        return {"response": "Light complexity response", "next": "finalize"}

    async def light_greeting_node(self, *args, **kwargs):
        """Light 인사 노드"""
        return {"response": "안녕하세요! 무엇을 도와드릴까요?", "next": "finalize"}

class MediumNodes:
    def __init__(self, sql_handler=None, vector_handler=None, dept_handler=None, curriculum_handler=None):
        self.sql_handler = sql_handler
        self.vector_handler = vector_handler
        self.dept_handler = dept_handler
        self.curriculum_handler = curriculum_handler

    async def medium_agent_node(self, *args, **kwargs):
        print("🟡🟡🟡🟡🟡 MEDIUM AGENT NODE CALLED! 🟡🟡🟡🟡🟡")
        return {"response": "Medium agent response", "next": "synthesis"}

    async def medium_sql_node(self, *args, **kwargs):
        return {"response": "Medium SQL response", "next": "synthesis"}

    async def medium_vector_node(self, *args, **kwargs):
        return {"response": "Medium vector response", "next": "synthesis"}

    async def medium_curriculum_node(self, state):
        """Medium 커리큘럼 노드 - 실제 커리큘럼 핸들러 호출"""
        import logging
        logger = logging.getLogger(__name__)

        logger.info("🚀🚀🚀 [CURRICULUM] medium_curriculum_node 메서드 진입!")
        logger.info(f"🔍 [CURRICULUM] state 키들: {list(state.keys())}")

        try:
            logger.info("⚡ [CURRICULUM] 커리큘럼 핸들러 호출 준비!")

            # 기본적인 메시지 처리
            if "messages" in state and state["messages"]:
                user_message = state["messages"][-1].content
            else:
                user_message = state.get("user_message", "커리큘럼을 짜줘")

            session_id = state.get("session_id", "default")

            logger.info(f"📝 [CURRICULUM] 사용자 메시지: '{user_message}'")
            logger.info(f"🎯 [CURRICULUM] 세션 ID: {session_id}")

            # 커리큘럼 핸들러가 없으면 기본 응답
            if not hasattr(self, 'curriculum_handler') or self.curriculum_handler is None:
                logger.warning("⚠️ [CURRICULUM] curriculum_handler가 없음 - 기본 응답 반환")
                return {
                    **state,
                    "response": "커리큘럼 핸들러가 초기화되지 않았습니다.",
                    "next": "synthesis"
                }

            # 쿼리 분석 정보 구성
            query_analysis = {
                "complexity": state.get("complexity", "medium"),
                "plan": state.get("plan", []),
                "reasoning": state.get("routing_reason", ""),
                "expanded_query": state.get("expanded_query", user_message),
                "keywords": state.get("keywords", "")
            }

            logger.info(f"🔍 [CURRICULUM] CurriculumHandler 호출 시작")
            result = await self.curriculum_handler.handle(
                user_message=user_message,
                query_analysis=query_analysis,
                session_id=session_id
            )
            logger.info(f"✅ [CURRICULUM] CurriculumHandler 결과: {len(str(result))} 문자")

            return {
                **state,
                "response": result,
                "processing_type": "medium_curriculum",
                "next": "synthesis"
            }

        except Exception as e:
            logger.error(f"❌ [CURRICULUM] 오류 발생: {e}")
            import traceback
            logger.error(f"❌ [CURRICULUM] 스택 트레이스:\n{traceback.format_exc()}")
            return {
                **state,
                "response": f"커리큘럼 처리 중 오류가 발생했습니다: {str(e)}",
                "next": "synthesis"
            }

class HeavyNodes:
    def __init__(self, sql_handler=None, vector_handler=None, dept_handler=None, curriculum_handler=None, llm_handler=None):
        self.sql_handler = sql_handler
        self.vector_handler = vector_handler
        self.dept_handler = dept_handler
        self.curriculum_handler = curriculum_handler
        self.llm_handler = llm_handler

    async def heavy_sequential_executor(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Heavy 복잡도: 순차적 에이전트 실행 (execution_nodes로 위임)"""
        import logging
        logger = logging.getLogger(__name__)

        logger.info("🔴 Heavy Sequential Executor 시작")
        logger.info(f"🔍 State 내용: {list(state.keys())}")

        from .execution_nodes import ExecutionNodes

        # ExecutionNodes 인스턴스 생성
        executor = ExecutionNodes(
            llm_handler=self.llm_handler,  # LLM 핸들러 전달
            sql_handler=self.sql_handler,
            vector_handler=self.vector_handler,
            dept_handler=self.dept_handler,
            curriculum_handler=self.curriculum_handler
        )

        # 실제 heavy_sequential_node 실행
        logger.info("🔴 ExecutionNodes.heavy_sequential_node 호출")
        result = await executor.heavy_sequential_node(state)
        logger.info(f"🔴 Heavy Sequential Executor 완료: {len(str(result))}자")

        return result

class UtilityNodes:
    def __init__(self, *args, **kwargs):
        pass
    async def finalize_node(self, state):
        """최종 처리 노드"""
        return {"final_response": state.get("response", "처리 완료")}
    async def error_handling_node(self, state):
        """에러 처리 노드"""
        return {"error_handled": True, "response": "오류가 발생했습니다."}
    async def health_check_node(self, *args, **kwargs):
        """헬스 체크 노드"""
        return {"status": "healthy"}
    async def debug_node(self, state):
        """디버그 노드"""
        return {"debug_info": str(state)}

# All nodes in one place
__all__ = [
    # Base
    "BaseNode",
    "NodeTimer",

    # Node classes
    "RoutingNodes",
    "LightNodes",
    "MediumNodes",
    "HeavyNodes",
    "SynthesisNodes",
    "UtilityNodes",
]


class NodeManager:
    """노드 관리자 - 모든 노드들을 한 곳에서 관리"""

    def __init__(self, query_analyzer=None, llm_handler=None,
                 sql_handler=None, vector_handler=None,
                 dept_handler=None, curriculum_handler=None,
                 result_synthesizer=None, openai_client=None):
        """
        노드 관리자 초기화

        Args:
            query_analyzer: 쿼리 분석기
            llm_handler: LLM 핸들러
            sql_handler: SQL 검색 핸들러
            vector_handler: 벡터 검색 핸들러
            dept_handler: 학과 매핑 핸들러
            curriculum_handler: 커리큘럼 핸들러
            result_synthesizer: 결과 합성기
        """
        # Node categories 초기화
        self.routing = RoutingNodes(query_analyzer, openai_client) if query_analyzer else None
        self.light = LightNodes(llm_handler) if llm_handler else None

        if all([sql_handler, vector_handler, dept_handler, curriculum_handler]):
            self.medium = MediumNodes(sql_handler, vector_handler, dept_handler, curriculum_handler)
            self.heavy = HeavyNodes(sql_handler, vector_handler, dept_handler, curriculum_handler, llm_handler)
        else:
            self.medium = None
            self.heavy = None

        self.synthesis = SynthesisNodes(result_synthesizer) if result_synthesizer else None
        self.utility = UtilityNodes()

    def get_all_nodes(self) -> dict:
        """모든 노드들을 딕셔너리로 반환 (LangGraph 등록용)"""
        import logging
        logger = logging.getLogger(__name__)

        nodes = {}

        # Routing nodes
        if self.routing:
            nodes.update({
                "router": self.routing.router_node,
            })
            logger.info("✅ Router 노드 등록 완료")

        # Light nodes
        if self.light:
            nodes.update({
                "light_llm": self.light.light_llm_node,
                "light_greeting": self.light.light_greeting_node,
            })
            logger.info("✅ Light 노드들 등록 완료")

        # Medium nodes
        if self.medium:
            nodes.update({
                "medium_agent": self.medium.medium_agent_node,
                "medium_sql": self.medium.medium_sql_node,
                "medium_vector": self.medium.medium_vector_node,
                "medium_curriculum": self.medium.medium_curriculum_node,
            })
            logger.info("✅ Medium 노드들 등록 완료")

        # Heavy nodes (순차 실행만)
        if self.heavy:
            nodes.update({
                "heavy_sequential": self.heavy.heavy_sequential_executor,
            })
            logger.info("✅ Heavy 노드 (heavy_sequential) 등록 완료")
            logger.info(f"🔍 Heavy handler 상태 - sql:{bool(self.heavy.sql_handler)}, vector:{bool(self.heavy.vector_handler)}")
        else:
            logger.warning("❌ Heavy 노드 등록 실패 - self.heavy가 None")

        # Synthesis nodes
        if self.synthesis:
            nodes.update({
                "synthesis": self.synthesis.synthesis_node,
                "quick_synthesis": self.synthesis.quick_synthesis_node,
                "tot_synthesis": self.synthesis.tot_synthesis_node,
            })
            logger.info("✅ Synthesis 노드들 등록 완료")

        # Utility nodes
        nodes.update({
            "finalize": self.utility.finalize_node,
            "error_handling": self.utility.error_handling_node,
            "health_check": self.utility.health_check_node,
            "debug": self.utility.debug_node,
        })
        logger.info("✅ Utility 노드들 등록 완료")

        logger.info(f"🎯 총 {len(nodes)}개 노드 등록: {list(nodes.keys())}")
        return nodes

    def get_conditional_edges(self) -> dict:
        """조건부 엣지들 반환 (LangGraph 등록용)"""
        edges = {}

        if self.routing:
            edges["route_by_complexity"] = self.routing.route_by_complexity

        return edges

    def validate_setup(self) -> dict:
        """노드 설정 유효성 검사"""
        status = {
            "routing": bool(self.routing),
            "light": bool(self.light),
            "medium": bool(self.medium),
            "heavy": bool(self.heavy),
            "synthesis": bool(self.synthesis),
            "utility": bool(self.utility),
        }

        status["total_nodes"] = sum(len(nodes) for nodes in [
            self.get_all_nodes()
        ])

        return status