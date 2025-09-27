import uvicorn
import os

from fastapi import FastAPI

from controller.searchController import router as agent_router
from util.logging_setup import init_logging

# 로깅 초기화
logger = init_logging(service_name=os.getenv("SERVICE_NAME", "faiss-search"))

app = FastAPI()

# 라우터 목록 등록
app.include_router(agent_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=7997)