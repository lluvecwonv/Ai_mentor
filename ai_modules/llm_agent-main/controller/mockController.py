from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/message")

@router.post("/receive")
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

    # (last_user_message를 로직에 사용하실 수 있습니다...)

    # 3) 응답 페이로드 구성
    img_url="https://i.ytimg.com/vi/0xj6nj35ugk/sddefault.jpg"
    pdf_url="https://github.com/mozilla/pdf.js/raw/master/web/compressed.tracemonkey-pldi-09.pdf"
    response_json = {
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    # content 안에 Markdown 형태로 이미지/링크 삽입
                    "content": (
                        "이미지와 PDF를 확인하세요."
                        f"![설명 이미지]({img_url})"
                        f"[PDF 보고서 다운로드]({pdf_url})"
                    ),
                },
                "finish_reason": "stop",
            }
        ]
    }

    # 4) FastAPI가 dict를 JSON으로 자동 변환해 줌
    return JSONResponse(content=response_json)
