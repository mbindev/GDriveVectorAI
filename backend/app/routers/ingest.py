from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.drive_service import list_files_in_folder
from app.tasks import process_and_embed_document

router = APIRouter()

class IngestRequest(BaseModel):
    folder_id: str

@router.post("/start")
async def start_ingestion(request: IngestRequest):
    """Start ingestion process for a Google Drive folder."""
    try:
        files = list_files_in_folder(request.folder_id)

        if not files:
            raise HTTPException(status_code=404, detail="No files found in the specified folder")

        # Enqueue processing tasks for each file
        for file_info in files:
            process_and_embed_document.delay(
                drive_file_id=file_info['id'],
                file_name=file_info['name'],
                mime_type=file_info['mimeType'],
                drive_url=file_info.get('webViewLink', '')
            )

        return {
            "message": f"Ingested {len(files)} files for processing",
            "files": [{"id": f['id'], "name": f['name']} for f in files]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingest failed: {str(e)}")
