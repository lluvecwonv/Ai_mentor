# JBNU AI Mentor

## 실행 순서

### 1. Frontend (port: 5173)
```bash
cd open-webui
npm install
npm run dev
```

### 2. Backend (port: 8080)
```bash
conda create --name open-webui python=3.11
conda activate open-webui
cd open-webui/backend/
pip install -r requirements.txt -U
sh dev.sh
```

### 3. Pipeline (port: 9099)
```bash
conda activate open-webui
cd pipelines/
pip install -r requirements.txt
./start.sh
```

### 4. AI Modules

```bash
conda activate open-webui

# llm-agent (port: 8001)
cd ai_modules/llm_agent-main/
uvicorn main:app --host 0.0.0.0 --port 8001

# curriculum (port: 7996)
cd ai_modules/curriculum-main/
python main.py

# faiss_search (port: 7997)
cd ai_modules/faiss_search-main/
python main.py

# tool_dumb (port: 7998)
cd ai_modules/tool_dumb-main/
python main.py

# tool_sql (port: 7999)
cd ai_modules/tool_sql-main/
python main.py
```

> ⚠️ **주의:** `ai_modules` 디렉토리의 각 모듈은 `.env` 파일에 `OPENAI_API_KEY`, `DB_HOST`, `DB_PASSWORD` 등의 환경 변수 설정 필요

---

## 초기 설정

### Pipeline 연동
**Admin Panel** > **Settings** > **Connections** > **OpenAI API 연결 관리**
- URL: `http://localhost:9099`
- Key: `0p3n-w3bu!`

### Pipeline 업로드
**Admin Panel** > **Settings** > **Pipeline** > **업로드 파이프라인**

### Task Model 설정
**Settings** > **External Task Model / Local Task Model**을 **OpenAI Pipeline**으로 설정
