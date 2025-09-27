
# 🤖 JBNU AI Mentor - 로컬 실행 가이드

docker logs --tail 15000 llm-agent | cat
docker logs llm-agent > ~/llm-agent.log 2>&1
docker logs --tail 400 svc7997 | cat
docker logs  --tail 400 svc7999 | cat
docker logs  --tail 400 department-mapping | cat


llm-agent (포트 8001): LLM 메인 오케스트레이터/게이트웨이. 프론트 요청을 받아 적절한 서브 에이전트로 라우팅. 디렉터리: ai_modules/llm_agent-main
svc7997 (포트 7997): Vector-Search-Agent (FAISS 유사도 검색). 과목/키워드 유사도 기반 검색. 엔드포인트: /search
svc7999 (포트 7999): DB-Agent (SQL 질의). 구조화된 DB 질의 처리. 엔드포인트: /agent
department-mapping (포트 8000): Department-Agent. 학과/전공 명칭 매핑·정규화. 엔드포인트: /agent
추가로 프로젝트에 자주 보이는 것:
svc7996: Curriculum-Agent (커리큘럼 생성/플래닝, /chat)
svc7998: LLM Fallback/General-Agent (일반 LLM 처리, /agent)



    - cd /home/dbs0510/
  AiMentor_edit
      - ./restart_all.sh --rebuild



## Frontend (port: 5173)


code --list-extensions | grep -i preview

curl -s http://localhost:3000 > /dev/null && echo "✅ Frontend service is running on port 3000" || echo "❌ Frontend service not responding"

### 설치
```bash
cd open-webui
npm install
```

### 실행

```bash
cd open-webui
npm run dev
```

---

## Backend (port: 8080)

### 설치

```bash
conda create --name open-webui python=3.11
conda activate open-webui
cd open-webui/backend/
pip install -r requirements.txt -U
sh dev.sh
```

### 실행

```bash
conda activate open-webui
cd open-webui/backend/
sh dev.sh
```

---

## Pipeline (port: 9099)

### 설치

```bash
conda activate open-webui
cd pipelines/
pip install -r requirements.txt
sudo apt update
sudo apt install dos2unix
sed -i 's/\r$//' start.sh
./start.sh
```x

### 실행

```bash
conda activate open-webui
cd pipelines/
./start.sh
```

---

## Open WebUI ↔ Pipelines 연동

1. **Admin Panel** > **Settings** > **Connections**
2. **OpenAI API 연결 관리** 클릭

   * URL: `http://localhost:9099`
   * Key: `0p3n-w3bu!`

---

## Pipeline 추가

1. **Admin Panel** > **Settings** > **Pipeline**
2. **업로드 파이프라인** → 파일 선택 → 옆의 버튼 클릭 → **저장**

---

## llm-agent-main Uvicorn (port: 8001)

```bash
conda activate open-webui
cd ai_modules/llm_agent-main/
uvicorn main:app --host 0.0.0.0 --port 8001
```
## faiss_search-main (port: 7996)

```bash
conda activate open-webui
cd ai_modules/curriculum-main/
python main.py
```
## faiss_search-main (port: 7997)

```bash
conda activate open-webui
cd ai_modules/faiss_search-main/
python main.py
```
## tool_dumb-main (port: 7998)

```bash
conda activate open-webui
cd ai_modules/tool_dumb-main/
python main.py
```
## tool_sql-main (port: 7999)

```bash
conda activate open-webui
cd ai_modules/tool_sql-main/
python main.py
```

> ⚠️ **주의:** `ai_modules` 디렉토리의 파일들은 `.env` 파일을 통해 `OPENAI_API_KEY`, `DB_HOST`, `DB_PASSWORD` 등의 환경 변수를 반드시 설정해야 합니다.


---
## 제목 & 태그 생성 설정 External Task Model, Local Task Model
![alt text](image.png)
공개 설정
![alt text](image-1.png)
External Task Model, Local Task Model: OpenAI Pipeline
안하면 llm-agent-main으로 보내져서 오류 뜸
---
## PDF 응답 처리

채팅 메시지 `content` 에 Markdown 링크로 PDF 다운로드 링크를 제공하세요:

```python
"content" : f"[PDF 보고서 다운로드 링크]({pdf_url})"
```


---
## Stream=False일 때

```jsonc
// stream=False 응답 예시
{
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "안녕하세요! 요청하신 내용을 처리했습니다.\n\n[PDF 보고서 다운로드](https://example.com/report.pdf)",
        "attachments": [
          {
            "type": "image",
            "url": "https://example.com/image.png",
            "name": "image.png"
          },
          {
            "type": "file",
            "url": "https://example.com/report.pdf",
            "name": "report.pdf"
          }
        ]
      },
      "finish_reason": "stop"
    }
  ]
}
```

## Stream=True일 때 응답 처리 (Server-Sent Events 형식)

* **헤더**

  ```
  HTTP/1.1 200 OK
  Content-Type: text/event-stream
  Connection: keep-alive
  ```

* **토큰 델타 이벤트 예시**

  ```http
  data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk",
         "choices":[{"delta":{"content":"맛"},
                     "index":0,
                     "finish_reason":null}]}

  data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk",
         "choices":[{"delta":{"content":"있"},
                     "index":0,
                     "finish_reason":null}]}

  data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk",
         "choices":[{"delta":{"content":"다"},
                     "index":0,
                     "finish_reason":null}]}

  data: [DONE]
  ```

* **FastAPI 제너레이터 예시**

  ```python
  async def event_generator():
      for token in ["맛", "있", "다"]:
          chunk = {
              "id": "chatcmpl-xxx",
              "object": "chat.completion.chunk",
              "choices": [{
                  "delta": {"content": token},
                  "index": 0,
                  "finish_reason": None
              }]
          }
          yield f"data: {json.dumps(chunk)}\n\n"
          await asyncio.sleep(0.1)

      # 스트림 종료
      yield "data: [DONE]\n\n"
  ```

  ```python
  return StreamingResponse(
      event_generator(),
      media_type="text/event-stream"
  )
  ```





---

## 📄 기능 항목 (진행 중)

* [x] PDF 처리
* [x] 대화 stream 처리
* [ ] 대화 기록 관리

---

## 🧼 참고사항

* 모든 서버는 `.env` 환경파일을 통해 민감정보(API KEY 등)를 관리합니다.
# Ai_mentor
