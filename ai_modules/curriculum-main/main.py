import uvicorn
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from controller.curriculumController import router as curriculum_router
from util.logging_setup import init_logging

# 로깅 초기화
logger = init_logging(service_name=os.getenv("SERVICE_NAME", "curriculum"))

app = FastAPI(title="Curriculum Recommendation API")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(curriculum_router)

if __name__ == "__main__":
    uvicorn.run("main_mvc:app", host="0.0.0.0", port=7996)