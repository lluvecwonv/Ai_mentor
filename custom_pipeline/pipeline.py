from typing import List, Union, Generator, Iterator
from pydantic import BaseModel
import requests

class Pipeline:
    class Valves(BaseModel):
        pass

    def __init__(self):
        # 파이프라인 이름 설정
        self.name = "Ai_Mentor_pipeline"
        self.valves = self.Valves()

    async def on_startup(self):
        # 파이프라인 시작 시 호출되는 함수
        print(f"on_startup:{__name__}")

    async def on_shutdown(self):
        # 파이프라인 종료 시 호출되는 함수
        print(f"on_shutdown:{__name__}")

    def pipe(
        self,
        user_message: str, # 사용자로부터 입력된 질문
        model_id: str, # 모델 ID
        messages: List[dict], # 전체 대화 히스토리
        body: dict # 요청 본문
    ) -> Union[str, Generator, Iterator]:
        # 1) UI에서 입력된 질문을 그대로 전달위해 payload 생성
        # user_message는 사용자가 입력한 질문
        payload = {"query": user_message}

        try:
            # 2) 7999 포트로 post 요청
            resp = requests.post(
                "http://host.docker.internal:7999/agent",
                json=payload, # 질문 전송
                timeout=200 # 타임아웃 설정 (200초)
            )
            resp.raise_for_status()

            # 3) 반환된 JSON의 "message" 필드 리턴
            return resp.json().get("message", "")
        
        except Exception as e:
            return f"SQL tool error: {e}"
