import logging
from .routing_nodes import RoutingNodes
from .synthesis_nodes import SynthesisNodes
from .query_route.light_nodes import LightNodes
from .query_route.medium_nodes import MediumNodes
from .query_route.heavy_nodes import HeavyNodes
from .utility_nodes import UtilityNodes
logger = logging.getLogger(__name__)

class NodeManager:
    """노드 관리자 - 모든 노드들을 한 곳에서 관리"""

    def __init__(self, query_analyzer=None, llm_handler=None,
                 sql_handler=None, vector_handler=None,
                 dept_handler=None, curriculum_handler=None,
                 result_synthesizer=None, openai_client=None):

        # Node categories 초기화
        self.routing = RoutingNodes(query_analyzer, openai_client)
        self.light = LightNodes(llm_handler)
        self.medium = MediumNodes(sql_handler, vector_handler, dept_handler, curriculum_handler)
        self.heavy = HeavyNodes(sql_handler, vector_handler, dept_handler, curriculum_handler, llm_handler)
        self.synthesis = SynthesisNodes(result_synthesizer)
        self.utility = UtilityNodes()

    def get_all_nodes(self) -> dict:
        """모든 노드들을 딕셔너리로 반환 (LangGraph 등록용)"""
        nodes = {
            # Routing nodes
            "router": self.routing.router_node,

            # Light node
            "light": self.light.light_node,

            # Medium nodes
            "medium_agent": self.medium.medium_agent_node,
            "medium_sql": self.medium.medium_sql_node,
            "medium_vector": self.medium.medium_vector_node,
            "medium_curriculum": self.medium.medium_curriculum_node,

            # Heavy nodes
            "heavy_sequential": self.heavy.heavy_sequential_executor,

            # Synthesis nodes
            "synthesis": self.synthesis.synthesis_node,
            "quick_synthesis": self.synthesis.quick_synthesis_node,
            "tot_synthesis": self.synthesis.tot_synthesis_node,

            # Utility nodes
            "finalize": self.utility.finalize_node,
            "error_handling": self.utility.error_handling_node,
            "health_check": self.utility.health_check_node,
            "debug": self.utility.debug_node,
        }

        logger.info(f"🎯 총 {len(nodes)}개 노드 등록: {list(nodes.keys())}")
        return nodes

    def get_conditional_edges(self) -> dict:
        """조건부 엣지들 반환 (LangGraph 등록용)"""

        def route_by_complexity(state: dict) -> str:
            """복잡도에 따른 세부 라우팅"""
            complexity = state.get("route", "medium")
            plan = state.get("plan", []) or []

            # Light 복잡도
            if complexity == "light":
                return "light"

            # Medium 복잡도 - plan 기반으로 세부 분기
            elif complexity == "medium":
                if plan and len(plan) > 0:
                    first_agent = plan[0].get("agent", "").upper()
                    if "SQL" in first_agent:
                        return "medium_sql"
                    elif "FAISS" in first_agent or "SEARCH" in first_agent:
                        return "medium_vector"
                    elif "CURRICULUM" in first_agent:
                        return "medium_curriculum"

                # 기본 medium 처리
                return "medium_agent"

            # Heavy 복잡도
            elif complexity == "heavy":
                return "heavy_sequential"

            # 기본값
            return "medium_agent"

        return {
            "route_by_complexity": route_by_complexity
        }

    def validate_setup(self) -> dict:
        """노드 설정 유효성 검사"""
        return {
            "routing": True,
            "light": True,
            "medium": True,
            "heavy": True,
            "synthesis": True,
            "utility": True,
            "total_nodes": len(self.get_all_nodes())
        }