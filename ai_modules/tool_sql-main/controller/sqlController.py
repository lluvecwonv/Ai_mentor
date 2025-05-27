
from fastapi import APIRouter
from pydantic import BaseModel
from service.sqlCoreService import SqlCoreService
from service.sanitizeService import SanitizeService

# 라우터 잡기
router = APIRouter()

core_service = SqlCoreService()
sanitize_service = SanitizeService()

class RequestBody(BaseModel):
    query: str

@router.post("/agent")
async def agent_api(data: RequestBody):

    # 질문 세니타이징 (모호한 질문이나, 반복 표현과 같은 부분 줄이기)
    sanitize_res = sanitize_service.execute(data.query)
    print(sanitize_res)
    
    # sql 쿼리 진행
    core_service.create_agent()
    result = core_service.execute(sanitize_res)

    return {"message": result}
