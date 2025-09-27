"""
AI 멘토 에이전트 컨트롤러 - 리팩토링된 버전
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse
import logging
import json

from service.core.mentor_service import HybridMentorService
import os
from models.validation import RequestBody, ChainRequest, AgentRequest, ErrorResponse
from utils.response_formatters import strip_markdown, format_sse
from utils.course_parser import parse_course_sections_with_preamble
from utils.graph_generator import generate_graph_base64
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

    # 스트리밍 요청인 경우
    if stream:
        return await _handle_streaming_request(request_body, session_id)

    # 일반 요청 처리
    try:
        # 메시지에서 사용자 입력 추출
        user_message = ""
        messages = [{"role": msg.role, "content": msg.content} for msg in request_body.messages]

        for msg in messages:
            if msg.get("role") == "user":
                user_message = msg.get("content", "")

        # AI 멘토 서비스 실행
        history = await hybrid_service.run_agent(user_message, session_id)

        # 응답 처리
        content = _process_response(history, request_body)

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


async def _handle_streaming_request(request_body: RequestBody, session_id: str):
    """스트리밍 요청 처리"""
    logger.info(f"🌊 Streaming request for session: {session_id}")

    async def generate_stream():
        try:
            # 메시지에서 사용자 입력 추출
            user_message = ""
            messages = [{"role": msg.role, "content": msg.content} for msg in request_body.messages]

            for msg in messages:
                if msg.get("role") == "user":
                    user_message = msg.get("content", "")

            # 즉시 "생각중입니다" 메시지 전송
            thinking_chunk = {
                "choices": [{
                    "index": 0,
                    "delta": {"content": "🤔 생각중입니다..."},
                    "finish_reason": None
                }]
            }
            yield f"data: {json.dumps(thinking_chunk, ensure_ascii=False)}\n\n"

            # 계획 수립 메시지
            planning_chunk = {
                "choices": [{
                    "index": 0,
                    "delta": {"content": "\n\n📋 분석하고 검색하고 있습니다..."},
                    "finish_reason": None
                }]
            }
            yield f"data: {json.dumps(planning_chunk, ensure_ascii=False)}\n\n"

            # AI 멘토 서비스 실행
            history = await hybrid_service.run_agent(user_message, session_id)

            # 응답 처리
            content = _process_response(history, request_body)

            # 완료 메시지
            ready_chunk = {
                "choices": [{
                    "index": 0,
                    "delta": {"content": "\n\n✅ 처리 완료! 답변을 준비하고 있습니다...\n\n"},
                    "finish_reason": None
                }]
            }
            yield f"data: {json.dumps(ready_chunk, ensure_ascii=False)}\n\n"

            # 스트리밍 형태로 응답 전송 (단어별로 분할)
            words = content.split()
            for i, word in enumerate(words):
                chunk_data = {
                    "choices": [{
                        "index": 0,
                        "delta": {"content": word + " "},
                        "finish_reason": None
                    }]
                }
                yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"

                # 마지막 청크에는 finish_reason 추가
                if i == len(words) - 1:
                    final_chunk = {
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }]
                    }
                    yield f"data: {json.dumps(final_chunk, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"스트리밍 처리 실패: {e}")
            error_chunk = {
                "error": {
                    "message": str(e),
                    "type": "internal_error"
                }
            }
            yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


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
        content = _process_curriculum_graph(content)

    # 포맷 처리
    if request_body.format == "plain" or step.get("tool_name") == "JBNU_SQL":
        content = strip_markdown(content)

    return content


def _process_curriculum_graph(raw_content: str) -> str:
    """커리큘럼 그래프 처리"""
    try:
        parsed = parse_course_sections_with_preamble(raw_content)
        preamble = parsed.pop("preamble", "")
        graph_b64 = generate_graph_base64(parsed)
        return f"{preamble}\n\n![Curriculum Graph](data:image/png;base64,{graph_b64})"
    except Exception as e:
        logger.error(f"커리큘럼 그래프 생성 실패: {e}")
        return raw_content  # 원본 텍스트 반환


def _error_response(status_code: int, error_code: str, message: str) -> JSONResponse:
    """에러 응답 생성"""
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            error=message,
            error_code=error_code
        ).model_dump()
    )


# === 헬스체크 ===
@router.get("/health")
async def health_check():
    """서비스 헬스 체크"""
    try:
        health_status = hybrid_service.get_health_status()
        status_code = 200 if health_status["status"] == "healthy" else 503
        return JSONResponse(status_code=status_code, content=health_status)
    except Exception as e:
        logger.error(f"헬스 체크 실패: {e}")
        return _error_response(503, "HEALTH_CHECK_ERROR", str(e))


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


# === LangChain 기능 ===
@router.post("/langchain/chain")
async def run_langchain_chain(request: ChainRequest):
    """LangChain 체인 실행"""
    try:
        logger.info(f"LangChain 체인 실행: {request.chain_type} - {request.user_input}")

        # 체인 타입별 처리
        if request.chain_type == "basic":
            result = await hybrid_service.llm_handler.run_chain("basic", request.user_input)
        elif request.chain_type == "context":
            result = await hybrid_service.llm_handler.run_chain("context", request.user_input, context=request.context)
        elif request.chain_type == "analysis":
            result = await hybrid_service.llm_handler.run_chain("analysis", request.user_input)
        else:
            return _error_response(400, "INVALID_CHAIN_TYPE", f"지원하지 않는 체인 타입: {request.chain_type}")

        return JSONResponse({
            "chain_type": request.chain_type,
            "result": result,
            "session_id": request.session_id
        })

    except Exception as e:
        logger.error(f"LangChain 체인 실행 오류: {e}")
        return _error_response(500, "CHAIN_EXECUTION_ERROR", str(e))


@router.post("/langchain/agent")
async def run_langchain_agent(request: AgentRequest):
    """LangChain 에이전트 실행"""
    try:
        logger.info(f"LangChain 에이전트 실행: {request.user_input}")
        result = await hybrid_service.llm_handler.run_agent(request.user_input)

        return JSONResponse({
            "agent_result": result,
            "session_id": request.session_id
        })

    except Exception as e:
        logger.error(f"LangChain 에이전트 실행 오류: {e}")
        return _error_response(500, "AGENT_EXECUTION_ERROR", str(e))


# === 스트리밍 API ===
@router.post("/agent-stream")
async def agent_streaming_api(request_body: RequestBody):
    """스트리밍 지원 에이전트 API"""
    session_id = request_body.session_id or "default"
    logger.info(f"🌊 /v2/agent endpoint called for session: {session_id}")

    # stream 파라미터 확인
    stream = getattr(request_body, 'stream', False)
    logger.info(f"Stream parameter: {stream}, request_body.stream: {request_body.stream}")

    if not stream:
        # 스트리밍이 아닌 경우 기본 agent_api 호출
        return await agent_api(request_body)

    async def generate_stream():
        try:
            # 메시지에서 사용자 입력 추출
            user_message = ""
            messages = [{"role": msg.role, "content": msg.content} for msg in request_body.messages]

            for msg in messages:
                if msg.get("role") == "user":
                    user_message = msg.get("content", "")

            # AI 멘토 서비스 실행
            history = await hybrid_service.run_agent(user_message, session_id)

            # 응답 처리
            content = _process_response(history, request_body)

            # 스트리밍 형태로 응답 전송 (단어별로 분할)
            words = content.split()
            for i, word in enumerate(words):
                chunk_data = {
                    "choices": [{
                        "index": 0,
                        "delta": {"content": word + " "},
                        "finish_reason": None
                    }]
                }
                yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"

                # 마지막 청크에는 finish_reason 추가
                if i == len(words) - 1:
                    final_chunk = {
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }]
                    }
                    yield f"data: {json.dumps(final_chunk, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"스트리밍 처리 실패: {e}")
            error_chunk = {
                "error": {
                    "message": str(e),
                    "type": "internal_error"
                }
            }
            yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )
