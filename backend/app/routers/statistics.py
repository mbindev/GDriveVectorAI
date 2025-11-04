from fastapi import APIRouter, HTTPException
from app.services.vector_db_service import get_statistics

router = APIRouter()

@router.get("/")
async def get_stats():
    """Get overall system statistics."""
    try:
        stats = get_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch statistics: {str(e)}")
