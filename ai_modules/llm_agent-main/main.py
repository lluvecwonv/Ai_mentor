import uvicorn

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from controller.agentController import router as agent_router


# FastAPI init
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 목록 등록
app.include_router(agent_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001)
