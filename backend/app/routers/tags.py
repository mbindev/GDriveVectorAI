"""
Tag API Router
Endpoints for document tagging and tag management.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Optional
from app.services import tag_service

router = APIRouter()


class TagDocumentRequest(BaseModel):
    document_id: str
    tag_type: str  # 'brand', 'campaign', 'client', 'holiday', 'offer'
    tag_id: int


class BulkTagRequest(BaseModel):
    document_ids: List[str]
    tag_type: str
    tag_id: int


class MultiTagSearchRequest(BaseModel):
    tag_filters: List[Dict[str, any]]  # [{"tag_type": "brand", "tag_id": 1}, ...]
    match_all: bool = False  # AND vs OR


@router.post("/tag-document")
async def tag_document(request: TagDocumentRequest):
    """Tag a single document."""
    try:
        result = tag_service.tag_document(
            document_id=request.document_id,
            tag_type=request.tag_type,
            tag_id=request.tag_id,
            tagged_by=None  # TODO: Get from current user
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/untag-document")
async def untag_document(
    document_id: str = Query(...),
    tag_type: str = Query(...),
    tag_id: int = Query(...)
):
    """Remove a tag from a document."""
    try:
        result = tag_service.untag_document(
            document_id=document_id,
            tag_type=tag_type,
            tag_id=tag_id
        )
        if not result:
            raise HTTPException(status_code=404, detail="Tag not found")
        return {"message": "Tag removed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk-tag")
async def bulk_tag_documents(request: BulkTagRequest):
    """Tag multiple documents at once."""
    try:
        result = tag_service.bulk_tag_documents(
            document_ids=request.document_ids,
            tag_type=request.tag_type,
            tag_id=request.tag_id,
            tagged_by=None  # TODO: Get from current user
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/bulk-untag")
async def bulk_untag_documents(request: BulkTagRequest):
    """Remove tags from multiple documents."""
    try:
        removed = tag_service.bulk_untag_documents(
            document_ids=request.document_ids,
            tag_type=request.tag_type,
            tag_id=request.tag_id
        )
        return {"message": f"Removed {removed} tags", "removed_count": removed}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/document/{document_id}/tags")
async def get_document_tags(document_id: str):
    """Get all tags for a document, grouped by type."""
    try:
        tags = tag_service.get_document_tags(document_id)
        return tags
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents-by-tag")
async def get_documents_by_tag(
    tag_type: str = Query(...),
    tag_id: int = Query(...),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0)
):
    """Get all documents with a specific tag."""
    try:
        documents = tag_service.get_documents_by_tag(
            tag_type=tag_type,
            tag_id=tag_id,
            limit=limit,
            offset=offset
        )
        return {"documents": documents, "count": len(documents)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents-by-multiple-tags")
async def get_documents_by_multiple_tags(request: MultiTagSearchRequest):
    """Get documents matching multiple tag criteria (AND/OR logic)."""
    try:
        documents = tag_service.get_documents_by_multiple_tags(
            tag_filters=request.tag_filters,
            match_all=request.match_all,
            limit=100,
            offset=0
        )
        return {"documents": documents, "count": len(documents), "match_all": request.match_all}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggest-tags/{document_id}")
async def suggest_tags_for_document(document_id: str):
    """Get AI-powered tag suggestions for a document."""
    try:
        suggestions = tag_service.suggest_tags_for_document(document_id)
        return suggestions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_tag_statistics():
    """Get overall tagging statistics."""
    try:
        stats = tag_service.get_tag_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/document/{document_id}/remove-all-tags")
async def remove_all_tags(document_id: str):
    """Remove all tags from a document."""
    try:
        removed = tag_service.remove_all_tags_from_document(document_id)
        return {"message": f"Removed {removed} tags", "removed_count": removed}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
