"""
리팩토링된 LangChain 기반 SQL 처리 서비스
"""
import logging
import time
from typing import Dict, Any

from util.langchainLlmClient import LangchainLlmClient
from util.dbClient import DbClient

from processors.sql_processor import SqlProcessor
from processors.result_formatter import ResultFormatter
from chains.sql_chain_manager import SqlChainManager
from monitoring.performance_monitor import PerformanceMonitor

# 로거 설정
logger = logging.getLogger(__name__)

class SqlCoreService:
    """리팩토링된 LangChain 기반 SQL 처리 서비스"""

    def __init__(self):
        self.logger = logger
        
        # 의존성 주입
        self.llm_client = LangchainLlmClient()
        self.db_client = DbClient()
        
        # 컴포넌트 초기화
        self.sql_processor = SqlProcessor(self.db_client, self.llm_client)
        self.result_formatter = ResultFormatter()
        self.performance_monitor = PerformanceMonitor()
        
        # 체인 관리자 초기화
        self.chain_manager = SqlChainManager(self.sql_processor, self.result_formatter)
        
        self.logger.info("✅ [서비스 초기화] SqlCoreService 초기화 완료")

    def create_agent(self):
        """SQL 에이전트 생성 (호환성을 위한 래퍼)"""
        self.sql_processor.create_agent()

    def execute(self, query: str) -> str:
        """LangChain 체인을 사용한 질문 처리"""
        start_time = time.time()
        self.logger.info(f"🚀 [메인 체인] 실행 시작: {query[:100]}...")
        self.logger.info(f"📝 [SQL] 전체 쿼리: {query}")

        try:
            # 체인 실행
            result = self.chain_manager.execute_chain(query)

            execution_time = time.time() - start_time
            self.performance_monitor.record_query(execution_time, True)

            self.logger.info(f"📊 [SQL] 실행 결과 길이: {len(result)} 문자")
            self.logger.info(f"📄 [SQL] 실행 결과: {result[:500]}...")  # 처음 500자만 로그
            self.logger.info(f"✅ [메인 체인] 실행 완료: {execution_time:.3f}초")
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.performance_monitor.record_query(execution_time, False)
            self.logger.error(f"❌ [메인 체인] 실행 실패: {e}")
            
            # 폴백 실행
            return self._fallback_execute(query)

    def process_query(self, query: str) -> str:
        """호환성을 위한 래퍼 메서드"""
        return self.execute(query)

    def _fallback_execute(self, query: str) -> str:
        """체인 실행 실패시 폴백 메서드"""
        self.logger.warning("⚠️ [폴백 실행] 체인 실패로 인한 폴백 모드 시작")
        
        try:
            result = self.sql_processor.execute_with_agent(query)
            if result.success:
                return self.result_formatter.remove_markdown(result.result)
            else:
                return f"SQL 처리 중 오류가 발생했습니다: {result.error_message}"
                
        except Exception as e:
            self.logger.error(f"❌ [폴백 실행] 폴백 모드도 실패: {e}")
            return f"SQL 처리 중 오류가 발생했습니다: {str(e)}"

    def get_performance_stats(self) -> Dict[str, Any]:
        """성능 통계 조회"""
        return self.performance_monitor.get_stats()

    def reset_stats(self):
        """성능 통계 초기화"""
        self.performance_monitor.reset_stats()
        self.logger.info("🔄 [통계 초기화] 성능 통계 리셋 완료")
