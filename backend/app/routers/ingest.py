from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.drive_service import list_files_in_folder
from app.tasks import process_and_embed_document
from app.services.vector_db_service import (
    create_ingestion_job,
    create_document_record,
    create_or_update_folder
)
import uuid

router = APIRouter()

class IngestRequest(BaseModel):
    folder_id: str
    folder_name: Optional[str] = None
    description: Optional[str] = None

@router.post("/start")
async def start_ingestion(request: IngestRequest):
    """Start ingestion process for a Google Drive folder."""
    try:
        # List files from Google Drive
        files = list_files_in_folder(request.folder_id)

        if not files:
            raise HTTPException(status_code=404, detail="No files found in the specified folder")

        # Create or update folder record
        folder_name = request.folder_name or f"Folder {request.folder_id}"
        create_or_update_folder(request.folder_id, folder_name, request.description)

        # Create a job record
        job_id = str(uuid.uuid4())
        create_ingestion_job(job_id, request.folder_id, len(files))

        # Create document records and enqueue processing tasks
        for file_info in files:
            # Create initial document record with pending status
            create_document_record(
                drive_file_id=file_info['id'],
                file_name=file_info['name'],
                mime_type=file_info['mimeType'],
                drive_url=file_info.get('webViewLink', ''),
                folder_id=request.folder_id,
                job_id=job_id
            )

            # Enqueue Celery task for processing
            process_and_embed_document.delay(
                drive_file_id=file_info['id'],
                file_name=file_info['name'],
                mime_type=file_info['mimeType'],
                drive_url=file_info.get('webViewLink', ''),
                folder_id=request.folder_id,
                job_id=job_id
            )

        return {
            "message": f"Started ingestion of {len(files)} files",
            "job_id": job_id,
            "folder_id": request.folder_id,
            "total_files": len(files),
            "files": [{"id": f['id'], "name": f['name']} for f in files]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingest failed: {str(e)}")
