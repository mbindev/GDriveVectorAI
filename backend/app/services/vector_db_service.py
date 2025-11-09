from app.main import get_db_connection
import psycopg2.extras
from typing import List, Dict, Optional
from datetime import datetime
import json

def init_db():
    """Initialize the database - tables are created via init.sql."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
    except Exception as e:
        print(f"Warning: Could not connect to database: {e}")

def insert_document(drive_file_id: str, file_name: str, mime_type: str,
                   drive_url: str, text_snippet: str, embedding: List[float],
                   folder_id: Optional[str] = None, job_id: Optional[str] = None,
                   full_text_length: int = 0, resource_type: str = 'unknown'):
    """Insert a document with its embedding into the database."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO documents (drive_file_id, file_name, mime_type, drive_url,
                                     extracted_text_snippet, embedding, folder_id, job_id,
                                     full_text_length, resource_type, status, processed_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'completed', NOW())
                ON CONFLICT (drive_file_id) DO UPDATE SET
                    file_name = EXCLUDED.file_name,
                    mime_type = EXCLUDED.mime_type,
                    drive_url = EXCLUDED.drive_url,
                    extracted_text_snippet = EXCLUDED.extracted_text_snippet,
                    embedding = EXCLUDED.embedding,
                    folder_id = EXCLUDED.folder_id,
                    job_id = EXCLUDED.job_id,
                    full_text_length = EXCLUDED.full_text_length,
                    resource_type = EXCLUDED.resource_type,
                    status = 'completed',
                    processed_at = NOW(),
                    updated_at = NOW();
            """, (drive_file_id, file_name, mime_type, drive_url, text_snippet, embedding,
                  folder_id, job_id, full_text_length, resource_type))
            conn.commit()

def update_document_status(drive_file_id: str, status: str, error_message: Optional[str] = None):
    """Update document processing status."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE documents
                SET status = %s, error_message = %s, updated_at = NOW()
                WHERE drive_file_id = %s
            """, (status, error_message, drive_file_id))
            conn.commit()

def create_document_record(drive_file_id: str, file_name: str, mime_type: str,
                          drive_url: str, folder_id: Optional[str] = None,
                          job_id: Optional[str] = None):
    """Create initial document record with pending status."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO documents (drive_file_id, file_name, mime_type, drive_url,
                                     folder_id, job_id, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'pending')
                ON CONFLICT (drive_file_id) DO UPDATE SET
                    file_name = EXCLUDED.file_name,
                    mime_type = EXCLUDED.mime_type,
                    drive_url = EXCLUDED.drive_url,
                    folder_id = EXCLUDED.folder_id,
                    job_id = EXCLUDED.job_id,
                    status = 'pending',
                    updated_at = NOW();
            """, (drive_file_id, file_name, mime_type, drive_url, folder_id, job_id))
            conn.commit()

def search_documents(query_embedding: List[float], limit: int = 5) -> List[Dict]:
    """Perform similarity search on documents."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""
                SELECT drive_file_id, file_name, mime_type, drive_url,
                       extracted_text_snippet,
                       1 - (embedding <=> %s::vector) as similarity_score
                FROM documents
                WHERE status = 'completed' AND embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
            """, (query_embedding, query_embedding, limit))

            return [dict(row) for row in cursor.fetchall()]

def get_all_documents(limit: int = 100, offset: int = 0,
                     status: Optional[str] = None, folder_id: Optional[str] = None) -> List[Dict]:
    """Get all documents with pagination and filtering."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            query = """
                SELECT id, drive_file_id, file_name, mime_type, drive_url, folder_id,
                       extracted_text_snippet, full_text_length, status, error_message,
                       job_id, created_at, updated_at, processed_at
                FROM documents
                WHERE 1=1
            """
            params = []

            if status:
                query += " AND status = %s"
                params.append(status)

            if folder_id:
                query += " AND folder_id = %s"
                params.append(folder_id)

            query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

def get_document_by_id(drive_file_id: str) -> Optional[Dict]:
    """Get a single document by ID."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""
                SELECT id, drive_file_id, file_name, mime_type, drive_url, folder_id,
                       extracted_text_snippet, full_text_length, status, error_message,
                       job_id, created_at, updated_at, processed_at
                FROM documents
                WHERE drive_file_id = %s
            """, (drive_file_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

def delete_document(drive_file_id: str):
    """Delete a document from the database."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM documents WHERE drive_file_id = %s", (drive_file_id,))
            conn.commit()

