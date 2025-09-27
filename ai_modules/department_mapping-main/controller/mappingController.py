from fastapi import APIRouter
from pydantic import BaseModel
from service.mappingService import MappingService

router = APIRouter()
mapping_service = MappingService()

class MappingRequest(BaseModel):
    query: str
    top_k: int = 3

class MappingResponse(BaseModel):
    original_query: str
    mapped_departments: list
    confidence_scores: list

@router.post("/map")
async def map_department(request: MappingRequest):
    """
    학과명 매핑 API
    예: "컴공" -> "컴퓨터인공지능학부"
    """
    try:
        result = mapping_service.find_similar_departments(
            query=request.query,
            top_k=request.top_k
        )
        
        return {
            "original_query": request.query,
            "mapped_departments": result["departments"],
            "confidence_scores": result["scores"],
            "success": True
        }
    except Exception as e:
        return {
            "original_query": request.query,
            "mapped_departments": [],
            "confidence_scores": [],
            "success": False,
            "error": str(e)
        }

@router.get("/departments")
async def get_all_departments():
    """모든 학과 목록 조회"""
    try:
        departments = mapping_service.get_all_departments()
        return {
            "departments": departments,
            "total_count": len(departments),
            "success": True
        }
    except Exception as e:
        return {
            "departments": [],
            "total_count": 0,
            "success": False,
            "error": str(e)
        }

@router.post("/agent")
async def agent_endpoint(request: MappingRequest):
    """
    기존 에이전트 인터페이스와 호환되는 엔드포인트
    """
    try:
        result = mapping_service.find_similar_departments(
            query=request.query,
            top_k=request.top_k
        )
        
        # 가장 유사한 학과 선택
        if result["departments"]:
            best_match = result["departments"][0]
            confidence = result["scores"][0]
            
            response_text = f"'{request.query}'에 대한 학과명 매핑 결과:\n\n"
            response_text += f"✅ 가장 유사한 학과: {best_match['department_name']}\n"
            response_text += f"📊 신뢰도: {confidence:.2%}\n\n"
            
            if len(result["departments"]) > 1:
                response_text += "🔍 다른 후보들:\n"
                for i, (dept, score) in enumerate(zip(result["departments"][1:], result["scores"][1:]), 2):
                    response_text += f"{i}. {dept['department_name']} (신뢰도: {score:.2%})\n"
            
            return {"message": response_text}
        else:
            return {"message": f"'{request.query}'에 대한 유사한 학과를 찾을 수 없습니다."}
            
    except Exception as e:
        return {"message": f"학과명 매핑 중 오류가 발생했습니다: {str(e)}"}
