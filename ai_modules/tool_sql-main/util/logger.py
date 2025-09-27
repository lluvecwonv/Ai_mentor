"""
초간단 로깅 시스템
"""
import logging
import sys

def setup_logging(log_level="INFO", log_file=None):
    """간단한 로깅 설정"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            *([logging.FileHandler(log_file, encoding='utf-8')] if log_file else [])
        ]
    )

def get_logger(name):
    """로거 가져오기"""
    return logging.getLogger(name)