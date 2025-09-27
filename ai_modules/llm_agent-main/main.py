import uvicorn
import re
import logging
import logging.config
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config.settings import settings, LOGGING_CONFIG
from controller.agentController import router as agent_router

from service.core.mentor_service import HybridMentorService

# 로그 디렉토리 확인 및 생성
log_dir = Path("/home/dbs0510/AiMentor_edit/ai_modules/llm_agent-main/logs")
log_dir.mkdir(exist_ok=True)

# 커스텀 로깅 설정 적용
logging.config.dictConfig(LOGGING_CONFIG)

logger = logging.getLogger(__name__)

# 서버 시작 시 로그 기록
logger.info("🚀 AI Mentor Service 시작 - 로그 시스템 초기화 완료")
logger.debug(f"📁 로그 디렉토리: {log_dir}")
logger.info("=" * 50)

# 전역 서비스 인스턴스 (서버 시작 시 초기화)
global_mentor_service = None

@asynccontextmanager
async def lifespan(_: FastAPI):
    """서버 시작 및 종료 시 실행되는 lifespan 이벤트 핸들러"""
    # Startup
    global global_mentor_service
    logger.info("🚀 서버 시작 - 핸들러 워밍업 시작")
    # 서비스 인스턴스 생성 (통합 LangGraph 모드로 초기화)
    global_mentor_service = HybridMentorService(use_unified_langgraph=True)

    # 워밍업 완료 확인
    warmup_status = global_mentor_service.get_health_status()

    if warmup_status.get("status") == "healthy":
        logger.info("✅ 서버 시작 - 모든 핸들러 워밍업 완료")
    else:
        logger.warning(f"⚠️ 워밍업 부분 실패: {warmup_status}")


    # Shutdown
    logger.info("서버 종료")

# FastAPI 앱 생성
app = FastAPI(
    title="AI Mentor Service",
    description="LangGraph 기반 지능형 AI 멘토링 시스템",
    version="3.0-improved",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS 미들웨어
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 라우터 등록
app.include_router(agent_router, tags=["AI Mentor"])

# OpenAI API 호환 엔드포인트
@app.get("/v1/models")
async def get_models():
    """OpenAI API 호환 모델 목록"""
    return {
        "object": "list",
        "data": [{
            "id": "ai-mentor",
            "object": "model",
            "owned_by": "ai-mentor"
        }]
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """OpenAI API 호환 채팅 완성"""
    try:
        data = await request.json()
        messages = data.get("messages", [])

        # 사용자 메시지 추출
        user_message = "\n".join(msg.get("content", "") for msg in messages if msg.get("role") == "user")

        if not user_message.strip():
            return JSONResponse(status_code=400, content={"error": "No user message provided"})

        # AI Mentor 서비스 호출
        global global_mentor_service
        response = await global_mentor_service.run_agent(user_message.strip())

        # OpenAI 형식 응답
        return {
            "id": "chatcmpl-ai-mentor",
            "object": "chat.completion",
            "model": "ai-mentor",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": str(response)},
                "finish_reason": "stop"
            }]
        }

    except Exception as e:
        logger.error(f"채팅 완성 오류: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# 기본 엔드포인트
@app.get("/")
async def root():
    """서비스 정보"""
    return {
        "service": "AI Mentor Service",
        "version": "3.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """서비스 상태 확인"""
    try:
        global global_mentor_service
        if global_mentor_service:
            health_status = global_mentor_service.get_health_status()
            return {"status": "healthy", **health_status}
        else:
            return {"status": "starting"}
    except Exception as e:
        logger.error(f"헬스 체크 실패: {e}")
        return {"status": "unhealthy", "error": str(e)}


if __name__ == "__main__":
    logger.info(f"AI Mentor Service v3.0-improved 시작")
    logger.info(f"포트: {settings.port}")
    logger.info(f"디버그 모드: {settings.debug}")
    logger.info(f"🚀 서버 시작 시 자동 워밍업 활성화")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.debug,
        log_config=None,
        access_log=False
    )
