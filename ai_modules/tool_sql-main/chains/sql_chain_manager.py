"""
SQL 체인 관리자
"""
import logging
from typing import Dict, Any
from langchain_core.runnables import RunnableLambda

from processors.sql_processor import SqlProcessor
from processors.result_formatter import ResultFormatter
from .callback_handlers import SqlExecutionCallbackHandler

logger = logging.getLogger(__name__)

class SqlChainManager:
    """SQL 체인 관리 클래스"""
    
    def __init__(self, sql_processor: SqlProcessor, result_formatter: ResultFormatter):
        self.sql_processor = sql_processor
        self.result_formatter = result_formatter
        self.logger = logger
        self.setup_chains()
    
    def setup_chains(self):
        """LangChain 체인 설정"""
        logger.info("🔧 [체인 설정] SQL 처리 체인 초기화 시작")
        
        # 1. SQL 에이전트 실행 체인
        self.sql_agent_chain = (
            RunnableLambda(self._execute_sql_agent)
            .with_config({"callbacks": [SqlExecutionCallbackHandler()]})
        )
        
        # 2. 마크다운 제거 체인
        self.markdown_removal_chain = (
            RunnableLambda(self._remove_markdown)
        )
        
        # 3. 결과 포맷팅 체인
        self.result_formatting_chain = (
            RunnableLambda(self._format_result)
        )
        
        # 4. 전체 처리 체인 (순차 실행)
        self.main_chain = (
            self.sql_agent_chain
            | self.markdown_removal_chain
            | self.result_formatting_chain
        )
        
        logger.info("✅ [체인 설정] SQL 처리 체인 초기화 완료")
    
    def _execute_sql_agent(self, query: str) -> Dict[str, Any]:
        """SQL 에이전트 실행 (체인용 내부 메서드)"""
        logger.info(f"🔗 [체인 1/3] SQL 에이전트 실행 시작")
        logger.info(f"🔍 [SQL] 입력 쿼리: {query}")

        # LangChain 에이전트 실행
        result = self.sql_processor.execute_with_agent(query)

        logger.info(f"📊 [SQL] 실행된 SQL 쿼리 개수: {len(result.sql_queries)}")
        if result.sql_queries:
            for i, sql_query in enumerate(result.sql_queries[:3]):  # 처음 3개만 로그
                logger.info(f"🗄️ [SQL] SQL #{i+1}: {sql_query[:200]}...")

        logger.info(f"📄 [SQL] 에이전트 응답: {result.result[:300]}...")
        logger.info(f"🔗 [체인 1/3] SQL 에이전트 실행 완료 - {'성공' if result.success else '실패'}")
        return {
            "query": result.query,
            "result": result.result,
            "sql_queries": result.sql_queries,
            "execution_time": result.execution_time,
            "success": result.success
        }
    
    def _remove_markdown(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """마크다운 제거 (체인용 내부 메서드)"""
        logger.info(f"🔗 [체인 2/3] 마크다운 제거 시작")
        
        result = data["result"]
        cleaned_result = self.result_formatter.remove_markdown(result)
        
        logger.info(f"🔗 [체인 2/3] 마크다운 제거 완료 - 결과 길이: {len(cleaned_result)}자")
        return {
            **data,
            "result": cleaned_result
        }
    
    def _format_result(self, data: Dict[str, Any]) -> str:
        """결과 포맷팅 (체인용 내부 메서드)"""
        logger.info(f"🔗 [체인 3/3] 결과 포맷팅 시작")
        
        formatted_result = self.result_formatter.format_chain_result(data)
        
        logger.info(f"🔗 [체인 3/3] 결과 포맷팅 완료 - 최종 길이: {len(formatted_result)}자")
        return formatted_result
    
    def execute_chain(self, query: str) -> str:
        """체인 실행"""
        logger.info(f"🔗 [전체 체인] 실행 시작: {query[:50]}...")
        
        result = self.main_chain.invoke(query)
        
        logger.info(f"🔗 [전체 체인] 실행 완료 - 최종 결과 길이: {len(result)}자")
        return result
