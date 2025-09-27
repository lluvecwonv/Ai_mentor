from typing import Any, Dict, Optional
import logging
import traceback
from datetime import datetime
import uuid


logger = logging.getLogger(__name__)


class ServiceError(Exception):
    """서비스 레이어 표준 예외 클래스"""

    def __init__(
        self,
        message: str,
        error_type: str = "service_error",
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500
    ):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.details = details or {}
        self.status_code = status_code


class ValidationError(ServiceError):
    """입력 검증 실패 예외"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "validation_error", details, 400)


class ProcessingError(ServiceError):
    """처리 중 발생한 예외"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "processing_error", details, 500)


class TimeoutError(ServiceError):
    """타임아웃 예외"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "timeout_error", details, 504)


class ErrorHandler:
    """통합 에러 처리 핸들러"""

    @staticmethod
    def create_error_response(
        error: Exception,
        request_id: Optional[str] = None,
        include_trace: bool = False
    ) -> Dict[str, Any]:
        """
        예외를 표준 에러 응답으로 변환

        Args:
            error: 발생한 예외
            request_id: 요청 ID
            include_trace: 스택 트레이스 포함 여부

        Returns:
            표준 에러 응답
        """
        # ServiceError 타입인 경우
        if isinstance(error, ServiceError):
            response = {
                "id": request_id or f"error-{uuid.uuid4().hex[:8]}",
                "object": "error",
                "created": int(datetime.now().timestamp()),
                "error": {
                    "type": error.error_type,
                    "message": error.message,
                    "details": error.details,
                    "status_code": error.status_code
                }
            }
        # 일반 예외인 경우
        else:
            response = {
                "id": request_id or f"error-{uuid.uuid4().hex[:8]}",
                "object": "error",
                "created": int(datetime.now().timestamp()),
                "error": {
                    "type": "internal_error",
                    "message": str(error),
                    "details": {},
                    "status_code": 500
                }
            }

        # 스택 트레이스 추가
        if include_trace:
            response["error"]["trace"] = traceback.format_exc()

        return response

    @staticmethod
    def create_openai_error_response(
        error: Exception,
        model: str = "gpt-4",
        fallback_message: str = "죄송합니다. 요청을 처리하는 중 오류가 발생했습니다."
    ) -> Dict[str, Any]:
        """
        OpenAI 호환 에러 응답 생성

        Args:
            error: 발생한 예외
            model: 모델 이름
            fallback_message: 폴백 메시지

        Returns:
            OpenAI 호환 에러 응답
        """
        error_message = fallback_message

        if isinstance(error, ServiceError):
            error_message = f"오류: {error.message}"
        elif isinstance(error, TimeoutError):
            error_message = "요청 처리 시간이 초과되었습니다. 잠시 후 다시 시도해주세요."
        elif isinstance(error, ValidationError):
            error_message = f"입력 검증 실패: {error.message}"

        response = {
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "created": int(datetime.now().timestamp()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": error_message
                    },
                    "finish_reason": "error"
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }
        }

        # 에러 정보 추가
        if isinstance(error, ServiceError):
            response["error"] = {
                "type": error.error_type,
                "message": error.message,
                "details": error.details
            }

        return response

    @staticmethod
    def log_error(
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        level: str = "error"
    ) -> None:
        """
        에러를 로깅

        Args:
            error: 발생한 예외
            context: 추가 컨텍스트 정보
            level: 로그 레벨 (debug, info, warning, error, critical)
        """
        log_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {}
        }

        # ServiceError인 경우 추가 정보 포함
        if isinstance(error, ServiceError):
            log_data["service_error_type"] = error.error_type
            log_data["service_error_details"] = error.details

        # 로그 레벨에 따른 로깅
        log_func = getattr(logger, level, logger.error)
        log_func(f"Error occurred: {log_data}", exc_info=True)

    @staticmethod
    def create_fallback_response(
        message: str = "서비스를 일시적으로 사용할 수 없습니다.",
        processing_type: str = "fallback"
    ) -> Dict[str, Any]:
        """
        폴백 응답 생성

        Args:
            message: 폴백 메시지
            processing_type: 처리 타입

        Returns:
            폴백 응답
        """
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "created": int(datetime.now().timestamp()),
            "model": "fallback",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": message
                    },
                    "finish_reason": "fallback"
                }
            ],
            "metadata": {
                "processing_type": processing_type,
                "is_fallback": True
            }
        }