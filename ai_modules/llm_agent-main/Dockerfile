# 공통 Dockerfile 템플릿
FROM python:3.11-slim

WORKDIR /app

# 빌드 캐시 최적화
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# 앱 복사
COPY . /app

# 로그 디렉터리 보장
RUN mkdir -p /app/logs \
 && chmod -R 755 /app/logs

# 기본 포트(없으면 8001)
ENV PORT=8001
EXPOSE ${PORT}

# PORT 환경변수로 uvicorn 포트 지정 (Python 로깅 시스템 사용)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
