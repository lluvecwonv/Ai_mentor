from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging

from service.curriculumService import CurriculumService
from util.dbClient import DbClient
from util.utils import format_curriculum_response

logger = logging.getLogger(__name__)
router = APIRouter()

# 서비스 초기화
db_client = DbClient()
db_client.connect()
curriculum_service = CurriculumService(db_client)


class QueryRequest(BaseModel):
    query: str
    required_dept_count: int = 30


@router.get("/")
async def root():
    return {"message": "curriculum-main is running"}


@router.get("/chat")
def chat_get():
    return {"message": "이 엔드포인트는 POST 방식으로 쿼리를 처리합니다. POST 요청을 보내세요."}


@router.post("/chat")
async def process_query_endpoint(request: QueryRequest):
    """커리큘럼 추천 쿼리 처리 API"""
    try:
        # 서비스 호출
        result = curriculum_service.process_query(request.query, request.required_dept_count)

        # 응답 포맷팅
        message_text = format_curriculum_response(result)

        logger.info(f"✅ API 응답 완료: {len(message_text)}자")

        return JSONResponse(
            status_code=200,
            content={
                "message": message_text,
                "graph": result.get("graph")
            }
        )

    except Exception as e:
        logger.error(f"❌ API 요청 처리 오류: {e}")
        return JSONResponse(
            status_code=500,
            content={"message": {"error": str(e)}}
        )