import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from controller.sqlController import router as sql_router

# FastAPI 앱 생성
app = FastAPI(
    title="SQL Tool",
    description="SQL 처리 도구",
    version="1.0.0"
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(sql_router, prefix="/api/v1", tags=["SQL"])

@app.get("/")
async def root():
    return {
        "message": "SQL Tool API",
        "version": "1.0.0",
        "status": "running"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=7999,
        reload=True
    )
