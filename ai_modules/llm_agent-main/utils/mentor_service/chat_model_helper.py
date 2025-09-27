"""
ChatModel 헬퍼 - LangChain 채팅 모델 검증 및 관리
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

class ChatModelHelper:
    """LangChain ChatModel 검증 및 헬퍼 유틸리티"""

    @staticmethod
    def validate_chat_model(chat_model: Any) -> bool:
        """
        ChatModel이 유효한지 검증

        Args:
            chat_model: 검증할 채팅 모델 인스턴스

        Returns:
            bool: 유효한 채팅 모델인지 여부
        """
        if not chat_model:
            logger.warning("ChatModel이 None입니다")
            return False

        # astream 메서드가 있는지 확인
        if not hasattr(chat_model, 'astream'):
            logger.warning("ChatModel에 astream 메서드가 없습니다")
            return False

        # invoke 메서드가 있는지 확인 (기본 LangChain ChatModel)
        if not hasattr(chat_model, 'invoke'):
            logger.warning("ChatModel에 invoke 메서드가 없습니다")
            return False

        logger.debug("ChatModel 검증 완료")
        return True

    @staticmethod
    def get_model_info(chat_model: Any) -> dict:
        """
        ChatModel 정보 추출

        Args:
            chat_model: 채팅 모델 인스턴스

        Returns:
            dict: 모델 정보
        """
        info = {
            "model_name": getattr(chat_model, 'model_name', 'unknown'),
            "model_type": type(chat_model).__name__,
            "has_streaming": hasattr(chat_model, 'astream'),
            "has_invoke": hasattr(chat_model, 'invoke')
        }

        # OpenAI 모델인 경우 추가 정보
        if hasattr(chat_model, 'openai_api_key'):
            info["provider"] = "OpenAI"
            info["api_key_set"] = bool(getattr(chat_model, 'openai_api_key'))

        return info