def get_documents_count(status: Optional[str] = None, folder_id: Optional[str] = None) -> int:
    """Get total count of documents."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            query = "SELECT COUNT(*) FROM documents WHERE 1=1"
            params = []

            if status:
                query += " AND status = %s"
                params.append(status)

            if folder_id:
                query += " AND folder_id = %s"
                params.append(folder_id)

            cursor.execute(query, params)
            return cursor.fetchone()[0]

# Job Management Functions
def create_ingestion_job(job_id: str, folder_id: Optional[str] = None, total_files: int = 0) -> str:
    """Create a new ingestion job."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO ingestion_jobs (job_id, folder_id, status, total_files)
                VALUES (%s, %s, 'running', %s)
                RETURNING job_id
            """, (job_id, folder_id, total_files))
            conn.commit()
            return job_id

def update_job_status(job_id: str, status: str, error_message: Optional[str] = None):
    """Update job status."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            completed_at = datetime.now() if status in ['completed', 'failed'] else None
            cursor.execute("""
                UPDATE ingestion_jobs
                SET status = %s, error_message = %s, completed_at = %s
                WHERE job_id = %s
            """, (status, error_message, completed_at, job_id))
            conn.commit()

def update_job_progress(job_id: str, processed_files: int = 0, failed_files: int = 0):
    """Update job progress counters."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE ingestion_jobs
                SET processed_files = processed_files + %s,
                    failed_files = failed_files + %s
                WHERE job_id = %s
            """, (processed_files, failed_files, job_id))
            conn.commit()

def get_job_status(job_id: str) -> Optional[Dict]:
    """Get job status and progress."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""
                SELECT job_id, folder_id, status, total_files, processed_files,
                       failed_files, error_message, started_at, completed_at
                FROM ingestion_jobs
                WHERE job_id = %s
            """, (job_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

def get_all_jobs(limit: int = 50, offset: int = 0) -> List[Dict]:
    """Get all ingestion jobs."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""
                SELECT job_id, folder_id, status, total_files, processed_files,
                       failed_files, error_message, started_at, completed_at
                FROM ingestion_jobs
                ORDER BY started_at DESC
                LIMIT %s OFFSET %s
            """, (limit, offset))
            return [dict(row) for row in cursor.fetchall()]

# Folder Management Functions
def create_or_update_folder(folder_id: str, folder_name: str, description: Optional[str] = None):
    """Create or update a drive folder."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO drive_folders (folder_id, folder_name, description)
                VALUES (%s, %s, %s)
                ON CONFLICT (folder_id) DO UPDATE SET
                    folder_name = EXCLUDED.folder_name,
                    description = EXCLUDED.description,
                    updated_at = NOW()
            """, (folder_id, folder_name, description))
            conn.commit()

def get_all_folders() -> List[Dict]:
    """Get all drive folders."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""
                SELECT folder_id, folder_name, description, is_active, created_at, updated_at
                FROM drive_folders
                ORDER BY created_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

def delete_folder(folder_id: str):
    """Delete a folder."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM drive_folders WHERE folder_id = %s", (folder_id,))
            conn.commit()

# Logging Functions
def add_processing_log(drive_file_id: str, log_level: str, message: str,
                      job_id: Optional[str] = None, details: Optional[Dict] = None):
    """Add a processing log entry."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO processing_logs (drive_file_id, job_id, log_level, message, details)
                VALUES (%s, %s, %s, %s, %s)
            """, (drive_file_id, job_id, log_level, message, json.dumps(details) if details else None))
            conn.commit()

def get_logs_for_job(job_id: str, limit: int = 100) -> List[Dict]:
    """Get logs for a specific job."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""
                SELECT id, drive_file_id, job_id, log_level, message, details, created_at
                FROM processing_logs
                WHERE job_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (job_id, limit))
            return [dict(row) for row in cursor.fetchall()]

def get_logs_for_document(drive_file_id: str) -> List[Dict]:
    """Get logs for a specific document."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""
                SELECT id, drive_file_id, job_id, log_level, message, details, created_at
                FROM processing_logs
                WHERE drive_file_id = %s
                ORDER BY created_at DESC
            """, (drive_file_id,))
            return [dict(row) for row in cursor.fetchall()]

# Statistics Functions
def get_statistics() -> Dict:
    """Get overall statistics."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""
                SELECT
                    COUNT(*) as total_documents,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_documents,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_documents,
                    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_documents,
                    COUNT(CASE WHEN status = 'processing' THEN 1 END) as processing_documents,
                    SUM(full_text_length) as total_text_length,
                    AVG(full_text_length) as avg_text_length
                FROM documents
            """)
            doc_stats = dict(cursor.fetchone())

            cursor.execute("""
                SELECT
                    COUNT(*) as total_jobs,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_jobs,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_jobs,
                    COUNT(CASE WHEN status = 'running' THEN 1 END) as running_jobs
                FROM ingestion_jobs
            """)
            job_stats = dict(cursor.fetchone())

            cursor.execute("""
                SELECT COUNT(*) as total_folders
                FROM drive_folders
            """)
            folder_stats = dict(cursor.fetchone())

            return {**doc_stats, **job_stats, **folder_stats}
