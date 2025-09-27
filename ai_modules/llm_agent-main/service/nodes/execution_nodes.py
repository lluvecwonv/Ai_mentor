"""
실행 노드들 - Light, Medium, Heavy 복잡도 통합
복잡도에 따라 다른 처리 방식을 제공하는 통합 노드
"""

import logging
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from .base_node import BaseNode, NodeTimer

logger = logging.getLogger(__name__)


class ExecutionNodes(BaseNode):
    """
    통합 실행 노드 클래스
    Light, Medium, Heavy 복잡도를 모두 처리
    """

    def __init__(self, llm_handler, sql_handler=None, vector_handler=None,
                 dept_handler=None, curriculum_handler=None):
        self.llm_handler = llm_handler
        self.sql_handler = sql_handler
        self.vector_handler = vector_handler
        self.dept_handler = dept_handler
        self.curriculum_handler = curriculum_handler

    # =============== Light 복잡도 노드들 ===============
    async def light_llm_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Light 복잡도: 간단한 LLM 직접 호출"""
        try:
            with NodeTimer("light_llm_node") as timer:
                logger.info("🟢 Light LLM 노드 실행 시작")

                query = state.get("current_query", "")

                messages = [
                    SystemMessage(content="당신은 학과정보를 제공하는 AI 어시스턴트입니다."),
                    HumanMessage(content=query)
                ]

                if hasattr(self.llm_handler, 'run_basic_chain'):
                    response = await self.llm_handler.run_basic_chain(messages)
                else:
                    response = await self.llm_handler.handle(query, {})

                result = {
                    "light_llm_result": response,
                    "complexity": "light",
                    "processing_time": timer.duration
                }

                logger.info(f"✅ Light LLM 노드 완료 ({timer.duration:.2f}s)")
                return result

        except Exception as e:
            logger.error(f"❌ Light LLM 노드 실패: {e}")
            return {
                "light_llm_result": f"처리 중 오류가 발생했습니다: {str(e)}",
                "complexity": "light",
                "error": str(e)
            }

    # =============== Medium 복잡도 노드들 ===============
    async def medium_single_agent_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Medium 복잡도: 단일 에이전트 실행"""
        try:
            with NodeTimer("medium_single_agent_node") as timer:
                logger.info("🟡 Medium 단일 에이전트 노드 실행 시작")

                plan_step = state.get("plan", [{}])[0]
                agent_type = plan_step.get("agent", "")
                query = state.get("current_query", "")

                # 에이전트 타입에 따른 처리
                if "SQL" in agent_type and self.sql_handler:
                    result = await self.sql_handler.handle(query, plan_step)
                elif "FAISS" in agent_type and self.vector_handler:
                    # expanded_query와 keywords 전달
                    expanded_query = state.get("expanded_query", query)
                    keywords = state.get("keywords", "")
                    result = await self.vector_handler.handle(expanded_query, plan_step, keywords=keywords)
                elif "DEPARTMENT" in agent_type and self.dept_handler:
                    result = await self.dept_handler.handle(query, plan_step)
                elif "CURRICULUM" in agent_type and self.curriculum_handler:
                    result = await self.curriculum_handler.handle(query, plan_step)
                elif "DEPARTMENT" in agent_type and not self.dept_handler:
                    result = f"Department handler가 초기화되지 않았습니다. {agent_type} 처리를 위해 handler를 설정해주세요."
                elif "CURRICULUM" in agent_type and not self.curriculum_handler:
                    result = f"Curriculum handler가 초기화되지 않았습니다. {agent_type} 처리를 위해 handler를 설정해주세요."
                elif "SQL" in agent_type and not self.sql_handler:
                    result = f"SQL handler가 초기화되지 않았습니다. {agent_type} 처리를 위해 handler를 설정해주세요."
                elif "FAISS" in agent_type and not self.vector_handler:
                    result = f"Vector handler가 초기화되지 않았습니다. {agent_type} 처리를 위해 handler를 설정해주세요."
                else:
                    # 기본 LLM 처리
                    if self.llm_handler and hasattr(self.llm_handler, 'handle'):
                        result = await self.llm_handler.handle(query, plan_step)
                    elif self.llm_handler and hasattr(self.llm_handler, 'run_basic_chain'):
                        result = await self.llm_handler.run_basic_chain(query)
                    else:
                        result = f"LLM handler가 초기화되지 않았거나 필요한 메서드가 없습니다. Agent: {agent_type}"

                response = {
                    "medium_result": result,
                    "agent_used": agent_type,
                    "complexity": "medium",
                    "processing_time": timer.duration
                }

                logger.info(f"✅ Medium 노드 완료 ({timer.duration:.2f}s)")
                return response

        except Exception as e:
            logger.error(f"❌ Medium 노드 실패: {e}")
            return {
                "medium_result": f"처리 중 오류가 발생했습니다: {str(e)}",
                "complexity": "medium",
                "error": str(e)
            }

    # =============== Heavy 복잡도 노드들 ===============
    async def heavy_sequential_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Heavy 복잡도: 순차적 에이전트 실행"""
        try:
            with NodeTimer("heavy_sequential_node") as timer:
                logger.info("🔴 Heavy 순차 실행 노드 시작")

                plan = state.get("plan", [])
                query = state.get("current_query", "")
                results = []

                for i, step in enumerate(plan):
                    step_timer = NodeTimer(f"heavy_step_{i+1}")
                    step_timer.__enter__()

                    agent_type = step.get("agent", "")
                    goal = step.get("goal", "")

                    logger.info(f"🔄 Heavy 단계 {i+1}/{len(plan)}: {agent_type}")

                    try:
                        # 에이전트 타입별 실행
                        if "SQL" in agent_type and self.sql_handler:
                            step_result = await self.sql_handler.handle(query, step)
                        elif "FAISS" in agent_type and self.vector_handler:
                            # expanded_query와 keywords 전달
                            expanded_query = state.get("expanded_query", query)
                            keywords = state.get("keywords", "")
                            step_result = await self.vector_handler.handle(expanded_query, step, keywords=keywords)
                        elif "DEPARTMENT" in agent_type and self.dept_handler:
                            step_result = await self.dept_handler.handle(query, step)
                        elif "CURRICULUM" in agent_type and self.curriculum_handler:
                            step_result = await self.curriculum_handler.handle(query, step)
                        elif "DEPARTMENT" in agent_type and not self.dept_handler:
                            step_result = f"Department handler가 초기화되지 않았습니다. {agent_type} 처리를 위해 handler를 설정해주세요."
                        elif "CURRICULUM" in agent_type and not self.curriculum_handler:
                            step_result = f"Curriculum handler가 초기화되지 않았습니다. {agent_type} 처리를 위해 handler를 설정해주세요."
                        elif "SQL" in agent_type and not self.sql_handler:
                            step_result = f"SQL handler가 초기화되지 않았습니다. {agent_type} 처리를 위해 handler를 설정해주세요."
                        elif "FAISS" in agent_type and not self.vector_handler:
                            step_result = f"Vector handler가 초기화되지 않았습니다. {agent_type} 처리를 위해 handler를 설정해주세요."
                        else:
                            if self.llm_handler and hasattr(self.llm_handler, 'handle'):
                                step_result = await self.llm_handler.handle(query, step)
                            elif self.llm_handler and hasattr(self.llm_handler, 'run_basic_chain'):
                                step_result = await self.llm_handler.run_basic_chain(query)
                            else:
                                step_result = f"LLM handler가 초기화되지 않았거나 필요한 메서드가 없습니다. Agent: {agent_type}"

                        results.append({
                            "step": i + 1,
                            "agent": agent_type,
                            "goal": goal,
                            "result": step_result,
                            "processing_time": step_timer.duration
                        })

                        logger.info(f"✅ Heavy 단계 {i+1} 완료")

                    except Exception as step_e:
                        logger.error(f"❌ Heavy 단계 {i+1} 실패: {step_e}")
                        results.append({
                            "step": i + 1,
                            "agent": agent_type,
                            "goal": goal,
                            "result": f"단계 실패: {str(step_e)}",
                            "error": str(step_e)
                        })
                    finally:
                        step_timer.__exit__(None, None, None)

                response = {
                    "heavy_results": results,
                    "complexity": "heavy",
                    "total_steps": len(plan),
                    "processing_time": timer.duration
                }

                logger.info(f"✅ Heavy 순차 노드 완료 ({timer.duration:.2f}s)")
                return response

        except Exception as e:
            logger.error(f"❌ Heavy 노드 실패: {e}")
            return {
                "heavy_results": [],
                "complexity": "heavy",
                "error": str(e)
            }

    # =============== 유틸리티 메소드들 ===============
    def _format_agent_response(self, agent_type: str, result: Any) -> str:
        """에이전트 응답을 포맷팅"""
        if isinstance(result, dict):
            return str(result.get('content', result))
        elif isinstance(result, list):
            return '\n'.join(str(item) for item in result)
        else:
            return str(result)

    def _get_execution_strategy(self, complexity: str) -> str:
        """복잡도에 따른 실행 전략 반환"""
        strategies = {
            "light": "direct_llm",
            "medium": "single_agent",
            "heavy": "sequential_agents"
        }
        return strategies.get(complexity, "direct_llm")