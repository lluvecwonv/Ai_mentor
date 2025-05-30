from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import time  # created 값에 타임스탬프 사용

router = APIRouter(prefix="/message")


# ==== 요청용 모델 ====
class Message(BaseModel):
    role: str
    content: str

class RequestBody(BaseModel):
    stream: bool
    model: str
    messages: List[Message]


# ==== 응답용 모델 ====
class ChatResponseMessage(BaseModel):
    role: str
    content: str

class ChatChoice(BaseModel):
    index: int
    message: ChatResponseMessage
    finish_reason: str

class UsageInfo(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class ChatResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: List[ChatChoice]
    usage: UsageInfo


@router.post("/receive", response_model=ChatResponse)
async def receive_message(data: RequestBody):
    last_user_message = next((m.content for m in reversed(data.messages) if m.role == "user"), "")

    response = ChatResponse(
        id="chatcmpl-abc123",
        object="chat.completion",
        created=int(time.time()),
        model="Controller",
        choices=[
            ChatChoice(
                index=0,
                message=ChatResponseMessage(
                    role="assistant",
                    content="나와라 얍: "+last_user_message
                ),
                finish_reason="stop"
            )
        ],
        usage=UsageInfo(
            prompt_tokens=9,
            completion_tokens=12,
            total_tokens=21
        )
    )
    return response
