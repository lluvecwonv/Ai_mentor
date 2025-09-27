from fastapi import APIRouter
from pydantic import BaseModel
from service.mappingService import MappingService

router = APIRouter()
mapping_service = MappingService()

class MappingRequest(BaseModel):
    query: str

@router.post("/map")
async def map_department(request: MappingRequest):
    """학과명 매핑 - 학과명만 반환"""
    result = mapping_service.find_similar_departments(request.query)
    
    if result["departments"]:
        return {"department": result["departments"][0]["department_name"]}
    else:
        return {"department": None}