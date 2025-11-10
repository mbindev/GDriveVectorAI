"""
Scanner Service
Recursive Google Drive folder scanning with 100% progress tracking.
"""
import logging
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from googleapiclient.discovery import build
from app.services.google_drive_service import get_drive_service

logger = logging.getLogger(__name__)


def get_db_connection():
    """Get database connection."""
    from app.services.vector_db_service import get_db_connection as get_conn
    return get_conn()


def create_scan_session(
    folder_id: str,
    scan_type: str = 'full',
    started_by: Optional[int] = None
) -> int:
    """
    Create a new scan session.
    
    Args:
        folder_id: Google Drive folder ID
        scan_type: 'full', 'incremental', or 'manual'
        started_by: User ID who started the scan
        
    Returns:
        Scan session ID
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO scan_sessions (folder_id, scan_type, status, started_at, started_by)
            VALUES (%s, %s, 'in_progress', NOW(), %s)
            RETURNING id
        """, (folder_id, scan_type, started_by))
        
        session_id = cur.fetchone()[0]
        conn.commit()
        
        logger.info(f"Created scan session {session_id} for folder {folder_id}")
        return session_id
    finally:
        cur.close()
        conn.close()


def update_scan_session(
    session_id: int,
    status: Optional[str] = None,
    total_items: Optional[int] = None,
    scanned_items: Optional[int] = None,
    new_items_found: Optional[int] = None,
    changed_items_found: Optional[int] = None,
    total_size_bytes: Optional[int] = None,
    error_message: Optional[str] = None
) -> None:
    """Update scan session progress."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        updates = []
        params = []
        
        if status is not None:
            updates.append("status = %s")
            params.append(status)
            if status in ['completed', 'failed']:
                updates.append("completed_at = NOW()")
                
        if total_items is not None:
            updates.append("total_items = %s")
            params.append(total_items)
            
        if scanned_items is not None:
            updates.append("scanned_items = %s")
            params.append(scanned_items)
            
        if new_items_found is not None:
            updates.append("new_items_found = %s")
            params.append(new_items_found)
            
        if changed_items_found is not None:
            updates.append("changed_items_found = %s")
            params.append(changed_items_found)
            
        if total_size_bytes is not None:
            updates.append("total_size_bytes = %s")
            params.append(total_size_bytes)
            
        if error_message is not None:
            updates.append("error_message = %s")
            params.append(error_message)
            
        if not updates:
            return
            
        params.append(session_id)
        query = f"UPDATE scan_sessions SET {', '.join(updates)} WHERE id = %s"
        
        cur.execute(query, params)
        conn.commit()
    finally:
        cur.close()
        conn.close()


def add_scan_item(
    session_id: int,
    item_path: str,
    item_type: str,
    item_id: str,
    status: str = 'scanned',
    file_size_bytes: Optional[int] = None,
    error_message: Optional[str] = None
) -> None:
    """Add an item to scan progress tracking."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO scan_progress (session_id, item_path, item_type, item_id, status, file_size_bytes, error_message, processed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        """, (session_id, item_path, item_type, item_id, status, file_size_bytes, error_message))
        
        conn.commit()
    finally:
        cur.close()
        conn.close()


def count_folder_items_recursive(drive_service, folder_id: str, path: str = "") -> Tuple[int, int]:
    """
    Recursively count all files and folders in a Google Drive folder.
    
    Args:
        drive_service: Google Drive API service
        folder_id: Folder ID to count
        path: Current path (for logging)
        
    Returns:
        Tuple of (total_items, total_size_bytes)
    """
    total_items = 0
    total_size = 0
    page_token = None
    
    try:
        while True:
            # List all items in this folder
            response = drive_service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields="nextPageToken, files(id, name, mimeType, size, modifiedTime)",
                pageToken=page_token,
                pageSize=1000
            ).execute()
            
            items = response.get('files', [])
            total_items += len(items)
            
            for item in items:
                # Add file size
                if 'size' in item:
                    total_size += int(item['size'])
                
                # Recursively count subfolders
                if item.get('mimeType') == 'application/vnd.google-apps.folder':
                    subfolder_items, subfolder_size = count_folder_items_recursive(
                        drive_service,
                        item['id'],
                        f"{path}/{item['name']}"
                    )
                    total_items += subfolder_items
                    total_size += subfolder_size
            
            page_token = response.get('nextPageToken')
            if not page_token:
                break
                
    except Exception as e:
        logger.error(f"Error counting items in {path}: {e}")
        
    return total_items, total_size


