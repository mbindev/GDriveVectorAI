from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.vector_db_service import (
    create_or_update_folder,
    get_all_folders,
    delete_folder
)

router = APIRouter()

class FolderCreate(BaseModel):
    folder_id: str
    folder_name: str
    description: Optional[str] = None

class FolderUpdate(BaseModel):
    folder_name: str
    description: Optional[str] = None

@router.get("/")
async def list_folders():
    """Get all drive folders."""
    try:
        folders = get_all_folders()
        return {"folders": folders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch folders: {str(e)}")

@router.post("/")
async def create_folder(folder: FolderCreate):
    """Create or update a drive folder."""
    try:
        create_or_update_folder(folder.folder_id, folder.folder_name, folder.description)
        return {"message": "Folder created/updated successfully", "folder_id": folder.folder_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create/update folder: {str(e)}")

@router.put("/{folder_id}")
async def update_folder(folder_id: str, folder: FolderUpdate):
    """Update a drive folder."""
    try:
        create_or_update_folder(folder_id, folder.folder_name, folder.description)
        return {"message": "Folder updated successfully", "folder_id": folder_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update folder: {str(e)}")

@router.delete("/{folder_id}")
async def remove_folder(folder_id: str):
    """Delete a drive folder."""
    try:
        delete_folder(folder_id)
        return {"message": "Folder deleted successfully", "folder_id": folder_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete folder: {str(e)}")
