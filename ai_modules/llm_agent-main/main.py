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
from exceptions import AIMentorException, ValidationError
from controller.agentController import router as agent_router

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

    try:
        from service.core.mentor_service import HybridMentorService

        # 서비스 인스턴스 생성 (통합 LangGraph 모드로 초기화)
        global_mentor_service = HybridMentorService(use_unified_langgraph=True)

        # 워밍업 완료 확인
        warmup_status = global_mentor_service.get_health_status()

        if warmup_status.get("status") == "healthy":
            logger.info("✅ 서버 시작 - 모든 핸들러 워밍업 완료")
        else:
            logger.warning(f"⚠️ 워밍업 부분 실패: {warmup_status}")

    except Exception as e:
        logger.error(f"❌ 서버 시작 워밍업 실패: {e}")
        global_mentor_service = None

    yield

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

# 전역 예외 핸들러
@app.exception_handler(AIMentorException)
async def ai_mentor_exception_handler(_: Request, exc: AIMentorException):
    logger.error(f"AI 멘토 예외: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": str(exc),
            "error_code": "AI_MENTOR_ERROR",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    )

@app.exception_handler(ValidationError)
async def validation_exception_handler(_: Request, exc: ValidationError):
    logger.error(f"검증 예외: {exc}")
    return JSONResponse(
        status_code=400,
        content={
            "error": str(exc),
            "error_code": "VALIDATION_ERROR",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(_: Request, exc: Exception):
    logger.error(f"일반 예외: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "서버 내부 오류가 발생했습니다",
            "error_code": "INTERNAL_ERROR",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    )

# 라우터 등록
app.include_router(agent_router, prefix="/api/v2", tags=["AI Mentor"])

# OpenAI API 호환 엔드포인트 (Open WebUI용)
@app.get("/v1/models")
async def get_models():
    """OpenAI API 호환 모델 목록"""
    return {
        "object": "list",
        "data": [
            {
                "id": "ai-mentor",
                "object": "model",
                "created": 1672531200,
                "owned_by": "ai-mentor",
                "permission": [],
                "root": "ai-mentor",
                "parent": None
            }
        ]
    }

# Compatibility aliases for OpenWebUI which may call baseURL/models
@app.get("/models")
async def get_models_alias():
    return await get_models()

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """OpenAI API 호환 채팅 완성"""
    try:
        # 요청 데이터 파싱
        data = await request.json()
        messages = data.get("messages", [])
        
        # 메시지를 문자열로 변환
        user_message = ""
        for msg in messages:
            if msg.get("role") == "user":
                user_message += msg.get("content", "") + "\n"

        # OpenWebUI의 내부 태스크 처리 (title, tags, follow-ups)
        text = (user_message or "").strip()
        if text:
            # 히스토리 추출
            m = re.search(r"<chat_history>\s*(.*?)\s*</chat_history>", text, flags=re.DOTALL)
            chat_hist = m.group(1).strip() if m else text

            # Title 생성 요청
            if "Generate a concise, 3-5 word title" in text or re.search(r'\{\s*"title"', text):
                title = "🤖 AI Topic" if any(k in chat_hist for k in ["인공지능", "AI"]) else "💬 Chat Summary"
                return {
                    "id": "chatcmpl-ai-mentor",
                    "object": "chat.completion",
                    "created": 1672531200,
                    "model": "ai-mentor",
                    "choices": [{"index": 0, "message": {"role": "assistant", "content": f'{{"title": "{title}"}}'}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
                }

            # Tags 생성 요청
            if "Generate 1-3 broad tags" in text or re.search(r'\{\s*"tags"', text):
                tags = ["Education", "Technology", "AI"] if "AI" in chat_hist or "인공지능" in chat_hist else ["General"]
                return {
                    "id": "chatcmpl-ai-mentor",
                    "object": "chat.completion",
                    "created": 1672531200,
                    "model": "ai-mentor",
                    "choices": [{"index": 0, "message": {"role": "assistant", "content": f'{{"tags": {tags}}}'.replace("'", '"')}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
                }

            # Follow-ups 생성 요청
            if "Suggest 3-5 relevant follow-up questions" in text or re.search(r'\{\s*"follow_ups"', text):
                followups = ["어떤 과목부터 수강하는 것이 좋을까요?", "선수과목이 있나요?", "프로젝트 과목이 있나요?"]
                return {
                    "id": "chatcmpl-ai-mentor",
                    "object": "chat.completion",
                    "created": 1672531200,
                    "model": "ai-mentor",
                    "choices": [{"index": 0, "message": {"role": "assistant", "content": f'{{"follow_ups": {followups}}}'.replace("'", '"')}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
                }

        if not user_message.strip():
            return JSONResponse(
                status_code=400,
                content={"error": "No user message provided"}
            )
        
        # AI Mentor 서비스 호출 (전역 인스턴스 우선 사용)
        global global_mentor_service
        
        if global_mentor_service is not None:
            # 이미 워밍업된 전역 인스턴스 사용
            service = global_mentor_service
        else:
            # 전역 인스턴스가 없으면 새로 생성 (fallback)
            logger.warning("전역 서비스 인스턴스가 없어 새로 생성합니다")
            from service.core.mentor_service import HybridMentorService
            service = HybridMentorService(use_unified_langgraph=True)
            global_mentor_service = service
        
        response = await service.run_agent(user_message.strip())
        
        # OpenAI 형식으로 응답 변환
        if isinstance(response, dict) and "choices" in response:
            return response
        else:
            # 기본 응답 형식
            return {
                "id": "chatcmpl-ai-mentor",
                "object": "chat.completion",
                "created": 1672531200,
                "model": "ai-mentor",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": str(response)
                        },
                        "finish_reason": "stop"
                    }
                ],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
            }
            
    except Exception as e:
        logger.error(f"채팅 완성 오류: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Internal server error: {str(e)}"}
        )

# Compatibility alias when base URL does not include /v1
@app.post("/chat/completions")
async def chat_completions_alias(request: Request):
    return await chat_completions(request)

# 루트 엔드포인트
@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "service": "AI Mentor Service",
        "version": "3.0-improved",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "main_api": "/api/v2/agent",
        "features": "/api/v2/langchain/features"
    }

# 헬스체크 엔드포인트
@app.get("/health")
async def health_check():
    """서비스 헬스 체크"""
    try:
        global global_mentor_service
        
        if global_mentor_service is not None:
            # 전역 인스턴스 사용 (이미 워밍업됨)
            health_status = global_mentor_service.get_health_status()
            # 워밍업 상태 추가
            health_status["prewarmed"] = True
        else:
            # 전역 인스턴스가 없으면 새로 생성
            from service.core.mentor_service import HybridMentorService
            service = HybridMentorService(use_unified_langgraph=True)
            health_status = service.get_health_status()
            health_status["prewarmed"] = False
            
        return health_status
    except Exception as e:
        logger.error(f"헬스 체크 실패: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "prewarmed": False,
            "timestamp": "2024-01-01T00:00:00Z"
        }


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
