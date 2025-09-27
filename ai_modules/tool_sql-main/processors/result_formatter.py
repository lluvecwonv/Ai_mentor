"""
결과 포맷팅 로직
"""
import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class ResultFormatter:
    """결과 포맷팅 클래스"""
    
    def __init__(self):
        self.logger = logger
    
    def remove_markdown(self, text: str) -> str:
        """마크다운 제거"""
        logger.debug("🔧 [마크다운 제거] 처리 시작")
        
        # **텍스트** → 텍스트 변환
        cleaned_text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        
        logger.debug(f"🔧 [마크다운 제거] 처리 완료: {len(text)} → {len(cleaned_text)} 문자")
        return cleaned_text
    
    
    def add_sql_debug_info(self, result: str, sql_queries: List[str]) -> str:
        """SQL 디버그 정보 추가"""
        if not sql_queries:
            return result
        
        debug_block = "\n\n[SQL_DEBUG]\n" + "\n---\n".join(sql_queries)
        result_with_debug = f"{result}{debug_block}"
        
        logger.debug(f"🔍 [SQL 디버그] {len(sql_queries)}개 SQL 쿼리 정보 추가")
        return result_with_debug
    
    def format_chain_result(self, data: Dict[str, Any]) -> str:
        """체인 결과 포맷팅"""
        logger.debug("🔧 [결과 포맷팅] 처리 시작")
        
        result = data["result"]
        sql_queries = data.get("sql_queries", [])
        
        # SQL 디버그 정보 추가
        if sql_queries:
            result = self.add_sql_debug_info(result, sql_queries)
        
        logger.debug("✅ [결과 포맷팅] 처리 완료")
        return result
