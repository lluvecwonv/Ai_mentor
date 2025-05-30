from fastapi import APIRouter,FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
import json

import httpx
import asyncio

from typing import List
import requests
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

router = APIRouter(prefix="/gpt")


@router.post("/chat")
async def receive_message(request: Request):

    payload = await request.json()
    payload["model"] = "gpt-4"
    stream_mode = payload.get("stream", False)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


    async with httpx.AsyncClient(timeout=None) as client:
        try:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=None,
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=str(e))

        if stream_mode:
            # 스트리밍 모드: OpenAI 서버에서 받은 chunk들을 그대로 전달
            async def event_generator():


                    # for token in ["맛", "있", "다"]:
                    #     chunk = {
                    #         "id": "chatcmpl-xxx",
                    #         "object": "chat.completion.chunk",
                    #         "choices": [{
                    #             "delta": {"content": token},
                    #             "index": 0,
                    #             "finish_reason": None
                    #         }]
                    #     }
                    #     # JSON → data: …\n\n
                    #     yield f"data: {json.dumps(chunk)}\n\n"
                    # # 스트림 종료
                    # yield "data: [DONE]\n\n"

                async for chunk in resp.aiter_lines():
                    # client 쪽이 SSE(event: message\n data: ...\n\n) 처리가 필요하면 형식 변환
                    yield chunk + "\n"
                
            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream"  # 혹은 "application/json" 필요 시 변경
            )
        else:
            # 비스트림 모드: 한 번에 JSON 파싱 후 반환
            data = resp.json()
            return JSONResponse(content=data)

