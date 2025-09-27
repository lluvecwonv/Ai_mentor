"""
LangChain 기반 SQL 도구 메인 애플리케이션
"""

import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from controller.sqlController import router as sql_router
from util.logger_config import setup_default_logging, get_logger

# 새로운 깔끔한 로깅 설정
from util.custom_logger import setup_clean_logging, get_clean_logger
setup_clean_logging(log_level="INFO", log_file="logs/sql_tool.log", console_output=True, show_only_important=True)
logger = get_clean_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # 시작
    logger.info("🚀 [애플리케이션] SQL 도구 서버 시작")
    # 에이전트/DB 초기화 워밍업 (콜드스타트 지연 방지)
    try:
        # controller 모듈의 지연 초기화 경로를 그대로 사용해 전역 서비스 준비
        from controller.sqlController import controller
        _ = controller._get_services()  # SanitizeService, SqlCoreService 생성 + create_agent() 호출
        logger.info("🔥 [워밍업] SqlCoreService 에이전트 초기화 완료")
    except Exception as e:
        logger.warning(f"⚠️ [워밍업] 초기화 실패(무시하고 계속 진행): {e}")
    yield
    # 종료
    logger.info("🛑 [애플리케이션] SQL 도구 서버 종료")

# FastAPI 앱 생성
app = FastAPI(
    title="LangChain SQL Tool",
    description="LangChain 기반 지능형 SQL 처리 도구",
    version="2.0.0",
    lifespan=lifespan
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(sql_router, prefix="/api/v1", tags=["SQL"])

@app.get("/")
async def root():
    """루트 엔드포인트"""
    logger.info("🌐 [루트] 메인 페이지 접근")
    return {
        "message": "LangChain SQL Tool API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/version")
async def version():
    """버전 정보"""
    return {
        "version": "2.0.0",
        "framework": "LangChain",
        "features": [
            "SQL Agent with LangChain",
            "Query Sanitization",
            "Performance Monitoring",
            "Structured Logging",
            "Chain-based Processing"
        ]
    }

if __name__ == "__main__":
    logger.info("🔧 [메인] 개발 서버 시작")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=7999,
        reload=True,
        log_level="info"
    )
