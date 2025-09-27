from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from service.searchService import SearchService
from util.dbClient import DbClient

logger = logging.getLogger(__name__)
router = APIRouter()

# 서비스 초기화
db_client = DbClient()
db_client.connect()
search_service = SearchService(db_client)

class SearchRequest(BaseModel):
    query: Optional[str] = None
    key: Optional[str] = None
    count: int = 30

@router.get("/")
async def root():
    return {"message": "faiss_search-main is running"}

@router.post("/search")
async def search(data: SearchRequest):
    """통합 검색 API"""
    # 입력 검증
    query_text = data.query or data.key
    if not query_text:
        raise HTTPException(status_code=422, detail="query 또는 key가 필요합니다")

    # 검색 실행
    results = search_service.search_hybrid(
        query_text=query_text,
        count=data.count
    )

    return {"results": results}