from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from app.services.vector_db_service import (
    get_job_status,
    get_all_jobs,
    get_logs_for_job
)

router = APIRouter()

class JobStatusResponse(BaseModel):
    job_id: str
    folder_id: Optional[str]
    status: str
    total_files: int
    processed_files: int
    failed_files: int
    error_message: Optional[str]
    started_at: str
    completed_at: Optional[str]

@router.get("/")
async def list_jobs(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get all ingestion jobs."""
    try:
        jobs = get_all_jobs(limit=limit, offset=offset)
        return {"jobs": jobs, "total": len(jobs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch jobs: {str(e)}")

@router.get("/{job_id}")
async def get_job(job_id: str):
    """Get status and progress of a specific job."""
    try:
        job = get_job_status(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch job: {str(e)}")

@router.get("/{job_id}/logs")
async def get_job_logs(job_id: str, limit: int = Query(100, ge=1, le=1000)):
    """Get processing logs for a specific job."""
    try:
        logs = get_logs_for_job(job_id, limit=limit)
        return {"job_id": job_id, "logs": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch logs: {str(e)}")
