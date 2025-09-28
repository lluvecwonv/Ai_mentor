from fastapi import APIRouter
from pydantic import BaseModel
from service.mappingService import MappingService

router = APIRouter()
mapping_service = MappingService()

class MappingRequest(BaseModel):
    query: str

@router.post("/map")
async def map_department(request: MappingRequest):
    """학과 설명 조회 - 학과명과 설명을 함께 반환"""
    result = mapping_service.find_department_with_description(request.query)

    if result["departments"]:
        return {
            "department": result["departments"][0]["department_name"],
            "description": result["departments"][0]["description"]
        }
    else:
        return {
            "department": None,
            "description": "해당 학과를 찾을 수 없습니다."
        }