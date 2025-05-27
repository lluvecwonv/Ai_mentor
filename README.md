# 🧠 JBNU AI Mentor - 로컬 실행 가이드

---

## ✅ Frontend (Open WebUI)
```bash
cd open-webui
npm install
npm run dev  # 실행: http://localhost:5173
````

---

## ✅ Backend (Open WebUI API)

리눅스 환경에서 실행 (포트: `8080`)

```bash
conda create --name open-webui python=3.11 # 처음 실행할 때만
conda activate open-webui
cd open-webui/backend
pip install -r requirements.txt -U
sh dev.sh  # 실행: http://localhost:8080
```

---

## ✅ Pipelines 서버

리눅스 환경에서 실행 (포트: `9099`)

```bash
conda activate open-webui
cd pipelines
pip install -r requirements.txt

# 쉘스크립트 윈도우 개행문자 제거
sudo apt update
sudo apt install dos2unix
sed -i 's/\r$//' start.sh
./start.sh  # 실행: http://localhost:9099
```

---

## 🔗 Open WebUI ↔ Pipelines 연동

> **Open WebUI Admin Panel**
> `Settings > Connections` 메뉴에서 API 추가

* **URL:** `http://localhost:9099`
* **Key:** `0p3n-w3bu!`

---

## 🧩 llm\_agent-main 서버

FastAPI 기반 서버 (포트: `8001`)

> open-webui의 백엔드와 **localhost 도메인을 맞춰야 함**

```bash
conda activate open-webui
cd ai_modules/llm_agent-main
uvicorn main:app --host 0.0.0.0 --port 8001
```

---

## 📄 기능 항목 (진행 중)

* [x] PDF 처리
* [x] 대화 stream 처리
* [x] 대화 기록 관리

---

## 🧼 참고사항

* 모든 서버는 `.env` 환경파일을 통해 민감정보(API KEY 등)를 관리합니다.

```

