from fastapi import APIRouter
from pydantic import BaseModel

from faiss_search.service.vectorService import VectorService

router = APIRouter()

vector_service = VectorService()

##########

class ReadBody(BaseModel):
    count: int
    key: str

@router.post("/search")
async def vector_search(data: ReadBody):
    
    response_key = vector_service.search_vector(data.count, data.key)

    return {"key": str(response_key)}


