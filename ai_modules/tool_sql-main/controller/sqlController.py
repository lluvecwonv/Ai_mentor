import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from service.sqlCoreService import sql_service

logger = logging.getLogger(__name__)
router = APIRouter()

class SqlRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="SQL 쿼리")


@router.post("/query")
async def execute_sql(request: SqlRequest):
    """SQL 쿼리 실행 엔드포인트"""
    try:
        result = sql_service.execute(request.query)
        return {"result": result}
    except Exception as e:
        logger.error(f"SQL 실행 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agent")
async def execute_sql_agent(request: SqlRequest):
    """SQL 에이전트 엔드포인트 (agent 호출용)"""
    try:
        result = sql_service.execute(request.query)
        return {"result": result}
    except Exception as e:
        logger.error(f"SQL 실행 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    try:
        return {"status": "healthy"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"서비스 상태 불량: {str(e)}")