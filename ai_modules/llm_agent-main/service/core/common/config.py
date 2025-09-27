from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import os
import json
from pathlib import Path


@dataclass
class ServiceConfig:
    """서비스 전역 설정"""

    # LangGraph 설정
    langgraph_timeout: int = 600
    langgraph_max_iterations: int = 10
    langgraph_checkpointer_enabled: bool = True

    # ToT (Tree of Thoughts) 설정
    tot_timeout_seconds: int = 30
    tot_max_workers: int = 4
    tot_max_thoughts: int = 3
    tot_max_depth: int = 3

    # 메모리 설정
    memory_ttl_seconds: int = 600
    memory_max_size: int = 1000
    memory_cache_expiry_hours: int = 24

    # 재시도 설정
    max_retry_count: int = 3
    retry_delay_seconds: int = 1
    exponential_backoff: bool = True

    # 병렬 처리 설정
    parallel_limit: int = 3
    thread_pool_size: int = 10

    # 캐싱 설정
    enable_cache: bool = True
    cache_ttl_minutes: int = 30
    max_cache_size_mb: int = 100

    # 로깅 설정
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    enable_performance_logging: bool = True

    # 모델 설정
    default_model: str = "gpt-4"
    fallback_model: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    max_tokens: int = 4096

    # API 설정
    openai_api_timeout: int = 120
    openai_api_max_retries: int = 2

    # 헬스체크 설정
    health_check_interval: int = 60
    health_check_timeout: int = 10

    @classmethod
    def from_env(cls) -> "ServiceConfig":
        """환경 변수에서 설정 로드"""
        config_dict = {}

        # 환경 변수를 설정 필드로 매핑
        env_mapping = {
            "LANGGRAPH_TIMEOUT": "langgraph_timeout",
            "LANGGRAPH_MAX_ITERATIONS": "langgraph_max_iterations",
            "TOT_TIMEOUT": "tot_timeout_seconds",
            "TOT_MAX_WORKERS": "tot_max_workers",
            "MEMORY_TTL": "memory_ttl_seconds",
            "MAX_RETRY_COUNT": "max_retry_count",
            "PARALLEL_LIMIT": "parallel_limit",
            "LOG_LEVEL": "log_level",
            "DEFAULT_MODEL": "default_model",
            "TEMPERATURE": "temperature",
            "MAX_TOKENS": "max_tokens",
        }

        for env_key, config_key in env_mapping.items():
            value = os.environ.get(env_key)
            if value is not None:
                # 타입 변환
                if config_key in ["langgraph_timeout", "tot_timeout_seconds", "memory_ttl_seconds",
                                   "max_retry_count", "parallel_limit", "max_tokens"]:
                    config_dict[config_key] = int(value)
                elif config_key in ["temperature"]:
                    config_dict[config_key] = float(value)
                elif config_key in ["langgraph_checkpointer_enabled", "enable_cache",
                                     "exponential_backoff", "enable_performance_logging"]:
                    config_dict[config_key] = value.lower() == "true"
                else:
                    config_dict[config_key] = value

        return cls(**config_dict)

    @classmethod
    def from_file(cls, file_path: str) -> "ServiceConfig":
        """JSON 파일에서 설정 로드"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {file_path}")

        with open(path, "r", encoding="utf-8") as f:
            config_dict = json.load(f)

        return cls(**config_dict)

    def to_dict(self) -> Dict[str, Any]:
        """설정을 딕셔너리로 변환"""
        return {
            key: getattr(self, key)
            for key in self.__dataclass_fields__
        }

    def save_to_file(self, file_path: str) -> None:
        """설정을 JSON 파일로 저장"""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)


@dataclass
class DatabaseConfig:
    """데이터베이스 설정"""

    # PostgreSQL 설정
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_database: str = "llm_service"
    postgres_user: str = "postgres"
    postgres_password: str = ""

    # 연결 풀 설정
    pool_min_size: int = 5
    pool_max_size: int = 20
    pool_timeout: int = 30

    # Redis 설정
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """환경 변수에서 데이터베이스 설정 로드"""
        return cls(
            postgres_host=os.environ.get("POSTGRES_HOST", "localhost"),
            postgres_port=int(os.environ.get("POSTGRES_PORT", "5432")),
            postgres_database=os.environ.get("POSTGRES_DB", "llm_service"),
            postgres_user=os.environ.get("POSTGRES_USER", "postgres"),
            postgres_password=os.environ.get("POSTGRES_PASSWORD", ""),
            redis_host=os.environ.get("REDIS_HOST", "localhost"),
            redis_port=int(os.environ.get("REDIS_PORT", "6379")),
            redis_db=int(os.environ.get("REDIS_DB", "0")),
            redis_password=os.environ.get("REDIS_PASSWORD"),
        )


class ConfigManager:
    """설정 관리자"""

    _instance: Optional["ConfigManager"] = None
    _service_config: Optional[ServiceConfig] = None
    _database_config: Optional[DatabaseConfig] = None

    def __new__(cls) -> "ConfigManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def service(self) -> ServiceConfig:
        """서비스 설정 반환"""
        if self._service_config is None:
            # 우선순위: 환경변수 > 파일 > 기본값
            config_file = os.environ.get("SERVICE_CONFIG_FILE")
            if config_file and Path(config_file).exists():
                self._service_config = ServiceConfig.from_file(config_file)
            else:
                self._service_config = ServiceConfig.from_env()
        return self._service_config

    @property
    def database(self) -> DatabaseConfig:
        """데이터베이스 설정 반환"""
        if self._database_config is None:
            self._database_config = DatabaseConfig.from_env()
        return self._database_config

    def reload(self) -> None:
        """설정 재로드"""
        self._service_config = None
        self._database_config = None

    def set_service_config(self, config: ServiceConfig) -> None:
        """서비스 설정 설정"""
        self._service_config = config

    def set_database_config(self, config: DatabaseConfig) -> None:
        """데이터베이스 설정 설정"""
        self._database_config = config


# 싱글톤 인스턴스
config_manager = ConfigManager()