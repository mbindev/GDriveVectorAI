"""
Scanner API Router
Endpoints for folder scanning and progress tracking.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from app.services import scanner_service

router = APIRouter()


class StartScanRequest(BaseModel):
    folder_id: str
    scan_type: str = 'full'  # 'full' or 'incremental'


@router.post("/start")
async def start_scan(request: StartScanRequest, background_tasks: BackgroundTasks):
    """
    Start a new folder scan in the background.
    
    Returns scan session ID immediately, scan runs async.
    """
    try:
        # Create session
        session_id = scanner_service.create_scan_session(
            folder_id=request.folder_id,
            scan_type=request.scan_type,
            started_by=None  # TODO: Get from current user
        )
        
        # Start scan in background
        background_tasks.add_task(
            scanner_service.perform_full_scan,
            request.folder_id,
            None  # started_by
        )
        
        return {
            "message": "Scan started",
            "session_id": session_id,
            "status": "in_progress"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def list_scan_sessions(folder_id: Optional[str] = None, limit: int = 50):
    """List scan sessions with optional folder filter."""
    try:
        conn = scanner_service.get_db_connection()
        cur = conn.cursor()
        
        query = """
            SELECT id, folder_id, scan_type, status, total_items, scanned_items,
                   new_items_found, started_at, completed_at
            FROM scan_sessions
        """
        params = []
        
        if folder_id:
            query += " WHERE folder_id = %s"
            params.append(folder_id)
            
        query += " ORDER BY started_at DESC LIMIT %s"
        params.append(limit)
        
        cur.execute(query, params)
        rows = cur.fetchall()
        
        sessions = []
        for row in rows:
            completion_pct = 0
            if row[4] and row[5]:
                completion_pct = round((row[5] / row[4] * 100), 2)
                
            sessions.append({
                "id": row[0],
                "folder_id": row[1],
                "scan_type": row[2],
                "status": row[3],
                "total_items": row[4],
                "scanned_items": row[5],
                "new_items_found": row[6],
                "started_at": row[7].isoformat() if row[7] else None,
                "completed_at": row[8].isoformat() if row[8] else None,
                "completion_percentage": completion_pct
            })
        
        cur.close()
        conn.close()
        
        return {"sessions": sessions, "count": len(sessions)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}")
async def get_scan_progress(session_id: int):
    """Get real-time progress of a scan session."""
    try:
        progress = scanner_service.get_scan_session_progress(session_id)
        if not progress:
            raise HTTPException(status_code=404, detail="Scan session not found")
        return progress
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/pause")
async def pause_scan(session_id: int):
    """Pause a running scan (placeholder - would need task management)."""
    try:
        scanner_service.update_scan_session(session_id, status='paused')
        return {"message": "Scan paused", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/resume")
async def resume_scan(session_id: int, background_tasks: BackgroundTasks):
    """Resume a paused scan (placeholder)."""
    try:
        scanner_service.update_scan_session(session_id, status='in_progress')
        # TODO: Implement resume logic
        return {"message": "Scan resumed", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/folder/{folder_id}/progress")
async def get_folder_scan_progress(folder_id: str):
    """Get scan progress for a specific folder."""
    try:
        conn = scanner_service.get_db_connection()
        cur = conn.cursor()
        
        # Get folder scan stats
        cur.execute("""
            SELECT folder_name, last_scan_at, last_scan_status,
                   total_items_count, scanned_items_count
            FROM drive_folders
            WHERE folder_id = %s
        """, (folder_id,))
        
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Folder not found")
        
        completion_pct = 0
        if row[3] and row[4]:
            completion_pct = round((row[4] / row[3] * 100), 2)
        
        # Get latest scan session
        cur.execute("""
            SELECT id, status, started_at, completed_at
            FROM scan_sessions
            WHERE folder_id = %s
            ORDER BY started_at DESC
            LIMIT 1
        """, (folder_id,))
        
        session_row = cur.fetchone()
        latest_session = None
        if session_row:
            latest_session = {
                "id": session_row[0],
                "status": session_row[1],
                "started_at": session_row[2].isoformat() if session_row[2] else None,
                "completed_at": session_row[3].isoformat() if session_row[3] else None
            }
        
        cur.close()
        conn.close()
        
        return {
            "folder_id": folder_id,
            "folder_name": row[0],
            "last_scan_at": row[1].isoformat() if row[1] else None,
            "last_scan_status": row[2],
            "total_items": row[3],
            "scanned_items": row[4],
            "completion_percentage": completion_pct,
            "is_100_percent_complete": completion_pct >= 100,
            "latest_session": latest_session
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_scan_statistics():
    """Get overall scanning statistics across all folders."""
    try:
        conn = scanner_service.get_db_connection()
        cur = conn.cursor()
        
        # Total scans
        cur.execute("SELECT COUNT(*) FROM scan_sessions")
        total_scans = cur.fetchone()[0]
        
        # Completed scans
        cur.execute("SELECT COUNT(*) FROM scan_sessions WHERE status = 'completed'")
        completed_scans = cur.fetchone()[0]
        
        # In progress scans
        cur.execute("SELECT COUNT(*) FROM scan_sessions WHERE status = 'in_progress'")
        in_progress_scans = cur.fetchone()[0]
        
        # Total items scanned
        cur.execute("SELECT SUM(scanned_items) FROM scan_sessions WHERE status = 'completed'")
        total_items_scanned = cur.fetchone()[0] or 0
        
        # Total new items found
        cur.execute("SELECT SUM(new_items_found) FROM scan_sessions WHERE status = 'completed'")
        total_new_items = cur.fetchone()[0] or 0
        
        # Folders with 100% completion
        cur.execute("""
            SELECT COUNT(*) FROM drive_folders
            WHERE total_items_count > 0
              AND scanned_items_count >= total_items_count
              AND last_scan_status = 'completed'
        """)
        fully_scanned_folders = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        return {
            "total_scans": total_scans,
            "completed_scans": completed_scans,
            "in_progress_scans": in_progress_scans,
            "total_items_scanned": total_items_scanned,
            "total_new_items_found": total_new_items,
            "fully_scanned_folders": fully_scanned_folders
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
