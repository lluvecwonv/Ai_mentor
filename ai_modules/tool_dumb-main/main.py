import uvicorn
from fastapi import FastAPI
from controller.controller import router as agent_router

app = FastAPI(
    title="AI Mentor Fallback Service",
    description="LLM Fallback/General-Agent for system stability",
    version="1.0"
)

# 라우터 목록 등록
app.include_router(agent_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=7998)