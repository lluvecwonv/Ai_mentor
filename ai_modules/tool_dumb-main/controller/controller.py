# ai_modules/tool_dumb-main/controller/controller.py

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

# service 패키지의 coreService 파일에서 CoreService 클래스를 가져옵니다.
from service.coreService import CoreService

router = APIRouter()
core_service = CoreService()

class Message(BaseModel):
    role: str
    content: str

class RequestBody(BaseModel):
    messages: List[Message]

@router.post("/agent")
async def agent_api(data: RequestBody):
    # 컨트롤러는 받은 데이터를 그대로 서비스 계층으로 전달합니다.
    response = core_service.execute(data.messages)
    result = response.choices[0].message.content

    return {"message": result}