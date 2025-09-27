"""
설정 관리 모듈
환경 변수를 통한 중앙화된 설정 관리
"""

import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import validator
from pathlib import Path


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # 기본 설정
    service_name: str = "llm-agent"
    debug: bool = False
    port: int = 8001
    
    # LLM 설정 (단순화)
    openai_api_key: Optional[str] = None
    default_model: str = "gpt-4o-mini"
    
    # 데이터베이스 설정
    db_host: Optional[str] = None
    db_port: int = 3306
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    db_name: Optional[str] = None
    
    # 메모리 설정
    max_history_length: int = 20
    max_conversation_turns: int = 10
    
    # ToT 설정
    tot_max_depth: int = 4
    tot_beam_width: int = 3
    tot_k_thoughts: int = 3
    tot_cost_limit: float = 30.0
    tot_timeout_seconds: int = 180
    
    # 복잡도 분석 임계값
    complexity_threshold: float = 0.4
    
    # 캐싱 설정
    enable_caching: bool = True
    cache_ttl: int = 3600  # 1시간
    
    # 로깅 설정
    log_level: str = "DEBUG"
    # Simplified log format
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # 보안 설정
    max_message_length: int = 10000
    max_messages_per_request: int = 100
    allowed_session_id_pattern: str = r'^[a-zA-Z0-9_-]+$'
    
    # 성능 설정
    max_concurrent_requests: int = 100
    request_timeout: int = 30
    
    @validator('log_level')
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'log_level must be one of {valid_levels}')
        return v.upper()
    
    @validator('port')
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError('port must be between 1 and 65535')
        return v
    
    @validator('max_history_length')
    def validate_max_history_length(cls, v):
        if v < 1 or v > 1000:
            raise ValueError('max_history_length must be between 1 and 1000')
        return v
    
    # 외부 서비스 URL 설정
    sql_query_url: str = "http://svc7999:7999/api/v1/agent"
    faiss_search_url: str = "http://svc7997:7997/search"
    curriculum_plan_url: str = "http://localhost:7996/chat"
    department_mapping_url: str = "http://department-mapping:8000/agent"
    llm_fallback_url: str = "http://svc7998:7998/agent"

    # 타임존 설정
    tz: str = "Asia/Seoul"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "allow"  # 추가 필드 허용


# 전역 설정 인스턴스
settings = Settings()

# 고정된 로그 형식 (settings 순환 참조 방지)
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# 로깅 설정 (간단화된 버전 - 오류 방지)
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",  # INFO 이상 콘솔 출력
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.FileHandler",
            "level": "DEBUG",  # DEBUG 이상 파일 기록
            "formatter": "default",
            "filename": "/home/dbs0510/AiMentor_edit/ai_modules/llm_agent-main/logs/llm-agent.log",
            "mode": "a",
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "": {
            "level": "DEBUG",  # 루트 로거를 DEBUG로 설정
            "handlers": ["console", "file"],  # 콘솔과 파일 둘 다 사용
            "propagate": False,
        },
    },
}
