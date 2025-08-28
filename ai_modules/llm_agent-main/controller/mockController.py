from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
import os, base64
from pathlib import Path

router = APIRouter()

def convert_image_to_base64(image_path: str):
    # 이 파일(mockController.py)이 있는 디렉터리
    here = Path(__file__).parent
    target = here / image_path
    with open(target, "rb") as f:
        return base64.b64encode(f.read()).decode()
    
@router.post("/mock")
async def receive_message(request: Request):
    # 1) JSON 본문 파싱
    body = await request.json()
    messages = body.get("messages", [])

    # 2) 마지막 user 메시지 추출
    last_user_message = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last_user_message = msg.get("content", "")
            break


    b64 = convert_image_to_base64("example.png")
    data_uri = f"data:image/jpeg;base64,{b64}"


    response_json = {
        "id": "chatcmpl-xyz",
        "object": "chat.completion",
        "model": "gpt-4-turbo",
        "choices": [
            {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": f"![image]({data_uri})\n"
            },
            "finish_reason": "stop"
            }
        ],
        "sources": [
            {
            "source": { "type": "file", "id": "f3a27a95-121d-4eb6-8505-19aafb9dd1cc" },
            "document": [],
            "metadata": [],
            "distances": []
            }
        ]
    }


    # 4) FastAPI가 dict를 JSON으로 자동 변환해 줌
    return JSONResponse(response_json)


