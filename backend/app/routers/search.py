from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.embedding_service import get_text_embedding
from app.services.vector_db_service import search_documents
from typing import List, Dict

router = APIRouter()

class SearchRequest(BaseModel):
    query_text: str
    limit: int = 5

class SearchResult(BaseModel):
    drive_file_id: str
    file_name: str
    mime_type: str
    drive_url: str
    extracted_text_snippet: str
    similarity_score: float

@router.post("/", response_model=List[SearchResult])
async def search_documents_endpoint(request: SearchRequest):
    """Search for documents similar to the query."""
    try:
        # Generate embedding for the query
        query_embedding = get_text_embedding(request.query_text)
        
        # Perform similarity search
        results = search_documents(query_embedding, request.limit)
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
