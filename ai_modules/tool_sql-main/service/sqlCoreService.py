import logging

from util.langchainLlmClient import LangchainLlmClient
from util.dbClient import DbClient
from util.utils import load_prompt, format_result

logger = logging.getLogger(__name__)

class SqlService:
    """초간단 SQL 처리 서비스"""

    def __init__(self):
        self.llm_client = LangchainLlmClient()
        self.db_client = DbClient()
        logger.info("✅ SqlService 초기화 완료")

    def execute(self, query: str) -> str:
        """SQL 쿼리 실행"""
        logger.info(f"🚀 실행: {query[:50]}...")

        try:
            # 1. 자연어 → SQL 변환
            sql = self._to_sql(query)

            # 2. SQL 실행
            result = self.db_client.execute_query(sql)

            # 3. 결과 반환
            return format_result(result)

        except Exception as e:
            logger.error(f"❌ 실패: {e}")
            return f"오류: {str(e)}"

    def _to_sql(self, query: str) -> str:
        """자연어를 SQL로 변환"""
        system_prompt = load_prompt("sql_system_prompt")

        # LLM 호출
        full_prompt = f"{system_prompt}\n\n질문: {query}\n\nSQL 쿼리:"
        response = self.llm_client.get_llm().invoke(full_prompt)
        sql = response.content.strip()

        # 정리
        if sql.startswith("```sql"):
            sql = sql.replace("```sql", "").replace("```", "").strip()
        if not sql.endswith(';'):
            sql += ';'

        logger.info(f"✅ SQL 변환: {sql}")
        return sql


# 서비스 인스턴스 생성
sql_service = SqlService()



