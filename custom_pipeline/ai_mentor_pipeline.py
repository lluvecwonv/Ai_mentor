from typing import List, Union, Generator, Iterator
from pydantic import BaseModel
import requests

class Pipeline:
    class Valves(BaseModel):
        # LLM 에이전트(8001번 포트) URL / 타임아웃 설정
        agent_url: str = "http://localhost:8001/agent"
        timeout: float = 200.0

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
        payload = {
            "stream": False,
            "model": model_id,
            "messages": messages  # 전체 히스토리 그대로 전달
        }

        try:
            resp = requests.post(
                self.valves.agent_url,
                json=payload,
                timeout=self.valves.timeout
            )
            resp.raise_for_status()

            # LLM에서 온 메시지 추출
            raw_message = resp.json().get("message", "")
            
            # dict이면 histroy_data일 가능성이 높음
            if isinstance(raw_message, dict):
                # steps 중 마지막 step의 tool_response만 뽑아서 user한테 보여주기
                steps = raw_message.get("steps", [])
                if steps:
                    last_tool_response = steps[-1].get("tool_response", "")
                    return last_tool_response
                else:
                    return "[LLM 응답 오류] 히스토리에 툴 실행 결과가 없습니다."
                
            # 원래 기대한 포맷 (string) 이라면 그대로 처리
            if isinstance(raw_message, str):
                parts = raw_message.split("|")
                if len(parts) >= 2: 
                    return parts[1]  # api_body만 반환
                else:
                    return f"[LLM 응답 포맷 오류] 예상한 포맷: tool_name|api_body|이유\n\n▶ 응답 원문:\n{raw_message}"
            
            # 만약 예상치 못한 포맷이라면
            return "[LLM 응답 오류] 알 수 없는 포맷입니다."

        except Exception as e:
            return f"LLM Agent error: {e}"