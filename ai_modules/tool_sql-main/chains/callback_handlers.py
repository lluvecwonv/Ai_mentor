"""
콜백 핸들러들
"""
import logging
from typing import Dict, Any
from langchain_core.callbacks import BaseCallbackHandler

logger = logging.getLogger(__name__)

class SqlExecutionCallbackHandler(BaseCallbackHandler):
    """SQL 실행 과정을 추적하는 콜백 핸들러"""
    
    def __init__(self):
        self.sql_queries = []
        self.steps = []
        
    def on_agent_action(self, action, **kwargs):
        """에이전트 액션 추적"""
        logger.info(f"🔧 [SQL 에이전트] 액션 실행: {action.tool}")
        if hasattr(action, 'tool_input'):
            tool_input = action.tool_input
            if isinstance(tool_input, dict):
                for key, value in tool_input.items():
                    if isinstance(value, str) and ("select" in value.lower() or " from " in value.lower()):
                        self.sql_queries.append(value.strip())
                        logger.debug(f"🔍 [SQL 추출] {key}: {value[:100]}...")
            elif isinstance(tool_input, str) and ("select" in tool_input.lower() or " from " in tool_input.lower()):
                self.sql_queries.append(tool_input.strip())
                logger.debug(f"🔍 [SQL 추출] 직접: {tool_input[:100]}...")
    
    def on_agent_finish(self, finish, **kwargs):
        """에이전트 완료 추적"""
        logger.info(f"✅ [SQL 에이전트] 실행 완료: {len(self.sql_queries)}개 SQL 생성")
    
    def get_sql_queries(self) -> list:
        """추출된 SQL 쿼리 반환"""
        return self.sql_queries.copy()
    
    def clear_queries(self):
        """SQL 쿼리 목록 초기화"""
        self.sql_queries.clear()
