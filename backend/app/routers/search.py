from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from app.services.embedding_service import get_text_embedding
from app.services.vector_db_service import search_documents
from app.services.analytics_service import log_search_query
from typing import List, Dict
import time

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
async def search_documents_endpoint(request: SearchRequest, http_request: Request):
    """Search for documents similar to the query."""
    start_time = time.time()

    try:
        # Generate embedding for the query
        query_embedding = get_text_embedding(request.query_text)

        # Perform similarity search
        results = search_documents(query_embedding, request.limit)

        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)

        # Log search query for analytics (async, non-blocking)
        try:
            log_search_query(
                query_text=request.query_text,
                search_type='vector',
                results_count=len(results),
                response_time_ms=response_time_ms,
                ip_address=http_request.client.host if http_request.client else None,
                user_agent=http_request.headers.get('user-agent')
            )
        except Exception as log_error:
            # Don't fail the search if logging fails
            pass

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
