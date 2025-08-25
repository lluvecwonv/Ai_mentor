# 공통 Dockerfile 템플릿
FROM python:3.11-slim

WORKDIR /app

# 빌드 캐시 최적화
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# 앱 복사
COPY . /app

# 기본 포트(없으면 8000)
ENV PORT=8000
EXPOSE ${PORT}

# PORT 환경변수로 uvicorn 포트 지정
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
