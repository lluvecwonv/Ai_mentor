import logging
import logging.handlers
import os
from pathlib import Path

def init_logging(service_name: str = "faiss_search",
                log_dir: str = "./logs"):
    """
    FAISS 검색 서비스용 로깅 초기화
    LLM-Agent와 동일한 로그 디렉토리 사용
    """

    # 로그 디렉토리 생성
    os.makedirs(log_dir, exist_ok=True)

    # 로그 파일 경로 (공통 로그 + FAISS 전용 로그)
    log_file = os.path.join(log_dir, "faiss-search.log")
    faiss_log_file = "./faiss-search.log"

    # 로거 설정
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # 기존 핸들러 제거 (중복 방지)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    # 포맷터 설정 (LLM-Agent와 동일한 형식)
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_handler.setFormatter(formatter)

    # 파일 핸들러 생성 시도 (권한 문제 시 건너뛰기)
    try:
        # 공통 로그 파일 핸들러 (RotatingFileHandler)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=50*1024*1024,  # 50MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # FAISS 전용 로그 파일 핸들러
        faiss_file_handler = logging.handlers.RotatingFileHandler(
            faiss_log_file,
            maxBytes=50*1024*1024,  # 50MB
            backupCount=3,
            encoding='utf-8'
        )
        faiss_file_handler.setLevel(logging.DEBUG)
        faiss_file_handler.setFormatter(formatter)
        logger.addHandler(faiss_file_handler)
    except PermissionError:
        print("Warning: Cannot write to log files, using console only")

    # 콘솔 핸들러는 항상 추가
    logger.addHandler(console_handler)

    # 서비스 시작 로그
    logger.info(f"=== {service_name} 서비스 시작 ===")
    logger.info(f"공통 로그 파일: {log_file}")
    logger.info(f"FAISS 전용 로그 파일: {faiss_log_file}")

    return logger