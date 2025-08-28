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

    def call_llm(self, system_prompt=None, user_prompt=None, assistant_prompt=None, stream: bool = False):
        sys_c  = _to_openai_content(system_prompt)
        usr_c  = _to_openai_content(user_prompt)
        asst_c = _to_openai_content(assistant_prompt)

        messages = []
        if sys_c != "":
            messages.append({"role": "system", "content": sys_c})
        messages.append({"role": "user", "content": usr_c})
        if asst_c != "":
            messages.append({"role": "assistant", "content": asst_c})

        # 디버그: 실제 타입 확인 (반드시 로그에 찍혀야 함)
        print("[LlmClient.call_llm] messages types:",
              [{"role": m["role"], "type": type(m["content"]).__name__} for m in messages])

        return self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=stream,
        )

    def chat(self, user_prompt, stream: bool = False):
        system_prompt = (
            "You are a professional translator.\n"
            "Translate only the Korean text into clear, idiomatic English.\n"
            "Preserve all existing markdown syntax (including image links) unchanged.\n"
            "Do not add explanations or alter formatting beyond the translation."
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
