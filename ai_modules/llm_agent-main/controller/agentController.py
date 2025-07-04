from typing import List
from fastapi import APIRouter
from pydantic import BaseModel
from service.coreService import CoreService

# 라우터 설정
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
async def agent_api(request_body: RequestBody):
    # 마지막 user 발화만 추출
    last_user_message = next((m.content for m in reversed(request_body.messages) if m.role == "user"), "")
    print("User query:", last_user_message)

    # dynamic_tool_chain에서 dict 반환
    history_data = core_service.dynamic_tool_chain(last_user_message)

    print("history_data:", history_data)

    return {"message":history_data}
