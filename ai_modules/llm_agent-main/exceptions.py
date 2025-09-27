"""
커스텀 예외 클래스들
시스템 전반에서 사용되는 예외들을 정의
"""


class AIMentorException(Exception):
    """AI 멘토 서비스 기본 예외"""
    pass


class QueryAnalysisError(AIMentorException):
    """쿼리 분석 오류"""
    pass


class VectorSearchError(AIMentorException):
    """벡터 검색 오류"""
    pass


class SQLQueryError(AIMentorException):
    """SQL 쿼리 오류"""
    pass


class DepartmentMappingError(AIMentorException):
    """학과 매핑 오류"""
    pass


class LLMServiceError(AIMentorException):
    """LLM 서비스 오류"""
    pass


class ChainProcessingError(AIMentorException):
    """체인 처리 오류"""
    pass


class ConversationMemoryError(AIMentorException):
    """대화 메모리 오류"""
    pass


class ValidationError(AIMentorException):
    """입력 검증 오류"""
    pass


class ConfigurationError(AIMentorException):
    """설정 오류"""
    pass


class RateLimitError(AIMentorException):
    """요청 제한 오류"""
    pass


class TimeoutError(AIMentorException):
    """타임아웃 오류"""
    pass