def scan_folder_recursive(
    drive_service,
    folder_id: str,
    session_id: int,
    path: str = "",
    scanned_count: int = 0
) -> Tuple[int, int, int]:
    """
    Recursively scan a Google Drive folder and track progress.
    
    Args:
        drive_service: Google Drive API service
        folder_id: Folder ID to scan
        session_id: Scan session ID
        path: Current path
        scanned_count: Running count of scanned items
        
    Returns:
        Tuple of (scanned_items, new_items, changed_items)
    """
    new_items = 0
    changed_items = 0
    page_token = None
    
    try:
        while True:
            # List all items in this folder
            response = drive_service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, webViewLink)",
                pageToken=page_token,
                pageSize=100  # Smaller batches for better progress tracking
            ).execute()
            
            items = response.get('files', [])
            
            for item in items:
                item_id = item['id']
                item_name = item['name']
                item_mime = item.get('mimeType', '')
                item_size = int(item.get('size', 0))
                item_path = f"{path}/{item_name}"
                
                scanned_count += 1
                
                # Check if item exists in database
                is_new = not document_exists(item_id)
                
                if is_new:
                    new_items += 1
                    
                # Add to scan progress
                item_type = 'folder' if item_mime == 'application/vnd.google-apps.folder' else 'file'
                add_scan_item(
                    session_id=session_id,
                    item_path=item_path,
                    item_type=item_type,
                    item_id=item_id,
                    status='scanned',
                    file_size_bytes=item_size if item_type == 'file' else None
                )
                
                # Update session progress
                update_scan_session(session_id, scanned_items=scanned_count)
                
                # If it's a folder, recursively scan it
                if item_mime == 'application/vnd.google-apps.folder':
                    sub_scanned, sub_new, sub_changed = scan_folder_recursive(
                        drive_service,
                        item_id,
                        session_id,
                        item_path,
                        scanned_count
                    )
                    scanned_count = sub_scanned
                    new_items += sub_new
                    changed_items += sub_changed
                else:
                    # Check if file should be queued for processing
                    if is_new and is_processable_file(item_mime):
                        # Queue for processing (will be done by existing ingestion system)
                        logger.info(f"New processable file found: {item_path}")
            
            page_token = response.get('nextPageToken')
            if not page_token:
                break
                
    except Exception as e:
        logger.error(f"Error scanning {path}: {e}")
        add_scan_item(
            session_id=session_id,
            item_path=path,
            item_type='folder',
            item_id=folder_id,
            status='failed',
            error_message=str(e)
        )
        
    return scanned_count, new_items, changed_items


