from fastapi import APIRouter
from pydantic import BaseModel

from service.coreService import coreService

# 라우터 잡기
router = APIRouter()

core_service = coreService()

class RequestBody(BaseModel):
    query: str

@router.post("/agent")
async def agent_api(data: RequestBody):

    response = core_service.execute(data.query)
    result = response.choices[0].message.content

    return {"message": result}