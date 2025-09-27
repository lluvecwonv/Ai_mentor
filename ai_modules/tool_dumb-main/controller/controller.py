"""
LLM Fallback Service Controller
시스템 안정성을 위한 폴백 서비스 컨트롤러
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import logging

from service.coreService import CoreService

logger = logging.getLogger(__name__)

router = APIRouter()
core_service = CoreService()

class Message(BaseModel):
    role: str
    content: str

class RequestBody(BaseModel):
    messages: List[Message]

@router.post("/agent")
async def agent_api(data: RequestBody):
    """폴백 에이전트 API - 시스템 안정성을 위한 기본 LLM 서비스"""
    try:
        logger.info(f"폴백 서비스 요청: {len(data.messages)}개 메시지")

        # 컨트롤러는 받은 데이터를 그대로 서비스 계층으로 전달
        response = core_service.execute(data.messages)
        result = response.choices[0].message.content

        logger.info("폴백 서비스 응답 생성 완료")
        return {"message": result}

    except Exception as e:
        logger.error(f"폴백 서비스 오류: {e}")
        raise HTTPException(status_code=500, detail=f"폴백 서비스 오류: {str(e)}")


@router.get("/health")
async def health_check():
    """폴백 서비스 헬스 체크"""
    return {
        "status": "healthy",
        "service": "llm-fallback",
        "port": 7998,
        "description": "LLM Fallback/General-Agent for system stability"
    }