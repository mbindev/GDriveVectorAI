from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from app.main import get_db_connection
import psycopg2.extras

router = APIRouter()

class ScheduledJobCreate(BaseModel):
    name: str
    job_type: str  # 'folder_sync', 'cleanup', etc.
    folder_id: Optional[str] = None
    schedule_type: str  # 'hourly', 'daily', 'weekly', 'cron'
    cron_expression: Optional[str] = None
    config: Optional[Dict] = None

class ScheduledJobUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    schedule_type: Optional[str] = None
    cron_expression: Optional[str] = None
    config: Optional[Dict] = None

@router.get("/")
async def list_scheduled_jobs(
    is_active: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """List all scheduled jobs."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                query = "SELECT * FROM scheduled_jobs WHERE 1=1"
                params = []

                if is_active is not None:
                    query += " AND is_active = %s"
                    params.append(is_active)

                query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])

                cursor.execute(query, params)
                jobs = [dict(row) for row in cursor.fetchall()]

                # Get total count
                count_query = "SELECT COUNT(*) FROM scheduled_jobs WHERE 1=1"
                count_params = []
                if is_active is not None:
                    count_query += " AND is_active = %s"
                    count_params.append(is_active)

                cursor.execute(count_query, count_params)
                total = cursor.fetchone()['count']

                return {
                    "jobs": jobs,
                    "total": total,
                    "limit": limit,
                    "offset": offset
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch scheduled jobs: {str(e)}")

@router.get("/{job_id}")
async def get_scheduled_job(job_id: int):
    """Get a specific scheduled job."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM scheduled_jobs WHERE id = %s", (job_id,))
                job = cursor.fetchone()

                if not job:
                    raise HTTPException(status_code=404, detail="Scheduled job not found")

                return dict(job)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch scheduled job: {str(e)}")

@router.post("/")
async def create_scheduled_job(job: ScheduledJobCreate):
    """Create a new scheduled job."""
    try:
        # Calculate next run time based on schedule type
        next_run_at = calculate_next_run_time(job.schedule_type, job.cron_expression)

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    INSERT INTO scheduled_jobs (
                        name, job_type, folder_id, schedule_type,
                        cron_expression, next_run_at, config, is_active
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, true)
                    RETURNING *
                """, (
                    job.name,
                    job.job_type,
                    job.folder_id,
                    job.schedule_type,
                    job.cron_expression,
                    next_run_at,
                    psycopg2.extras.Json(job.config) if job.config else None
                ))
                result = dict(cursor.fetchone())
                conn.commit()

                return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create scheduled job: {str(e)}")

@router.put("/{job_id}")
async def update_scheduled_job(job_id: int, job: ScheduledJobUpdate):
    """Update a scheduled job."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                updates = []
                params = []

                if job.name is not None:
                    updates.append("name = %s")
                    params.append(job.name)

                if job.is_active is not None:
                    updates.append("is_active = %s")
                    params.append(job.is_active)

                if job.schedule_type is not None:
                    updates.append("schedule_type = %s")
                    params.append(job.schedule_type)
                    # Recalculate next run time
                    next_run_at = calculate_next_run_time(job.schedule_type, job.cron_expression)
                    updates.append("next_run_at = %s")
                    params.append(next_run_at)

                if job.cron_expression is not None:
                    updates.append("cron_expression = %s")
                    params.append(job.cron_expression)

                if job.config is not None:
                    updates.append("config = %s")
                    params.append(psycopg2.extras.Json(job.config))

                if not updates:
                    raise HTTPException(status_code=400, detail="No fields to update")

                updates.append("updated_at = CURRENT_TIMESTAMP")
                params.append(job_id)

                query = f"UPDATE scheduled_jobs SET {', '.join(updates)} WHERE id = %s"
                cursor.execute(query, params)
                conn.commit()

                if cursor.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Scheduled job not found")

                return {"message": "Scheduled job updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update scheduled job: {str(e)}")

@router.delete("/{job_id}")
async def delete_scheduled_job(job_id: int):
    """Delete a scheduled job."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM scheduled_jobs WHERE id = %s", (job_id,))
                conn.commit()

                if cursor.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Scheduled job not found")

                return {"message": "Scheduled job deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete scheduled job: {str(e)}")

@router.post("/{job_id}/run")
async def run_scheduled_job_now(job_id: int):
    """Manually trigger a scheduled job to run immediately."""
    try:
        from app.tasks import sync_all_active_folders
        from app.routers.ingest import start_ingestion_internal

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM scheduled_jobs WHERE id = %s", (job_id,))
                job = cursor.fetchone()

                if not job:
                    raise HTTPException(status_code=404, detail="Scheduled job not found")

                job_dict = dict(job)
                job_type = job_dict['job_type']
                folder_id = job_dict['folder_id']

                # Execute the job based on type
                if job_type == 'folder_sync' and folder_id:
                    ingestion_job_id = start_ingestion_internal(folder_id)
                    return {
                        "message": "Scheduled job triggered successfully",
                        "ingestion_job_id": ingestion_job_id
                    }
                elif job_type == 'sync_all':
                    sync_all_active_folders.delay()
                    return {"message": "Scheduled job triggered successfully (async)"}
                else:
                    raise HTTPException(status_code=400, detail=f"Unsupported job type: {job_type}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run scheduled job: {str(e)}")

def calculate_next_run_time(schedule_type: str, cron_expression: Optional[str] = None) -> datetime:
    """Calculate the next run time based on schedule type."""
    now = datetime.utcnow()

    if schedule_type == 'hourly':
        return now + timedelta(hours=1)
    elif schedule_type == 'daily':
        return now + timedelta(days=1)
    elif schedule_type == 'weekly':
        return now + timedelta(weeks=1)
    elif schedule_type == 'cron' and cron_expression:
        # Use croniter to parse cron expression
        try:
            from croniter import croniter
            return croniter(cron_expression, now).get_next(datetime)
        except Exception:
            # Fallback to daily if cron parsing fails
            return now + timedelta(days=1)
    else:
        # Default to daily
        return now + timedelta(days=1)
