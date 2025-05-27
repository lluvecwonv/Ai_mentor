from typing import List
from fastapi import APIRouter
from pydantic import BaseModel
from service.coreService import CoreService

# 라우터 잡기
router = APIRouter()

core_service = CoreService()

class Message(BaseModel):
    role: str
    content: str

class RequestBody(BaseModel):
    stream: bool
    model: str
    messages: List[Message]

@router.post("/agent")
async def agent_api(data: RequestBody):
    # 마지막 user 발화만 뽑아서 처리
    last_user_message = next((m.content for m in reversed(data.messages) if m.role == "user"), "")
    print(last_user_message)
    result = core_service.dynamic_tool_chain(last_user_message)

    print(result)
    return {"message": result}