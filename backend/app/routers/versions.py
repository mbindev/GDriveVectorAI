from fastapi import APIRouter, HTTPException, Query
from app.services.versioning_service import (
    get_document_versions,
    get_version_details,
    compare_versions,
    get_version_statistics,
    delete_old_versions
)

router = APIRouter()

@router.get("/{drive_file_id}/versions")
async def list_document_versions(
    drive_file_id: str,
    limit: int = Query(50, ge=1, le=100)
):
    """Get all versions of a document."""
    try:
        versions = get_document_versions(drive_file_id, limit=limit)

        return {
            "drive_file_id": drive_file_id,
            "versions": versions,
            "total_versions": len(versions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch versions: {str(e)}")

@router.get("/{drive_file_id}/versions/{version_number}")
async def get_version(drive_file_id: str, version_number: int):
    """Get details of a specific version."""
    try:
        version = get_version_details(drive_file_id, version_number)

        if not version:
            raise HTTPException(status_code=404, detail="Version not found")

        return version
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch version: {str(e)}")

@router.get("/{drive_file_id}/versions/compare")
async def compare_document_versions(
    drive_file_id: str,
    version1: int = Query(..., description="First version number"),
    version2: int = Query(..., description="Second version number")
):
    """Compare two versions of a document."""
    try:
        comparison = compare_versions(drive_file_id, version1, version2)

        if "error" in comparison:
            raise HTTPException(status_code=400, detail=comparison["error"])

        return comparison
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compare versions: {str(e)}")

@router.delete("/{drive_file_id}/versions/cleanup")
async def cleanup_old_versions(
    drive_file_id: str,
    keep_latest: int = Query(10, ge=1, le=100, description="Number of latest versions to keep")
):
    """Delete old versions, keeping only the latest N versions."""
    try:
        deleted_count = delete_old_versions(drive_file_id, keep_latest=keep_latest)

        return {
            "message": f"Deleted {deleted_count} old versions",
            "drive_file_id": drive_file_id,
            "versions_deleted": deleted_count,
            "versions_kept": keep_latest
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cleanup versions: {str(e)}")

@router.get("/statistics")
async def version_statistics():
    """Get statistics about document versions."""
    try:
        stats = get_version_statistics()

        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch statistics: {str(e)}")
