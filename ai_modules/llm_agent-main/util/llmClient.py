from openai import OpenAI
from dotenv import load_dotenv
import os, json

load_dotenv()  # .env 파일 자동 로드

api_key = os.getenv("OPENAI_API_KEY")
db_host = os.getenv("DB_HOST")

def _to_openai_content(x):
    """
    OpenAI chat.completions 에서 허용하는 content 형태로 정규화:
    - str -> 그대로
    - list -> 그대로 (이미 content parts 로 간주)
    - dict ->
        - {'type':'text','text':'...'} 는 [dict] 로 감싸 parts 배열로
        - {'text':'...'} 만 있으면 그 텍스트 사용
        - 그 외 dict 는 JSON 문자열로 직렬화
    - None -> ""
    - 기타 -> str(x)
    """
    if x is None:
        return ""
    if isinstance(x, str):
        return x
    if isinstance(x, list):
        return x
    if isinstance(x, dict):
        if "type" in x and "text" in x:
            return [x]
        if "text" in x and isinstance(x["text"], str):
            return x["text"]
        return json.dumps(x, ensure_ascii=False)
    return str(x)


class LlmClient():
    def __init__(self):
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"

    # ★★★ 수정한 call_llm 함수 ★★★
    def call_llm(self, messages: list, json_mode: bool = False) -> str:
        """
        메시지 리스트를 직접 받아 LLM을 호출합니다.
        json_mode가 True이면 JSON 응답을 강제합니다.
        """
        extra_args = {}
        if json_mode:
            # JSON 모드는 GPT-4o, GPT-3.5-Turbo 최신 모델에서 지원됩니다.
            extra_args["response_format"] = {"type": "json_object"}
            
        return self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **extra_args
        )

        sys_c = _to_openai_content(system_prompt)
        usr_c = _to_openai_content(user_prompt)

        messages = [
            {"role": "system", "content": sys_c},
            {"role": "user",   "content": usr_c},
        ]

        print("[LlmClient.chat] messages types:",
              [{"role": m["role"], "type": type(m["content"]).__name__} for m in messages])

        return self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=stream
        )
