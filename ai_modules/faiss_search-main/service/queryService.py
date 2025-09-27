import logging
from typing import Optional, List, Dict
from openai import OpenAI
from pathlib import Path
from util.utils import extract_sql_query_from_llm_response

logger = logging.getLogger(__name__)


class QueryService:
    """SQL 쿼리 생성 및 실행 서비스"""

    def __init__(self, openai_client: OpenAI, db_client):
        self.llm_client = openai_client
        self.db_client = db_client
        self.prompt_path = Path(__file__).parent.parent / "prompts" / "sql_prefilter_generator.txt"
        self._load_prompt()

    def _load_prompt(self):
        """프롬프트 파일 로드"""
        try:
            with open(self.prompt_path, 'r', encoding='utf-8') as f:
                self.system_prompt = f.read()
            logger.info("✅ SQL 쿼리 프롬프트 로드 완료")
        except Exception as e:
            logger.error(f"❌ 프롬프트 파일 로드 실패: {e}")
            self.system_prompt = "SQL 쿼리를 생성하세요."

    def generate_sql(self, user_query: str) -> Optional[str]:
        """LLM으로 SQL 쿼리 생성"""
        logger.info(f"🔍 [QueryService] SQL 쿼리 생성 시작: '{user_query}'")

        try:
            response = self.llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"다음 쿼리를 분석하여 SQL 사전 필터링 쿼리를 생성하세요: {user_query}"}
                ],
                temperature=0.1,
                max_tokens=1000
            )

            result_text = response.choices[0].message.content.strip()
            logger.info(f"📝 [QueryService] LLM 응답: {result_text}")

            return extract_sql_query_from_llm_response(result_text)

        except Exception as e:
            logger.error(f"❌ [QueryService] SQL 쿼리 생성 실패: {e}")
            return None

    def get_filtered_courses(self, user_query: str) -> List[Dict]:
        """SQL 쿼리 생성 → 실행 → 벡터 데이터와 함께 반환"""
        # 1. SQL 쿼리 생성
        sql_query = self.generate_sql(user_query)
        if not sql_query:
            logger.info("ℹ️ [QueryService] SQL 필터링 불필요")
            return []

        # 2. SQL 실행하여 벡터 데이터 포함해서 가져오기
        return self._execute_sql_with_vectors(sql_query)

    def _execute_sql_with_vectors(self, sql_query: str) -> List[Dict]:
        """SQL 실행하여 벡터 데이터 포함한 강의 목록 반환"""
        try:
            if not self.db_client.ensure_connection():
                return []

            with self.db_client.connection.cursor() as cursor:
                # 벡터 데이터도 함께 가져오는 강화된 SQL
                enhanced_sql = f"""
                SELECT id, name, department_full_name, department, professor, credits,
                       schedule, location, delivery_mode, gpt_description, vector
                FROM jbnu_class_gpt
                WHERE id IN (
                    SELECT DISTINCT id FROM ({sql_query}) as filtered
                )
                """

                logger.info(f"🔍 [QueryService] SQL 실행: {enhanced_sql}")
                cursor.execute(enhanced_sql)
                results = cursor.fetchall()

                logger.info(f"📊 [QueryService] 필터링 결과: {len(results)}개 강의")

                # 결과 로깅
                for i, row in enumerate(results):
                    course_id = row.get('id')
                    name = row.get('name', 'N/A')
                    dept = row.get('department_full_name', 'N/A')
                    logger.info(f"   #{i+1}: ID={course_id}, 과목명={name}, 학과={dept}")

                return results

        except Exception as e:
            logger.error(f"❌ [QueryService] SQL 실행 실패: {e}")
            return []