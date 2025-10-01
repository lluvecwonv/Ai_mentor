from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse, HTMLResponse, FileResponse
from pydantic import BaseModel
import logging
import os

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
    """커리큘럼 추천 쿼리 처리 API - 텍스트 + 그래프 반환"""
    try:
        # 서비스 호출
        result = curriculum_service.process_query(request.query, request.required_dept_count)

        # 응답 포맷팅
        message_text = format_curriculum_response(result)

        logger.info(f"✅ API 응답 완료: {len(message_text)}자")

        # 텍스트 + 그래프 이미지 URL JSON 응답
        # 브라우저에서 접근 가능한 절대 URL 필요 (환경변수 또는 서버 IP)
        server_host = os.getenv("SERVER_HOST", "210.117.181.110")
        graph_image_url = f"http://{server_host}:7996/graph-image"
        graph_base64 = result.get("graph", "")  # "data:image/png;base64,..." 형식

        # 메시지는 텍스트만 (이미지는 별도로 처리)
        return JSONResponse(
            status_code=200,
            content={
                "message": message_text,  # 텍스트만 반환
                "graph_base64": graph_base64,  # PNG base64 이미지
                "graph_image_url": graph_image_url  # PNG 이미지 URL
            }
        )

    except Exception as e:
        logger.error(f"❌ API 요청 처리 오류: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.get("/graph-image")
async def get_graph_image():
    """최근 생성된 그래프 PNG 이미지 반환"""
    try:
        image_path = "result/0_result_department_top1_graph.png"

        if not os.path.exists(image_path):
            raise HTTPException(status_code=404, detail="그래프 이미지를 찾을 수 없습니다")

        return FileResponse(
            image_path,
            media_type="image/png",
            headers={"Cache-Control": "no-cache"}
        )

    except Exception as e:
        logger.error(f"❌ 그래프 이미지 로드 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))