from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from app.services.enrichment_service import (
    enrich_document_metadata,
    add_custom_tags,
    remove_custom_tags,
    search_by_metadata
)
from app.services.vector_db_service import get_document_by_id
from app.main import get_db_connection
import psycopg2.extras

router = APIRouter()

class TagsRequest(BaseModel):
    tags: List[str]

@router.post("/{drive_file_id}/enrich")
async def enrich_document(drive_file_id: str):
    """Manually trigger metadata enrichment for a document."""
    try:
        # Get document and extract text
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT drive_file_id, extracted_text_snippet, full_text_length
                    FROM documents
                    WHERE drive_file_id = %s
                """, (drive_file_id,))
                document = cursor.fetchone()

                if not document:
                    raise HTTPException(status_code=404, detail="Document not found")

                # For now, use the snippet for enrichment
                # In production, you might want to store full text or re-download
                text_content = document['extracted_text_snippet'] or ""

                if not text_content:
                    raise HTTPException(status_code=400, detail="No text content available for enrichment")

                # Perform enrichment
                enrichment_data = enrich_document_metadata(drive_file_id, text_content)

                return {
                    "message": "Document enriched successfully",
                    "drive_file_id": drive_file_id,
                    "enrichment": enrichment_data
                }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enrichment failed: {str(e)}")

@router.post("/{drive_file_id}/tags")
async def add_tags_to_document(drive_file_id: str, request: TagsRequest):
    """Add custom tags to a document."""
    try:
        success = add_custom_tags(drive_file_id, request.tags)

        if not success:
            raise HTTPException(status_code=404, detail="Document not found")

        return {
            "message": "Tags added successfully",
            "drive_file_id": drive_file_id,
            "tags": request.tags
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add tags: {str(e)}")

@router.delete("/{drive_file_id}/tags")
async def remove_tags_from_document(drive_file_id: str, request: TagsRequest):
    """Remove custom tags from a document."""
    try:
        success = remove_custom_tags(drive_file_id, request.tags)

        if not success:
            raise HTTPException(status_code=404, detail="Document not found")

        return {
            "message": "Tags removed successfully",
            "drive_file_id": drive_file_id,
            "tags": request.tags
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove tags: {str(e)}")

@router.get("/search")
async def search_documents_by_metadata(
    keywords: Optional[List[str]] = Query(None),
    categories: Optional[List[str]] = Query(None),
    tags: Optional[List[str]] = Query(None),
    language: Optional[str] = None,
    min_sentiment: Optional[float] = Query(None, ge=-1.0, le=1.0),
    max_sentiment: Optional[float] = Query(None, ge=-1.0, le=1.0),
    limit: int = Query(50, ge=1, le=100)
):
    """Search documents by enriched metadata."""
    try:
        results = search_by_metadata(
            keywords=keywords,
            categories=categories,
            tags=tags,
            language=language,
            min_sentiment=min_sentiment,
            max_sentiment=max_sentiment,
            limit=limit
        )

        return {
            "results": results,
            "total": len(results),
            "filters": {
                "keywords": keywords,
                "categories": categories,
                "tags": tags,
                "language": language,
                "sentiment_range": [min_sentiment, max_sentiment] if min_sentiment or max_sentiment else None
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/metadata/stats")
async def get_metadata_statistics():
    """Get statistics about document metadata."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                # Get language distribution
                cursor.execute("""
                    SELECT language, COUNT(*) as count
                    FROM documents
                    WHERE language IS NOT NULL
                    GROUP BY language
                    ORDER BY count DESC
                """)
                language_dist = [dict(row) for row in cursor.fetchall()]

                # Get average sentiment
                cursor.execute("""
                    SELECT AVG(sentiment_score) as avg_sentiment,
                           MIN(sentiment_score) as min_sentiment,
                           MAX(sentiment_score) as max_sentiment
                    FROM documents
                    WHERE sentiment_score IS NOT NULL
                """)
                sentiment_stats = dict(cursor.fetchone())

                # Get most common keywords
                cursor.execute("""
                    SELECT UNNEST(ai_keywords) as keyword, COUNT(*) as count
                    FROM documents
                    WHERE ai_keywords IS NOT NULL AND array_length(ai_keywords, 1) > 0
                    GROUP BY keyword
                    ORDER BY count DESC
                    LIMIT 20
                """)
                top_keywords = [dict(row) for row in cursor.fetchall()]

                # Get most common categories
                cursor.execute("""
                    SELECT UNNEST(ai_categories) as category, COUNT(*) as count
                    FROM documents
                    WHERE ai_categories IS NOT NULL AND array_length(ai_categories, 1) > 0
                    GROUP BY category
                    ORDER BY count DESC
                    LIMIT 10
                """)
                top_categories = [dict(row) for row in cursor.fetchall()]

                # Get enrichment status
                cursor.execute("""
                    SELECT
                        COUNT(*) FILTER (WHERE enriched_at IS NOT NULL) as enriched_count,
                        COUNT(*) FILTER (WHERE enriched_at IS NULL AND status = 'completed') as pending_enrichment,
                        COUNT(*) as total_documents
                    FROM documents
                """)
                enrichment_status = dict(cursor.fetchone())

                return {
                    "language_distribution": language_dist,
                    "sentiment_statistics": sentiment_stats,
                    "top_keywords": top_keywords,
                    "top_categories": top_categories,
                    "enrichment_status": enrichment_status
                }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch statistics: {str(e)}")
