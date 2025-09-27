from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import logging
from datetime import datetime

from service.searchService import SearchService
from util.dbClient import DbClient
from openai import OpenAI
import os

# 로거 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# 서비스 초기화
db_client = DbClient()
db_client.connect()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
search_service = SearchService(openai_client, db_client)

##########

@router.get("/")
async def root():
    return {"message": "faiss_search-main is running"}

class ReadBody(BaseModel):
    # 기존 호환성: key와 query 모두 지원
    query: Optional[str] = None
    key: Optional[str] = None
    count: int = 5
    debug: Optional[bool] = False

@router.post("/search")
async def vector_search(data: ReadBody):
    start_time = datetime.now()

    logger.info(f"🔍 [FAISS] 검색 시작:")
    if data.query:
        logger.info(f"  - 쿼리: '{data.query}'")
    logger.info(f"  - 요청 개수: {data.count}")
    logger.info(f"  - 시작 시간: {start_time.strftime('%H:%M:%S.%f')[:-3]}")

    # 입력 텍스트 추출
    query_text = data.query if data.query is not None else data.key
    if not query_text:
        logger.error("❌ [FAISS] 검색 실패: query 또는 key가 누락됨")
        raise HTTPException(status_code=422, detail="Either 'query' or 'key' must be provided")

    logger.info(f"🔍 [FAISS] 검색: '{query_text}'")
    # 간단한 하이브리드 검색
    results = search_service.search_hybrid(
        query_text=query_text,
        count=data.count
    )

    end_time = datetime.now()
    processing_time = (end_time - start_time).total_seconds()

    logger.info(f"✅ [FAISS] 검색 완료:")
    logger.info(f"  - 처리 시간: {processing_time:.3f}초")
    logger.info(f"  - 결과 개수: {len(results)}")

    if results:
        logger.info(f"📋 [FAISS] 검색 결과:")
        for i, result in enumerate(results[:3]):  # 상위 3개만 로그
            name = result.get('name', 'N/A')
            dept = result.get('department', 'N/A')
            similarity = result.get('similarity_score', 0)
            logger.info(f"  {i+1}. {name} ({dept}) - 유사도: {similarity:.3f}")

        if len(results) > 3:
            logger.info(f"  ... 총 {len(results)}개 결과")
    else:
        logger.warning(f"⚠️ [FAISS] 검색 결과 없음: '{query_text}'")

    # 표준화된 응답 포맷 반환
    return {
        "results": results,
        "debug": bool(data.debug)
    }

@router.post("/search-sql-filter")
async def vector_search_with_sql_filter(data: ReadBody):
    """SQL 사전 필터링 기반 벡터 검색"""
    start_time = datetime.now()

    logger.info(f"🎯 [SQL+Vector] SQL 필터링 검색 시작:")
    logger.info(f"  - 쿼리: '{data.query or data.key}'")
    logger.info(f"  - 요청 개수: {data.count}")
    logger.info(f"  - 시작 시간: {start_time.strftime('%H:%M:%S.%f')[:-3]}")

    # 입력 텍스트 추출
    query_text = data.query if data.query is not None else data.key
    if not query_text:
        logger.error("❌ [SQL+Vector] 검색 실패: query 또는 key가 누락됨")
        raise HTTPException(status_code=422, detail="Either 'query' or 'key' must be provided")

    # 하이브리드 검색
    results = search_service.search_hybrid(
        query_text=query_text,
        count=data.count
    )

    end_time = datetime.now()
    processing_time = (end_time - start_time).total_seconds()

    logger.info(f"✅ [SQL+Vector] 검색 완료:")
    logger.info(f"  - 처리 시간: {processing_time:.3f}초")
    logger.info(f"  - 결과 개수: {len(results)}")

    if results:
        logger.info(f"📋 [SQL+Vector] 검색 결과:")
        for i, result in enumerate(results[:3]):  # 상위 3개만 로그
            name = result.get('name', 'N/A')
            dept = result.get('department', 'N/A')
            similarity = result.get('similarity_score', 0)
            logger.info(f"  {i+1}. {name} ({dept}) - 유사도: {similarity:.3f}")

        if len(results) > 3:
            logger.info(f"  ... 총 {len(results)}개 결과")
    else:
        logger.warning(f"⚠️ [SQL+Vector] 검색 결과 없음: '{query_text}'")

    return {
        "results": results,
        "search_method": "sql_prefilter",
        "debug": bool(data.debug)
    }

@router.post("/search-sql-filter-improved")
async def vector_search_with_sql_filter_improved(data: ReadBody):
    """개선된 SQL 사전 필터링 + 벡터 검색 (성능 최적화)"""
    start_time = datetime.now()

    logger.info(f"🚀 [SQL+Vector-v2] 개선된 SQL 필터링 검색 시작:")
    logger.info(f"  - 쿼리: '{data.query or data.key}'")
    logger.info(f"  - 요청 개수: {data.count}")
    logger.info(f"  - 학과 필터: {data.department}")
    logger.info(f"  - 시작 시간: {start_time.strftime('%H:%M:%S.%f')[:-3]}")

    # 입력 텍스트 추출
    query_text = data.query if data.query is not None else data.key
    if not query_text:
        logger.error("❌ [SQL+Vector-v2] 검색 실패: query 또는 key가 누락됨")
        raise HTTPException(status_code=422, detail="Either 'query' or 'key' must be provided")

    # 하이브리드 검색
    results = search_service.search_hybrid(
        query_text=query_text,
        count=data.count
    )

    end_time = datetime.now()
    processing_time = (end_time - start_time).total_seconds()

    logger.info(f"✅ [SQL+Vector-v2] 검색 완료:")
    logger.info(f"  - 처리 시간: {processing_time:.3f}초")
    logger.info(f"  - 결과 개수: {len(results)}")

    if results:
        logger.info(f"📋 [SQL+Vector-v2] 검색 결과:")
        for i, result in enumerate(results[:3]):  # 상위 3개만 로그
            name = result.get('name', 'N/A')
            dept = result.get('department', 'N/A')
            similarity = result.get('similarity_score', 0)
            professor = result.get('professor', 'N/A')
            logger.info(f"  {i+1}. {name} ({dept}) - 교수: {professor} - 유사도: {similarity:.3f}")

        if len(results) > 3:
            logger.info(f"  ... 총 {len(results)}개 결과")
    else:
        logger.warning(f"⚠️ [SQL+Vector-v2] 검색 결과 없음: '{query_text}'")

    return {
        "results": results,
        "search_method": "sql_prefilter_improved",
        "processing_time": processing_time,
        "debug": bool(data.debug)
    }
