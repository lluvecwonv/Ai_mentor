from fastapi import APIRouter,FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse


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
                async for chunk in resp.aiter_bytes():
                    # client 쪽이 SSE(event: message\n data: ...\n\n) 처리가 필요하면 형식 변환
                    yield chunk

            return StreamingResponse(
                resp.aiter_lines(),             # 바이트 덩어리 대신 라인 단위
                media_type="text/event-stream"
            )
        else:
            # 비스트림 모드: 한 번에 JSON 파싱 후 반환
            data = resp.json()
            return JSONResponse(content=data)

