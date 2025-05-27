import uvicorn

from fastapi import FastAPI

from controller.sqlController import router as agent_router


app = FastAPI()

# 라우터 목록 등록
app.include_router(agent_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=7999)