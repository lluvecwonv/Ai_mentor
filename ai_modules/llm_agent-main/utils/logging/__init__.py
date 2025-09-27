"""
로깅 유틸리티 모듈
"""

import logging
from typing import Optional

# 간단한 로깅 유틸리티 함수들
def new_request_id() -> str:
    """새 요청 ID 생성"""
    import uuid
    return str(uuid.uuid4())[:8]

def set_context(context_data: dict):
    """컨텍스트 설정 (간단 구현)"""
    pass

def clear_context():
    """컨텍스트 초기화 (간단 구현)"""
    pass

class ChainLogger:
    """체인 로거"""
    def __init__(self, name: str):
        self.logger = logging.getLogger(f"chain.{name}")

    def info(self, message: str):
        self.logger.info(message)

    def debug(self, message: str):
        self.logger.debug(message)

    def error(self, message: str):
        self.logger.error(message)

    @classmethod
    def log_chain_result(cls, result):
        """체인 결과 로깅"""
        logger = logging.getLogger("chain.result")
        logger.info(f"🔗 체인 결과: {str(result)[:100]}...")

    @classmethod
    def log_synthesis_decision(cls, processing_type, should_synthesize, has_result):
        """합성 결정 로깅"""
        logger = logging.getLogger("chain.synthesis")
        logger.info(f"🔄 합성 결정: type={processing_type}, synthesize={should_synthesize}, has_result={has_result}")

    @classmethod
    def log_synthesis_result(cls, synthesized_content, final_result):
        """합성 결과 로깅"""
        logger = logging.getLogger("chain.synthesis")
        logger.info(f"✨ 합성 완료: {str(synthesized_content)[:100]}...")

    @classmethod
    def log_synthesis_error(cls, error):
        """합성 오류 로깅"""
        logger = logging.getLogger("chain.synthesis")
        logger.error(f"❌ 합성 오류: {error}")

class QueryLogger:
    """쿼리 로거"""
    def __init__(self, name: str):
        self.logger = logging.getLogger(f"query.{name}")

    def info(self, message: str):
        self.logger.info(message)

    def debug(self, message: str):
        self.logger.debug(message)

    def error(self, message: str):
        self.logger.error(message)

    @classmethod
    def log_chain_execution_start(cls, user_message: str, session_id: str):
        """체인 실행 시작 로깅"""
        logger = logging.getLogger("query.chain")
        logger.info(f"🔗 체인 실행 시작: {user_message[:50]}... (session: {session_id})")

    @classmethod
    def log_analysis_result(cls, query_analysis, kw_list):
        """분석 결과 로깅"""
        logger = logging.getLogger("query.analysis")
        logger.info(f"📊 쿼리 분석 완료: keywords={kw_list}")

    @classmethod
    def log_expansion_context(cls, exp_ctx):
        """확장 컨텍스트 로깅"""
        logger = logging.getLogger("query.expansion")
        logger.info(f"🔍 컨텍스트 확장 완료: {str(exp_ctx)[:100]}...")

    @classmethod
    def log_routing_decision(cls, disp_agent, category, complexity, reasoning):
        """라우팅 결정 로깅"""
        logger = logging.getLogger("query.routing")
        logger.info(f"🎯 라우팅 결정: {disp_agent} (category: {category}, complexity: {complexity})")

    @classmethod
    def log_execution_plan(cls, plan):
        """실행 계획 로깅"""
        logger = logging.getLogger("query.plan")
        logger.info(f"📋 실행 계획: {str(plan)[:100]}...")

    @classmethod
    def log_chain_execution_complete(cls, processing_time):
        """체인 실행 완료 로깅"""
        logger = logging.getLogger("query.chain")
        logger.info(f"✅ 체인 실행 완료: {processing_time:.2f}초")

class SynthesisLogger:
    """합성 로거"""
    def __init__(self, name: str):
        self.logger = logging.getLogger(f"synthesis.{name}")

    def info(self, message: str):
        self.logger.info(message)

    def debug(self, message: str):
        self.logger.debug(message)

    def error(self, message: str):
        self.logger.error(message)

    @classmethod
    def log_synthesis_start(cls, prompt_length):
        """합성 시작 로깅"""
        logger = logging.getLogger("synthesis.start")
        logger.info(f"🚀 합성 시작: prompt_length={prompt_length}")

    @classmethod
    def log_handler_unavailable(cls):
        """핸들러 불가 로깅"""
        logger = logging.getLogger("synthesis.handler")
        logger.warning("⚠️ 핸들러 사용 불가")

    @classmethod
    def log_synthesis_success(cls, result_length):
        """합성 성공 로깅"""
        logger = logging.getLogger("synthesis.success")
        logger.info(f"✅ 합성 성공: result_length={result_length}")

    @classmethod
    def log_synthesis_empty(cls):
        """합성 결과 비어있음 로깅"""
        logger = logging.getLogger("synthesis.empty")
        logger.warning("⚠️ 합성 결과 비어있음")

    @classmethod
    def log_synthesis_error(cls, error):
        """합성 오류 로깅"""
        logger = logging.getLogger("synthesis.error")
        logger.error(f"❌ 합성 오류: {error}")

    @classmethod
    def log_should_synthesize_decision(cls, processing_type, should_synthesize):
        """합성 여부 결정 로깅"""
        logger = logging.getLogger("synthesis.decision")
        logger.info(f"🤔 합성 결정: type={processing_type}, should_synthesize={should_synthesize}")

# 기타 필요한 로거들
class ResultLogger:
    """결과 로거"""
    def __init__(self, name: str):
        self.logger = logging.getLogger(f"result.{name}")

    def info(self, message: str):
        self.logger.info(message)

    def debug(self, message: str):
        self.logger.debug(message)

    def error(self, message: str):
        self.logger.error(message)

class ToTLogger:
    """ToT 로거"""
    def __init__(self, name: str):
        self.logger = logging.getLogger(f"tot.{name}")

    def info(self, message: str):
        self.logger.info(message)

    def debug(self, message: str):
        self.logger.debug(message)

    def error(self, message: str):
        self.logger.error(message)

__all__ = [
    'ChainLogger',
    'QueryLogger',
    'SynthesisLogger',
    'ResultLogger',
    'ToTLogger',
    'set_context',
    'clear_context',
    'new_request_id'
]