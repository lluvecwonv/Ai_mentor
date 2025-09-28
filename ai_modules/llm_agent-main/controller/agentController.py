from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse
import logging
import json

from service.core.mentor_service import HybridMentorService
from models.validation import RequestBody, ErrorResponse
from utils.controller_utils import strip_markdown, process_curriculum_graph
from exceptions import AIMentorException, ValidationError

router = APIRouter()

# LangGraph 전용 모드로 간소화
hybrid_service = HybridMentorService(use_unified_langgraph=True)
logger = logging.getLogger(__name__)


@router.post("/agent", response_model=dict)
async def agent_api(request_body: RequestBody):
    """메인 에이전트 API (스트리밍 지원)"""
    session_id = request_body.session_id or "default"
    stream = getattr(request_body, 'stream', False)
    logger.info(f"🚀 /agent endpoint called for session: {session_id}, stream: {stream}")

    try:
        # 사용자 메시지 추출
        user_message = _extract_user_message(request_body.messages)

        # AI 멘토 서비스 실행
        history = await hybrid_service.run_agent(user_message, session_id)

        # 응답 처리
        content = _process_response(history, request_body)

        # 스트리밍 요청인 경우
        if stream:
            return _create_streaming_response(content)

        # 일반 응답
        return JSONResponse({
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop"
            }]
        })

    except ValidationError as e:
        logger.error(f"입력 검증 오류: {e}")
        return _error_response(400, "VALIDATION_ERROR", str(e))
    except AIMentorException as e:
        logger.error(f"AI 멘토 서비스 오류: {e}")
        return _error_response(500, "SERVICE_ERROR", str(e))
    except Exception as e:
        logger.error(f"예상치 못한 오류: {e}")
        return _error_response(500, "INTERNAL_ERROR", str(e))


def _extract_user_message(messages):
    """사용자 메시지 추출"""
    for msg in messages:
        if msg.role == "user":
            return msg.content
    return ""


def _process_response(history: dict, request_body: RequestBody) -> str:
    """응답 처리 로직"""
    # OpenAI 호환 응답 처리
    if "choices" in history and len(history["choices"]) > 0:
        content = history["choices"][0]["message"]["content"]
        step = {"tool_name": "LANGGRAPH_RESPONSE"}
    else:
        step = history.get("steps", [{}])[-1] if "steps" in history else {}
        content = step.get("tool_response", "응답을 생성할 수 없습니다.")

    # 커리큘럼 그래프 처리
    if step.get("tool_name") == "CURRICULUM_RECOMMEND":
        content = process_curriculum_graph(content)

    # 포맷 처리
    if request_body.format == "plain" or step.get("tool_name") == "JBNU_SQL":
        content = strip_markdown(content)

    return content


def _create_streaming_response(content: str):
    """스트리밍 응답 생성"""
    async def generate_stream():
        # 진행 상황 메시지들
        progress_messages = [
            "🤔 생각중입니다...",
            "\n\n📋 분석하고 검색하고 있습니다...",
            "\n\n✅ 처리 완료! 답변을 준비하고 있습니다...\n\n"
        ]

        for msg in progress_messages:
            chunk = {
                "choices": [{
                    "index": 0,
                    "delta": {"content": msg},
                    "finish_reason": None
                }]
            }
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

        # 실제 답변 스트리밍
        words = content.split()
        for i, word in enumerate(words):
            chunk = {
                "choices": [{
                    "index": 0,
                    "delta": {"content": word + " "},
                    "finish_reason": "stop" if i == len(words) - 1 else None
                }]
            }
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


def _error_response(status_code: int, error_code: str, message: str) -> JSONResponse:
    """에러 응답 생성"""
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            error=message,
            error_code=error_code
        ).model_dump()
    )


# === 세션 관리 ===
@router.get("/session/{session_id}/summary")
async def get_session_summary(session_id: str):
    """세션 요약 조회"""
    try:
        stats = hybrid_service.get_session_info(session_id)
        session_info = stats.get('session_info', {})
        summary = f"대화 요약: {session_info.get('total_messages', 0)}개 메시지, 주제: {session_info.get('current_topic', 'None')}"
        return JSONResponse({
            "session_id": session_id,
            "summary": summary,
            "stats": stats
        })
    except Exception as e:
        logger.error(f"세션 요약 조회 실패: {e}")
        return _error_response(500, "SESSION_SUMMARY_ERROR", str(e))


@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """세션 초기화"""
    try:
        success = hybrid_service.clear_session_history(session_id)
        if success:
            return JSONResponse({
                "session_id": session_id,
                "message": "Session history cleared successfully"
            })
        else:
            return _error_response(500, "SESSION_CLEAR_ERROR", "세션 초기화 실패")
    except Exception as e:
        logger.error(f"세션 초기화 실패: {e}")
        return _error_response(500, "SESSION_CLEAR_ERROR", str(e))


