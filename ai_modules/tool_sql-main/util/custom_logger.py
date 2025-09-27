"""
SQL 도구를 위한 커스텀 로깅 시스템
중요한 로그만 표시하고 ANSI 색상 코드를 제거합니다.
"""

import logging
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class ImportantLogsFilter(logging.Filter):
    """중요한 로그만 필터링하는 필터"""
    
    IMPORTANT_KEYWORDS = [
        # 에이전트 실행 관련
        "에이전트 실행",
        "에이전트 시작", 
        "에이전트 완료",
        "SQL 에이전트",
        
        # LLM 호출 관련
        "LLM 호출",
        "LLM 응답",
        "SQL 생성",
        "쿼리 생성",
        
        # 체인 실행 관련
        "체인 실행",
        "체인 시작",
        "체인 완료",
        
        # 중요한 결과
        "SQL 실행 완료",
        "요청 완료",
        "최종 결과",
        
        # 오류 관련
        "실패",
        "오류",
        "에러",
        "ERROR",
        "WARNING"
    ]
    
    def filter(self, record):
        """로그 메시지가 중요한지 판단"""
        message = record.getMessage().lower()
        
        # ERROR, WARNING 레벨은 항상 표시
        if record.levelno >= logging.WARNING:
            return True
            
        # 중요한 키워드가 포함된 경우만 표시
        for keyword in self.IMPORTANT_KEYWORDS:
            if keyword.lower() in message:
                return True
                
        return False


class CleanFormatter(logging.Formatter):
    """ANSI 색상 코드를 제거하고 깔끔하게 포맷팅하는 포매터"""
    
    def format(self, record):
        # 기본 포맷팅
        formatted = super().format(record)
        
        # ANSI 색상 코드 제거
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        cleaned = ansi_escape.sub('', formatted)
        
        # 이모지 추가 (레벨별)
        if record.levelname == 'INFO':
            if any(keyword in record.getMessage().lower() for keyword in 
                   ["에이전트 실행", "에이전트 시작", "SQL 에이전트"]):
                cleaned = f"🤖 {cleaned}"
            elif any(keyword in record.getMessage().lower() for keyword in 
                     ["llm 호출", "llm 응답", "sql 생성"]):
                cleaned = f"🧠 {cleaned}"
            elif any(keyword in record.getMessage().lower() for keyword in 
                     ["체인 실행", "체인 시작"]):
                cleaned = f"🔗 {cleaned}"
            elif any(keyword in record.getMessage().lower() for keyword in 
                     ["완료", "성공"]):
                cleaned = f"✅ {cleaned}"
            else:
                cleaned = f"ℹ️ {cleaned}"
        elif record.levelname == 'WARNING':
            cleaned = f"⚠️ {cleaned}"
        elif record.levelname == 'ERROR':
            cleaned = f"❌ {cleaned}"
        elif record.levelname == 'CRITICAL':
            cleaned = f"🚨 {cleaned}"
        elif record.levelname == 'DEBUG':
            cleaned = f"🔧 {cleaned}"
            
        return cleaned


def setup_clean_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    console_output: bool = True,
    show_only_important: bool = True
) -> logging.Logger:
    """깔끔한 로깅 시스템 설정"""
    
    # 로그 레벨 설정
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 깔끔한 포매터 설정
    formatter = CleanFormatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 필터 설정
    important_filter = ImportantLogsFilter() if show_only_important else None
    
    # 콘솔 핸들러
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        if important_filter:
            console_handler.addFilter(important_filter)
        root_logger.addHandler(console_handler)
    
    # 파일 핸들러
    if log_file:
        # 로그 디렉토리 생성
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        if important_filter:
            file_handler.addFilter(important_filter)
        root_logger.addHandler(file_handler)
    
    return root_logger


def get_clean_logger(name: str) -> logging.Logger:
    """깔끔한 로거 인스턴스 가져오기"""
    return logging.getLogger(name)


# 편의 함수들
def log_agent_start(logger: logging.Logger, agent_type: str, query: str):
    """에이전트 시작 로그"""
    logger.info(f"🤖 에이전트 실행 시작: {agent_type}")
    logger.info(f"📝 사용자 질문: {query}")


def log_agent_complete(logger: logging.Logger, agent_type: str, duration: float, success: bool):
    """에이전트 완료 로그"""
    status = "성공" if success else "실패"
    logger.info(f"🤖 에이전트 실행 완료: {agent_type} - {status} ({duration:.3f}초)")


def log_llm_call(logger: logging.Logger, prompt_type: str, response_length: int = None):
    """LLM 호출 로그"""
    logger.info(f"🧠 LLM 호출: {prompt_type}")
    if response_length:
        logger.info(f"🧠 LLM 응답 받음: {response_length}자")


def log_sql_generation(logger: logging.Logger, sql_query: str):
    """SQL 생성 로그"""
    # SQL 쿼리를 간단히 표시 (너무 길면 자름)
    display_query = sql_query[:100] + "..." if len(sql_query) > 100 else sql_query
    logger.info(f"🧠 SQL 생성 완료: {display_query}")


def log_chain_execution(logger: logging.Logger, chain_name: str, duration: float, success: bool):
    """체인 실행 로그"""
    status = "성공" if success else "실패"
    logger.info(f"🔗 체인 실행 완료: {chain_name} - {status} ({duration:.3f}초)")


def log_final_result(logger: logging.Logger, result_length: int, processing_time: float):
    """최종 결과 로그"""
    logger.info(f"✅ 최종 결과 생성 완료: {result_length}자 ({processing_time:.3f}초)")
