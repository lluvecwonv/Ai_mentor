"""
LangChain 기반 SQL 도구를 위한 통합 로깅 시스템
"""

import logging
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

class JsonFormatter(logging.Formatter):
    """JSON 형태로 로그를 포맷팅하는 포매터"""
    
    def format(self, record):
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # 추가 필드가 있으면 포함
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'session_id'):
            log_entry['session_id'] = record.session_id
        if hasattr(record, 'processing_time'):
            log_entry['processing_time'] = record.processing_time
        if hasattr(record, 'sql_queries'):
            log_entry['sql_queries'] = record.sql_queries
        
        return json.dumps(log_entry, ensure_ascii=False)

class ColoredFormatter(logging.Formatter):
    """컬러가 적용된 콘솔 포매터"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # 청록색
        'INFO': '\033[32m',     # 녹색
        'WARNING': '\033[33m',  # 노란색
        'ERROR': '\033[31m',    # 빨간색
        'CRITICAL': '\033[35m', # 자주색
        'RESET': '\033[0m'      # 리셋
    }
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # 레벨에 색상 적용
        record.levelname = f"{color}{record.levelname}{reset}"
        
        # 메시지에 이모지 추가
        if record.levelname.startswith('\033[32m'):  # INFO
            record.msg = f"✅ {record.msg}"
        elif record.levelname.startswith('\033[33m'):  # WARNING
            record.msg = f"⚠️ {record.msg}"
        elif record.levelname.startswith('\033[31m'):  # ERROR
            record.msg = f"❌ {record.msg}"
        elif record.levelname.startswith('\033[35m'):  # CRITICAL
            record.msg = f"🚨 {record.msg}"
        elif record.levelname.startswith('\033[36m'):  # DEBUG
            record.msg = f"🔧 {record.msg}"
        
        return super().format(record)

class PerformanceTracker:
    """성능 추적을 위한 클래스"""
    
    def __init__(self, logger_name: str):
        self.logger = logging.getLogger(logger_name)
        self.metrics = {}
    
    def start_timer(self, operation: str) -> str:
        """타이머 시작"""
        timer_id = f"{operation}_{datetime.now().timestamp()}"
        self.metrics[timer_id] = {
            "operation": operation,
            "start_time": datetime.now(),
            "end_time": None,
            "duration": None
        }
        self.logger.debug(f"⏱️ [타이머 시작] {operation}: {timer_id}")
        return timer_id
    
    def end_timer(self, timer_id: str) -> float:
        """타이머 종료"""
        if timer_id in self.metrics:
            end_time = datetime.now()
            start_time = self.metrics[timer_id]["start_time"]
            duration = (end_time - start_time).total_seconds()
            
            self.metrics[timer_id]["end_time"] = end_time
            self.metrics[timer_id]["duration"] = duration
            
            self.logger.info(f"⏱️ [타이머 종료] {self.metrics[timer_id]['operation']}: {duration:.3f}초")
            return duration
        return 0.0
    
    def get_metrics(self) -> Dict[str, Any]:
        """메트릭 조회"""
        return self.metrics

def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    json_format: bool = False,
    console_output: bool = True
) -> logging.Logger:
    """로깅 시스템 설정"""
    
    # 로그 레벨 설정
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 포매터 설정
    if json_format:
        formatter = JsonFormatter()
    else:
        formatter = ColoredFormatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # 콘솔 핸들러
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # 파일 핸들러
    if log_file:
        # 로그 디렉토리 생성
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    return root_logger

def get_logger(name: str) -> logging.Logger:
    """로거 인스턴스 가져오기"""
    return logging.getLogger(name)

def log_performance(logger: logging.Logger, operation: str, duration: float, **kwargs):
    """성능 로깅 헬퍼"""
    logger.info(f"📊 [성능] {operation}: {duration:.3f}초", extra={
        'operation': operation,
        'duration': duration,
        **kwargs
    })

def log_sql_execution(logger: logging.Logger, query: str, result: str, duration: float, **kwargs):
    """SQL 실행 로깅 헬퍼"""
    logger.info(f"🔍 [SQL 실행] 완료: {duration:.3f}초", extra={
        'query': query[:100] + '...' if len(query) > 100 else query,
        'result_length': len(result),
        'duration': duration,
        **kwargs
    })

def log_chain_execution(logger: logging.Logger, chain_name: str, input_data: Any, output_data: Any, duration: float, **kwargs):
    """체인 실행 로깅 헬퍼"""
    logger.info(f"🔗 [체인 실행] {chain_name}: {duration:.3f}초", extra={
        'chain_name': chain_name,
        'input_type': type(input_data).__name__,
        'output_type': type(output_data).__name__,
        'duration': duration,
        **kwargs
    })

# 기본 로깅 설정
def setup_default_logging():
    """기본 로깅 설정"""
    return setup_logging(
        log_level="INFO",
        log_file="logs/sql_tool.log",
        json_format=False,
        console_output=True
    )

# 성능 추적기 인스턴스
performance_tracker = PerformanceTracker("sql_tool.performance")
