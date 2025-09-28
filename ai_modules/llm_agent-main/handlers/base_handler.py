"""
Base handler interface for query processing
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class BaseQueryHandler(ABC):
    """Query handler base class"""

    def __init__(self):
        self.logger = logger

    @abstractmethod
    async def handle(self, user_message: str, query_analysis: Dict, **kwargs) -> Dict[str, Any]:
        """
        Process the user query and return standardized response

        Args:
            user_message: User's input message
            query_analysis: Analysis results from QueryAnalyzer
            **kwargs: Additional parameters (state, session_id, etc.)

        Returns:
            Dict with standardized structure:
            {
                "agent_type": str,      # 에이전트 타입 (예: "department", "vector_search")
                "result": Any,          # 실제 결과 데이터
                "metadata": Dict,       # 메타데이터 (confidence, source 등)
                "normalized": str,      # 다음 에이전트에 전달할 정규화된 텍스트
                "display": str,         # 사용자에게 보여줄 텍스트
                "success": bool         # 처리 성공 여부
            }
        """
        pass

    def create_response(self,
                       agent_type: str,
                       result: Any,
                       normalized: str = None,
                       display: str = None,
                       metadata: Dict = None,
                       success: bool = True) -> Dict[str, Any]:
        """
        Create standardized response structure

        Args:
            agent_type: Type of agent
            result: The actual result data
            normalized: Normalized text for next agent (optional)
            display: Display text for user (optional)
            metadata: Additional metadata (optional)
            success: Whether the processing was successful

        Returns:
            Standardized response dictionary
        """
        return {
            "agent_type": agent_type,
            "result": result,
            "metadata": metadata or {},
            "normalized": normalized or str(result),
            "display": display or str(result),
            "success": success
        }

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the handler is available for use"""
        pass

    def get_fallback_message(self) -> str:
        """Return fallback message when handler is not available"""
        return "해당 서비스를 사용할 수 없습니다."