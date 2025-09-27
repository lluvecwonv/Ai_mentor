"""
체인 프로세서 - 간소화된 체인 처리 관리자
모든 복잡한 로직을 개별 프로세서로 위임하고, 단순한 조정만 담당
"""

import logging
from typing import Dict, Any
# LangGraph 전용 모드로 간소화
logger = logging.getLogger(__name__)

from .router import Router
from .vector_processor import VectorProcessor
from .sql_processor import SqlProcessor
from .llm_processor import LlmProcessor
from .mapping_processor import MappingProcessor
from .result_integrator import ResultIntegrator

# LangGraph 전용 모드로 간소화 - ToT 제거

class ChainProcessor:
    """간소화된 체인 프로세서 - 복잡한 로직은 개별 프로세서가 담당"""

    def __init__(self, query_analyzer, conversation_memory, llm_handler,
                 vector_handler, sql_handler, mapping_handler, settings=None):
        # LangGraph 전용 모드로 간소화

        # 개별 프로세서 초기화
        self.vector_processor = VectorProcessor(vector_handler)
        self.sql_processor = SqlProcessor(sql_handler, conversation_memory)
        self.mapping_processor = MappingProcessor(mapping_handler)
        self.llm_processor = LlmProcessor(llm_handler, settings)
        
        # LangGraph 전용 모드로 간소화
        
        # 라우터에 프로세서 의존성 주입
        self.router = Router(
            vector_processor=self.vector_processor,
            sql_processor=self.sql_processor,
            mapping_processor=self.mapping_processor,
            llm_processor=self.llm_processor
        )
        self.result_integrator = ResultIntegrator()

        # 기존 컴포넌트들 (호환성 유지)
        self.query_analyzer = query_analyzer
        self.conversation_memory = conversation_memory
        self.llm_handler = llm_handler

        logger.debug("ChainProcessor 초기화 완료 - 모듈형 아키텍처")

    async def execute_with_context(
        self,
        resolved_query: str,
        query_analysis: Dict[str, Any],
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """
        컨텍스트를 포함한 체인 실행

        Args:
            resolved_query: LLM이 이해한 해결된 쿼리
            query_analysis: 쿼리 분석 결과
            context: 대화 컨텍스트 정보
            session_id: 세션 ID

        Returns:
            처리 결과
        """
        try:
            # 데이터 구조 준비
            data = {
                "user_message": resolved_query,
                "analysis": query_analysis,
                "context": context,
                "session_id": session_id,
                "conversation_memory": self.conversation_memory
            }

            # 기존 process 메서드 활용
            result = await self.process(data)

            # OpenAI 형식으로 변환
            if not result.get("choices"):
                content = result.get("result", "처리 완료")
                result = {
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": content
                        },
                        "finish_reason": "stop"
                    }]
                }

            return result

        except Exception as e:
            logger.error(f"컨텍스트 처리 실패: {e}")
            return {
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": f"죄송합니다. 처리 중 오류가 발생했습니다: {str(e)}"
                    },
                    "finish_reason": "error"
                }]
            }

    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """메인 처리 함수 - 라우팅 → 실행 → 통합 (직접 실행)"""
        # async with self.performance_tracker.measure_time_async("total_processing"):
        try:
            # 1) 분석 후 바로 실행
            query_analysis = data.get("analysis", data.get("pre_analysis", {}))
            logger.info(f"체인 처리 시작: {query_analysis.get('complexity')}")

            # ConversationMemory를 데이터에 포함
            data_with_memory = {
                **data,
                "conversation_memory": self.conversation_memory
            }

            results = await self.router.process(query_analysis, data_with_memory)

            # 2) 결과 검증 및 통합
            if results is None:
                logger.error("라우터가 None을 반환했습니다.")
                results = {
                    "processing_type": "error",
                    "result": "처리 중 오류가 발생했습니다.",
                    "error": "router returned None"
                }

            logger.info(f"🔧 라우터 결과: {results.get('processing_type')} (키: {list(results.keys()) if isinstance(results, dict) else type(results)})")

            # ToT 결과인 경우 컨텍스트를 포함하여 통합
            if results.get('processing_type') == 'tot':
                tot_context = results.get('tot_context', {})

                # ToT가 실행한 각 프로세서들의 결과를 contexts로 수집
                contexts = results.get('contexts', {})
                if not contexts:
                    # contexts가 없으면 tot_context에서 추출 시도
                    contexts = {
                        "sql": tot_context.get('sql_context', tot_context.get('sql', "")),
                        "vector": tot_context.get('vector_context', tot_context.get('vector', "")),
                        "mapping": tot_context.get('mapping_context', tot_context.get('mapping', "")),
                        "tot_raw": tot_context
                    }
                    results['contexts'] = contexts  # ToT 결과에 contexts 추가

                logger.info(f"🏫 ToT contexts 확인: sql={bool(contexts.get('sql'))}, vector={bool(contexts.get('vector'))}, mapping={bool(contexts.get('mapping'))}")
                logger.info(f"🏫 ToT context department_filter: {tot_context.get('department_filter', 'None')}")

                # 통합 시 contexts와 tot_context 모두 전달
                final_response = self.result_integrator.integrate(results, tot_context)
            else:
                final_response = self.result_integrator.integrate(results)
            
            # 최종 응답 상세 로그
            logger.info(f"✅ 체인 처리 완료: {final_response.get('processing_type')}")
            logger.info(f"📋 최종 응답 구조: {list(final_response.keys()) if isinstance(final_response, dict) else type(final_response)}")
            
            # choices 상세 정보
            if isinstance(final_response, dict) and 'choices' in final_response:
                choices = final_response.get('choices', [])
                logger.info(f"📝 최종 Choices 수: {len(choices)}")
                for i, choice in enumerate(choices):
                    if isinstance(choice, dict):
                        message = choice.get('message', {})
                        content = message.get('content', '')
                        logger.info(f"  최종 Choice {i}: content_length={len(str(content))}")
                        if content and len(str(content)) < 2000:
                            logger.info(f"    Content: {content}")
                        else:
                            preview = str(content)[:2000] + "... (총 " + str(len(str(content))) + "자)" if len(str(content)) > 2000 else str(content)
                            logger.info(f"    Content: {preview}")
            
            return final_response
        except Exception as e:
            logger.error(f"체인 처리 실패: {e}")
            return self.result_integrator._create_fallback_response(str(e))



    def get_stats(self) -> Dict[str, Any]:
        """전체 통계 조회"""
        return {
            "chain_manager": self.performance_tracker.get_performance_stats(),
            "router": {
                "available_routes": list(self.router.route_map.keys()),
                "total_routes": len(self.router.route_map)
            },
            "processors": {
                "vector": self.vector_processor.get_stats(),
                "sql": self.sql_processor.get_stats(),
                "llm": self.llm_processor.get_stats()
            }
        }

    # 기존 인터페이스 호환성 유지
    @property
    def main_chain(self):
        """기존 main_chain 인터페이스 호환성"""
        class ChainInterface:
            def __init__(self, manager):
                self.manager = manager

            async def ainvoke(self, input_data):
                return await self.manager.process(input_data)

        return ChainInterface(self)
