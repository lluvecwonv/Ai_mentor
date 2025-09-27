"""
SQL 처리 핵심 로직
"""
import logging
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass

from util.dbClient import DbClient
from util.langchainLlmClient import LangchainLlmClient
from util.prompt_loader import PromptLoader
from langchain_community.agent_toolkits import create_sql_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.utilities import SQLDatabase
import os

# Custom logger 사용
try:
    from util.custom_logger import get_clean_logger
    logger = get_clean_logger(__name__)
except:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

@dataclass
class SqlExecutionResult:
    """SQL 실행 결과를 담는 데이터 클래스"""
    query: str
    result: str
    sql_queries: list
    execution_time: float
    success: bool
    error_message: Optional[str] = None

class SqlProcessor:
    """SQL 처리 핵심 로직"""
    
    def __init__(self, db_client: DbClient, llm_client: LangchainLlmClient):
        self.db_client = db_client
        self.llm_client = llm_client
        self.agent_executor = None
        self.prompt_loader = PromptLoader()
        
    def create_agent(self):
        """SQL 에이전트 생성"""
        logger.info("🔧 [에이전트 생성] SQL 에이전트 초기화 시작")
        
        try:
            # 커스텀 프롬프트 로드
            system_prompt = self.prompt_loader.load_sql_system_prompt()
            
            # LangChain SQLDatabase 생성 (환경변수 기반 연결)
            host = os.getenv("DB_HOST", "210.117.181.113")
            port = os.getenv("DB_PORT", "3313")
            user = os.getenv("DB_USER", "root")
            password = os.getenv("VECTOR_DB_PASSWORD") or os.getenv("DB_PASSWORD", "vmfhaltmskdls123")
            database = os.getenv("DB_NAME", "nll")

            db_url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"

            # SQLDatabase 인스턴스 생성
            db = SQLDatabase.from_uri(db_url)

            # 커스텀 프롬프트로 에이전트 생성
            self.agent_executor = create_sql_agent(
                llm=self.llm_client.llm,
                db=db,
                agent_type="openai-tools",
                verbose=True,  # SQL 생성 과정 보기 위해 활성화
                return_intermediate_steps=True,  # 중간 단계 반환 활성화
                handle_parsing_errors=True,
                max_iterations=10,
                max_execution_time=30,
                system_message=system_prompt,  # 커스텀 프롬프트 적용
                include_tables=["jbnu_class", "jbnu_department", "jbnu_college"]  # 사용할 테이블 제한
            )
            logger.info("✅ [에이전트 생성] SQL 에이전트 초기화 완료")
        except Exception as e:
            logger.error(f"❌ [에이전트 생성] 초기화 실패: {e}")
            raise
    
    def execute_with_agent(self, query: str) -> SqlExecutionResult:
        """LangChain 에이전트를 사용한 SQL 실행"""
        start_time = time.time()
        logger.info(f"🚀 [SQL 에이전트] 실행 시작: {query[:100]}...")
        
        try:
            if not self.agent_executor:
                self.create_agent()
            
            # 에이전트 실행 (타임아웃 적용)
            logger.info(f"🔍 [SQL 에이전트] 쿼리 실행 시작: '{query}'")
            logger.info(f"📝 [SQL DEBUG] 전체 입력 쿼리: {query}")

            res = self.agent_executor.invoke(
                {"input": query},
                config={
                    "max_execution_time": 5,
                    "callbacks": []
                }
            )

            logger.info(f"🔧 [SQL DEBUG] Agent 응답 타입: {type(res)}")
            logger.info(f"🔧 [SQL DEBUG] Agent 응답 키: {list(res.keys()) if isinstance(res, dict) else 'not dict'}")
            
            execution_time = time.time() - start_time
            
            # 결과 파싱
            output = res.get("output") if isinstance(res, dict) else str(res)

            # 중간 단계에서 실제 SQL 쿼리 추출
            intermediate_steps = res.get("intermediate_steps", []) if isinstance(res, dict) else []
            sql_queries = self._extract_sql_from_steps(intermediate_steps)

            # intermediate_steps 자체도 로깅
            logger.info(f"🔧 [SQL DEBUG] intermediate_steps 개수: {len(intermediate_steps)}")
            if intermediate_steps:
                for i, step in enumerate(intermediate_steps[:3]):  # 처음 3개만
                    logger.info(f"🔧 [SQL DEBUG] Step {i}: {str(step)[:200]}...")

            # SQL 쿼리 로깅
            if sql_queries:
                logger.info(f"💡 [생성된 SQL] 총 {len(sql_queries)}개 쿼리:")
                for i, sql in enumerate(sql_queries, 1):
                    logger.info(f"   🔍 [SQL {i}] {sql}")
            else:
                logger.warning("⚠️ [SQL 생성] 생성된 SQL 쿼리를 찾을 수 없음")
                # output에서 SQL 패턴 찾기 시도
                import re
                sql_pattern = r"(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER).*?(?:;|$|\n)"
                found_sqls = re.findall(sql_pattern, output, re.IGNORECASE | re.DOTALL)
                if found_sqls:
                    logger.info(f"📝 [SQL 패턴] output에서 SQL 유사 패턴 발견: {len(found_sqls)}개")
                    for i, sql in enumerate(found_sqls[:3]):
                        logger.info(f"   📝 [패턴 {i+1}] {sql[:100]}...")

            # 결과 요약 로깅
            logger.info(f"📋 [최종 결과] {len(output)}자: {output[:200]}{'...' if len(output) > 200 else ''}")
            
            logger.info(f"✅ [SQL 에이전트] 실행 완료: {execution_time:.3f}초")
            
            return SqlExecutionResult(
                query=query,
                result=output,
                sql_queries=sql_queries,
                execution_time=execution_time,
                success=True
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ [SQL 에이전트] 실행 실패: {e}")
            
            return SqlExecutionResult(
                query=query,
                result=f"SQL 실행 중 오류가 발생했습니다: {str(e)}",
                sql_queries=[],
                execution_time=execution_time,
                success=False,
                error_message=str(e)
            )

    def _extract_sql_from_steps(self, intermediate_steps: list) -> list:
        """중간 단계에서 실제 실행된 SQL 쿼리 추출"""
        sql_queries = []

        for step in intermediate_steps:
            # 각 스텝은 (agent_action, observation) 튜플
            if len(step) >= 2:
                agent_action, observation = step[0], step[1]

                # tool_input에서 SQL 쿼리 찾기
                if hasattr(agent_action, 'tool_input') and isinstance(agent_action.tool_input, dict):
                    query = agent_action.tool_input.get('query', '')
                    if query and query.strip().upper().startswith(('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER')):
                        sql_queries.append(query.strip())

                # tool 이름이 sql 관련인 경우 추가 정보 로깅
                if hasattr(agent_action, 'tool'):
                    tool_name = getattr(agent_action, 'tool', '')
                    if 'sql' in tool_name.lower():
                        logger.info(f"🔧 [도구 사용] {tool_name}")

        return sql_queries

    def _extract_sql_queries(self, output: str) -> list:
        """출력에서 SQL 쿼리를 추출합니다"""
        import re
        
        sql_queries = []
        
        # SQL 쿼리 패턴들 (일반적인 SQL 키워드로 시작하는 패턴)
        sql_patterns = [
            r'SELECT\s+.*?(?:;|$|\n\n)',
            r'INSERT\s+.*?(?:;|$|\n\n)',
            r'UPDATE\s+.*?(?:;|$|\n\n)',
            r'DELETE\s+.*?(?:;|$|\n\n)',
            r'CREATE\s+.*?(?:;|$|\n\n)',
            r'DROP\s+.*?(?:;|$|\n\n)',
            r'ALTER\s+.*?(?:;|$|\n\n)'
        ]
        
        # 각 패턴으로 쿼리 추출
        for pattern in sql_patterns:
            matches = re.findall(pattern, output, re.IGNORECASE | re.DOTALL)
            for match in matches:
                # 쿼리 정리 (공백 및 개행 정리)
                cleaned_query = ' '.join(match.strip().split())
                if cleaned_query and len(cleaned_query) > 10:  # 너무 짧은 쿼리 제외
                    sql_queries.append(cleaned_query)
        
        # 중복 제거
        sql_queries = list(dict.fromkeys(sql_queries))
        
        logger.debug(f"추출된 SQL 쿼리 수: {len(sql_queries)}")
        return sql_queries
    
