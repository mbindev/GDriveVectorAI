from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from app.services.vector_db_service import (
    get_all_documents,
    get_document_by_id,
    delete_document,
    get_documents_count,
    get_logs_for_document
)

router = APIRouter()

class DocumentResponse(BaseModel):
    id: int
    drive_file_id: str
    file_name: str
    mime_type: str
    drive_url: Optional[str]
    folder_id: Optional[str]
    extracted_text_snippet: Optional[str]
    full_text_length: Optional[int]
    status: str
    error_message: Optional[str]
    job_id: Optional[str]
    created_at: str
    updated_at: str
    processed_at: Optional[str]

@router.get("/")
async def list_documents(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None,
    folder_id: Optional[str] = None
):
    """Get all documents with pagination and filtering."""
    try:
        documents = get_all_documents(limit=limit, offset=offset, status=status, folder_id=folder_id)
        total = get_documents_count(status=status, folder_id=folder_id)

        return {
            "documents": documents,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch documents: {str(e)}")

@router.get("/{drive_file_id}")
async def get_document(drive_file_id: str):
    """Get a specific document by ID."""
    try:
        document = get_document_by_id(drive_file_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        return document
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch document: {str(e)}")

@router.delete("/{drive_file_id}")
async def remove_document(drive_file_id: str):
    """Delete a document."""
    try:
        document = get_document_by_id(drive_file_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        delete_document(drive_file_id)
        return {"message": "Document deleted successfully", "drive_file_id": drive_file_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

@router.get("/{drive_file_id}/logs")
async def get_document_logs(drive_file_id: str):
    """Get processing logs for a specific document."""
    try:
        logs = get_logs_for_document(drive_file_id)
        return {"drive_file_id": drive_file_id, "logs": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch logs: {str(e)}")
