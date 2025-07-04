from fastapi import APIRouter
from pydantic import BaseModel
from dotenv import load_dotenv
import os

from service.curriculumService import CurriculumService

load_dotenv()  # .env 파일 자동 로드

openai_api_key = os.getenv("OPENAI_API_KEY")

router = APIRouter()

svc = CurriculumService(
    openai_api_key,
    db_config_path="service/curriculumplan/data/db.json"
)
##########

class CurriculumRequest(BaseModel):
    goal: str
    level: str

@router.post("/curriculum")
async def vector_search(req: CurriculumRequest):
    
    plan = svc.generate(req.goal, req.level)
    return {"curriculum": plan}
