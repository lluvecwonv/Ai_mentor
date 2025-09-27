"""
Base handler interface for query processing
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class BaseQueryHandler(ABC):
    """Query handler base class"""

    def __init__(self):
        self.logger = logger

    @abstractmethod
    async def handle(self, user_message: str, query_analysis: Dict, **kwargs) -> str:
        """
        Process the user query and return response content

        Args:
            user_message: User's input message
            query_analysis: Analysis results from QueryAnalyzer
            **kwargs: Additional parameters (state, session_id, etc.)

        Returns:
            str: Response content
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the handler is available for use"""
        pass

    def get_fallback_message(self) -> str:
        """Return fallback message when handler is not available"""
        return "해당 서비스를 사용할 수 없습니다."