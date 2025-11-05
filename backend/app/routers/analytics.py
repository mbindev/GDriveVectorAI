from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.services.analytics_service import (
    get_search_history,
    get_popular_searches,
    get_search_analytics,
    get_api_usage_stats
)

router = APIRouter()

@router.get("/search/history")
async def search_history(
    search_type: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get search history."""
    try:
        history = get_search_history(
            user_id=None,  # TODO: Get from current user
            search_type=search_type,
            days=days,
            limit=limit
        )

        return {
            "history": history,
            "total": len(history),
            "period_days": days
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch search history: {str(e)}")

@router.get("/search/popular")
async def popular_searches(
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(20, ge=1, le=100)
):
    """Get most popular search queries."""
    try:
        popular = get_popular_searches(days=days, limit=limit)

        return {
            "popular_searches": popular,
            "total": len(popular),
            "period_days": days
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch popular searches: {str(e)}")

@router.get("/search/analytics")
async def search_analytics_endpoint(
    days: int = Query(30, ge=1, le=365)
):
    """Get comprehensive search analytics."""
    try:
        analytics = get_search_analytics(days=days)

        return analytics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch search analytics: {str(e)}")

@router.get("/api/usage")
async def api_usage(
    days: int = Query(7, ge=1, le=90)
):
    """Get API usage statistics."""
    try:
        stats = get_api_usage_stats(days=days)

        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch API usage stats: {str(e)}")
