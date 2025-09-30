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
        graph_url = "http://localhost:7996/graph"
        graph_image_url = "http://localhost:7996/graph-image"

        # Open WebUI에서 마크다운 이미지로 렌더링
        message_with_graph = f"{message_text}\n\n📊 **커리큘럼 로드맵**\n\n![커리큘럼 그래프]({graph_image_url})"

        return JSONResponse(
            status_code=200,
            content={
                "message": message_with_graph,
                "graph_html": result.get("graph"),  # D3.js 인터랙티브 HTML
                "graph_url": graph_url,  # 인터랙티브 그래프 링크
                "graph_image_url": graph_image_url  # PNG 이미지 링크
            }
        )

    except Exception as e:
        logger.error(f"❌ API 요청 처리 오류: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.get("/graph")
async def show_latest_graph():
    """최근 생성된 그래프를 HTML로 직접 반환"""
    try:
        # 가장 최근 요청의 그래프를 보여주기 위한 기본 쿼리
        result = curriculum_service.process_query("컴퓨터과학과 추천해줘", 30)
        graph_html = result.get("graph", "<h1>그래프를 생성할 수 없습니다</h1>")

        return HTMLResponse(content=graph_html, status_code=200)

    except Exception as e:
        logger.error(f"❌ 그래프 표시 오류: {e}")
        return HTMLResponse(
            content=f"<h1>오류 발생</h1><p>{str(e)}</p>",
            status_code=500
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