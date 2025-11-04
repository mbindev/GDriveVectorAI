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

@router.post("/{drive_file_id}/reprocess")
async def reprocess_document(drive_file_id: str):
    """Re-process a document (useful for failed documents)."""
    try:
        from app.services.vector_db_service import update_document_status
        from app.tasks import process_and_embed_document

        # Get document details
        document = get_document_by_id(drive_file_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Reset status to pending
        update_document_status(drive_file_id, 'pending', None)

        # Re-queue the processing task
        process_and_embed_document.delay(
            drive_file_id=document['drive_file_id'],
            file_name=document['file_name'],
            mime_type=document['mime_type'],
            drive_url=document['drive_url'] or '',
            folder_id=document.get('folder_id'),
            job_id=document.get('job_id')
        )

        return {
            "message": "Document queued for re-processing",
            "drive_file_id": drive_file_id,
            "status": "pending"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reprocess document: {str(e)}")

@router.post("/batch/reprocess")
async def batch_reprocess_documents(drive_file_ids: List[str]):
    """Re-process multiple documents."""
    try:
        from app.services.vector_db_service import update_document_status
        from app.tasks import process_and_embed_document

        results = {"queued": [], "not_found": [], "failed": []}

        for drive_file_id in drive_file_ids:
            try:
                document = get_document_by_id(drive_file_id)
                if not document:
                    results["not_found"].append(drive_file_id)
                    continue

                # Reset status
                update_document_status(drive_file_id, 'pending', None)

                # Re-queue
                process_and_embed_document.delay(
                    drive_file_id=document['drive_file_id'],
                    file_name=document['file_name'],
                    mime_type=document['mime_type'],
                    drive_url=document['drive_url'] or '',
                    folder_id=document.get('folder_id'),
                    job_id=document.get('job_id')
                )

                results["queued"].append(drive_file_id)
            except Exception as e:
                results["failed"].append({"drive_file_id": drive_file_id, "error": str(e)})

        return {
            "message": f"Queued {len(results['queued'])} documents for re-processing",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch reprocess failed: {str(e)}")

@router.post("/batch/delete")
async def batch_delete_documents(drive_file_ids: List[str]):
    """Delete multiple documents."""
    try:
        results = {"deleted": [], "not_found": [], "failed": []}

        for drive_file_id in drive_file_ids:
            try:
                document = get_document_by_id(drive_file_id)
                if not document:
                    results["not_found"].append(drive_file_id)
                    continue

                delete_document(drive_file_id)
                results["deleted"].append(drive_file_id)
            except Exception as e:
                results["failed"].append({"drive_file_id": drive_file_id, "error": str(e)})

        return {
            "message": f"Deleted {len(results['deleted'])} documents",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")

@router.get("/export")
async def export_documents(
    format: str = Query("json", regex="^(json|csv)$"),
    status: Optional[str] = None,
    folder_id: Optional[str] = None
):
    """Export documents metadata as JSON or CSV."""
    try:
        documents = get_all_documents(limit=10000, offset=0, status=status, folder_id=folder_id)

        if format == "csv":
            import csv
            import io
            from fastapi.responses import StreamingResponse

            output = io.StringIO()
            if documents:
                writer = csv.DictWriter(output, fieldnames=documents[0].keys())
                writer.writeheader()
                writer.writerows(documents)

            output.seek(0)
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=documents_export.csv"}
            )
        else:
            # JSON format
            from fastapi.responses import JSONResponse
            from datetime import datetime

            # Convert datetime objects to strings
            for doc in documents:
                for key, value in doc.items():
                    if isinstance(value, datetime):
                        doc[key] = value.isoformat()

            return JSONResponse(content={"documents": documents, "total": len(documents)})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