def document_exists(drive_file_id: str) -> bool:
    """Check if a document already exists in the database."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT 1 FROM documents WHERE drive_file_id = %s LIMIT 1", (drive_file_id,))
        return cur.fetchone() is not None
    finally:
        cur.close()
        conn.close()


def is_processable_file(mime_type: str) -> bool:
    """Check if a file type can be processed."""
    processable_types = [
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain',
        'application/vnd.google-apps.document'
    ]
    return mime_type in processable_types


def perform_full_scan(folder_id: str, started_by: Optional[int] = None) -> Dict[str, Any]:
    """
    Perform a complete scan of a folder and all subfolders.
    
    Args:
        folder_id: Google Drive folder ID
        started_by: User ID who started the scan
        
    Returns:
        Dict with scan results
    """
    drive_service = get_drive_service()
    
    # Create scan session
    session_id = create_scan_session(folder_id, 'full', started_by)
    
    try:
        # Step 1: Count total items (for progress percentage)
        logger.info(f"Counting items in folder {folder_id}...")
        total_items, total_size = count_folder_items_recursive(drive_service, folder_id)
        
        update_scan_session(
            session_id,
            total_items=total_items,
            total_size_bytes=total_size
        )
        
        logger.info(f"Total items to scan: {total_items} ({total_size / 1024 / 1024:.2f} MB)")
        
        # Step 2: Recursive scan
        logger.info(f"Starting recursive scan...")
        scanned_count, new_items, changed_items = scan_folder_recursive(
            drive_service,
            folder_id,
            session_id
        )
        
        # Step 3: Update folder stats
        update_folder_scan_stats(folder_id, total_items, scanned_count, 'completed')
        
        # Step 4: Complete session
        update_scan_session(
            session_id,
            status='completed',
            scanned_items=scanned_count,
            new_items_found=new_items,
            changed_items_found=changed_items
        )
        
        logger.info(f"Scan complete: {scanned_count}/{total_items} items, {new_items} new, {changed_items} changed")
        
        return {
            "session_id": session_id,
            "status": "completed",
            "total_items": total_items,
            "scanned_items": scanned_count,
            "new_items": new_items,
            "changed_items": changed_items,
            "total_size_bytes": total_size,
            "completion_percentage": round((scanned_count / total_items * 100) if total_items > 0 else 100, 2)
        }
        
    except Exception as e:
        logger.error(f"Scan failed: {e}")
        update_scan_session(session_id, status='failed', error_message=str(e))
        update_folder_scan_stats(folder_id, 0, 0, 'failed')
        raise


def update_folder_scan_stats(folder_id: str, total_items: int, scanned_items: int, status: str) -> None:
    """Update folder scan statistics."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            UPDATE drive_folders
            SET last_scan_at = NOW(),
                last_scan_status = %s,
                total_items_count = %s,
                scanned_items_count = %s
            WHERE folder_id = %s
        """, (status, total_items, scanned_items, folder_id))
        
        conn.commit()
    finally:
        cur.close()
        conn.close()


def get_scan_session_progress(session_id: int) -> Optional[Dict[str, Any]]:
    """Get real-time progress of a scan session."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT id, folder_id, scan_type, status, total_items, scanned_items,
                   new_items_found, changed_items_found, total_size_bytes,
                   error_message, started_at, completed_at
            FROM scan_sessions
            WHERE id = %s
        """, (session_id,))
        
        row = cur.fetchone()
        if not row:
            return None
            
        completion_pct = 0
        if row[4] and row[5]:  # total_items and scanned_items
            completion_pct = round((row[5] / row[4] * 100), 2)
            
        return {
            "id": row[0],
            "folder_id": row[1],
            "scan_type": row[2],
            "status": row[3],
            "total_items": row[4],
            "scanned_items": row[5],
            "new_items_found": row[6],
            "changed_items_found": row[7],
            "total_size_bytes": row[8],
            "total_size_mb": round(row[8] / 1024 / 1024, 2) if row[8] else 0,
            "error_message": row[9],
            "started_at": row[10].isoformat() if row[10] else None,
            "completed_at": row[11].isoformat() if row[11] else None,
            "completion_percentage": completion_pct
        }
    finally:
        cur.close()
        conn.close()


def send_scan_notification(session_id: int, status: str, message: str) -> None:
    """Send notification about scan completion/failure."""
    try:
        from app.services.notification_service import create_notification
        
        create_notification(
            user_id=None,  # System notification
            notification_type='in_app',
            category='scan_completed' if status == 'completed' else 'scan_failed',
            title=f"Scan {status.title()}",
            message=message,
            metadata={"session_id": session_id, "status": status}
        )
    except Exception as e:
        logger.error(f"Failed to send scan notification: {e}")
