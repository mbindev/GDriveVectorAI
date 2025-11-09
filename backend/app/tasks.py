from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure
from app.main import settings
from app.services.drive_service import download_file
from app.services.embedding_service import get_text_embedding
from app.services.vector_db_service import (
    insert_document,
    update_document_status,
    update_job_progress,
    update_job_status,
    add_processing_log
)
import logging
import PyPDF2
import docx
import io
from typing import Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Celery
app = Celery('tasks', broker=settings.redis_broker_url)

# Celery Beat Schedule Configuration
app.conf.beat_schedule = {
    'sync-active-folders-every-hour': {
        'task': 'app.tasks.sync_all_active_folders',
        'schedule': 3600.0,  # Every hour
    },
    'cleanup-old-notifications-daily': {
        'task': 'app.tasks.cleanup_old_notifications',
        'schedule': 86400.0,  # Every 24 hours
    },
    'check-scheduled-jobs-every-minute': {
        'task': 'app.tasks.process_scheduled_jobs',
        'schedule': 60.0,  # Every minute
    },
}
app.conf.timezone = 'UTC'

def extract_text_from_pdf(content: bytes) -> str:
    """Extract text from PDF content."""
    pdf_file = io.BytesIO(content)
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
    return text

def extract_text_from_docx(content: bytes) -> str:
    """Extract text from DOCX content."""
    docx_file = io.BytesIO(content)
    doc = docx.Document(docx_file)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text

def extract_text_from_txt(content: bytes) -> str:
    """Extract text from TXT content."""
    return content.decode('utf-8', errors='ignore')

@app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_and_embed_document(self, drive_file_id: str, file_name: str, mime_type: str,
                               drive_url: str, folder_id: Optional[str] = None,
                               job_id: Optional[str] = None):
    """Process a document: download, extract text, generate embedding, and store."""
    try:
        logger.info(f"Processing document: {file_name} (Job: {job_id})")

        # Detect resource type from MIME type
        from app.utils.resource_detector import detect_resource_type
        resource_type = detect_resource_type(mime_type)

        # Update status to processing
        update_document_status(drive_file_id, 'processing')
        add_processing_log(drive_file_id, 'info', f"Started processing {file_name} (type: {resource_type})", job_id)

        # Download the file
        content = download_file(drive_file_id, file_name)
        add_processing_log(drive_file_id, 'info', f"Downloaded file ({len(content)} bytes)", job_id)

        # Extract text based on mime type
        if mime_type == 'application/pdf':
            text = extract_text_from_pdf(content)
        elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            text = extract_text_from_docx(content)
        elif mime_type.startswith('text/'):
            text = extract_text_from_txt(content)
        else:
            error_msg = f"Unsupported mime type: {mime_type}"
            logger.warning(f"{error_msg} for file {file_name}")
            update_document_status(drive_file_id, 'failed', error_msg)
            add_processing_log(drive_file_id, 'warning', error_msg, job_id)
            if job_id:
                update_job_progress(job_id, processed_files=1, failed_files=1)
            return

        if not text.strip():
            error_msg = "No text extracted from document"
            logger.warning(f"{error_msg}: {file_name}")
            update_document_status(drive_file_id, 'failed', error_msg)
            add_processing_log(drive_file_id, 'warning', error_msg, job_id)
            if job_id:
                update_job_progress(job_id, processed_files=1, failed_files=1)
            return

        full_text_length = len(text)
        text_for_embedding = text[:5000]  # Limit for embedding generation
        add_processing_log(drive_file_id, 'info', f"Extracted {full_text_length} characters", job_id)

        # Generate embedding
        embedding = get_text_embedding(text_for_embedding)
        add_processing_log(drive_file_id, 'info', "Generated embedding", job_id)

        # Store in database
        insert_document(
            drive_file_id=drive_file_id,
            file_name=file_name,
            mime_type=mime_type,
            drive_url=drive_url,
            text_snippet=text[:500],
            embedding=embedding,
            folder_id=folder_id,
            job_id=job_id,
            full_text_length=full_text_length,
            resource_type=resource_type
        )

        add_processing_log(drive_file_id, 'info', "Successfully completed processing", job_id)
        logger.info(f"Successfully processed and embedded document: {file_name}")

        # Enrich document metadata with AI analysis (async, non-blocking)
        try:
            from app.services.enrichment_service import enrich_document_metadata
            enrich_document_metadata(drive_file_id, text)
            add_processing_log(drive_file_id, 'info', "Document metadata enriched", job_id)
        except Exception as enrich_error:
            # Don't fail the job if enrichment fails
            logger.warning(f"Failed to enrich document {file_name}: {str(enrich_error)}")
            add_processing_log(drive_file_id, 'warning', f"Enrichment failed: {str(enrich_error)}", job_id)

        # Update job progress
        if job_id:
            update_job_progress(job_id, processed_files=1)
            # Check if job is complete
            check_and_complete_job(job_id)

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to process document {file_name}: {error_msg}")

        # Update document status to failed
        update_document_status(drive_file_id, 'failed', error_msg)
        add_processing_log(drive_file_id, 'error', f"Processing failed: {error_msg}", job_id,
                          details={"exception": type(e).__name__})

        # Update job progress
        if job_id:
            update_job_progress(job_id, processed_files=1, failed_files=1)

        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying document {file_name} (attempt {self.request.retries + 1})")
            add_processing_log(drive_file_id, 'info',
                             f"Retrying processing (attempt {self.request.retries + 1})", job_id)
            raise self.retry(exc=e)
        else:
            logger.error(f"Max retries exceeded for document {file_name}")
            add_processing_log(drive_file_id, 'error', "Max retries exceeded", job_id)

def check_and_complete_job(job_id: str):
    """Check if all documents in a job are processed and mark job as complete."""
    from app.services.vector_db_service import get_job_status

    try:
        job = get_job_status(job_id)
        if job:
            total = job['total_files']
            processed = job['processed_files']

            if processed >= total:
                # All files processed
                failed = job['failed_files']
                if failed > 0:
                    update_job_status(job_id, 'completed',
                                    f"Completed with {failed} failed files")
                else:
                    update_job_status(job_id, 'completed')
                logger.info(f"Job {job_id} completed: {processed}/{total} files processed, {failed} failed")
    except Exception as e:
        logger.error(f"Error checking job completion for {job_id}: {str(e)}")

# Celery signal handlers for monitoring
@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **extra):
    """Handler called before task execution."""
    logger.info(f"Task {task.name} [{task_id}] starting with args: {args}")

@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None,
                        retval=None, state=None, **extra):
    """Handler called after task execution."""
    logger.info(f"Task {task.name} [{task_id}] finished with state: {state}")

@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, args=None,
                        kwargs=None, traceback=None, einfo=None, **extra):
    """Handler called when task fails."""
    logger.error(f"Task {sender.name} [{task_id}] failed with exception: {exception}")

# ============================================================================
# SCHEDULED TASKS
# ============================================================================

@app.task(name='app.tasks.sync_all_active_folders')
def sync_all_active_folders():
    """Automatically sync all active folders on schedule."""
    from app.services.vector_db_service import get_all_folders
    from app.services.drive_service import list_files_in_folder
    from app.routers.ingest import start_ingestion_internal

    try:
        logger.info("Starting scheduled sync of all active folders")
        folders = get_all_folders()
        active_folders = [f for f in folders if f.get('is_active', True)]

        synced_count = 0
        for folder in active_folders:
            try:
                folder_id = folder['folder_id']
                folder_name = folder['folder_name']

                logger.info(f"Syncing folder: {folder_name} ({folder_id})")

                # Check if folder has any new files
                files = list_files_in_folder(folder_id)
                if files:
                    # Start ingestion for this folder
                    job_id = start_ingestion_internal(folder_id)
                    logger.info(f"Started sync job {job_id} for folder {folder_name}")
                    synced_count += 1
                else:
                    logger.info(f"No new files in folder {folder_name}")

            except Exception as e:
                logger.error(f"Failed to sync folder {folder.get('folder_name', 'unknown')}: {str(e)}")
                continue

        logger.info(f"Scheduled sync completed: {synced_count} folders synced")
        return {"synced_folders": synced_count, "total_active_folders": len(active_folders)}

    except Exception as e:
        logger.error(f"Scheduled sync failed: {str(e)}")
        raise

@app.task(name='app.tasks.cleanup_old_notifications')
def cleanup_old_notifications():
    """Clean up old read notifications (older than 30 days)."""
    from app.main import get_db_connection
    from datetime import datetime, timedelta

    try:
        logger.info("Starting cleanup of old notifications")
        cutoff_date = datetime.utcnow() - timedelta(days=30)

        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM notifications
                    WHERE is_read = true AND created_at < %s
                    RETURNING id
                """, (cutoff_date,))
                deleted_count = len(cursor.fetchall())
                conn.commit()

        logger.info(f"Cleaned up {deleted_count} old notifications")
        return {"deleted_notifications": deleted_count}

    except Exception as e:
        logger.error(f"Notification cleanup failed: {str(e)}")
        raise

@app.task(name='app.tasks.process_scheduled_jobs')
def process_scheduled_jobs():
    """Process scheduled jobs from the database."""
    from app.main import get_db_connection
    from datetime import datetime
    import json

    try:
        logger.info("Checking for scheduled jobs to process")

        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Find jobs that are due to run
                cursor.execute("""
                    SELECT id, job_type, folder_id, schedule_type, next_run_at, config
                    FROM scheduled_jobs
                    WHERE is_active = true
                    AND next_run_at <= %s
                    ORDER BY next_run_at
                """, (datetime.utcnow(),))

                jobs = cursor.fetchall()

                for job in jobs:
                    job_id, job_type, folder_id, schedule_type, next_run_at, config = job

                    try:
                        logger.info(f"Processing scheduled job {job_id}: {job_type}")

                        # Execute the scheduled job based on type
                        if job_type == 'folder_sync':
                            from app.routers.ingest import start_ingestion_internal
                            ingestion_job_id = start_ingestion_internal(folder_id)
                            logger.info(f"Started ingestion job {ingestion_job_id} from scheduled job {job_id}")

                        # Update last run and calculate next run
                        cursor.execute("""
                            UPDATE scheduled_jobs
                            SET last_run_at = %s,
                                next_run_at = calculate_next_run(%s, %s),
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s
                        """, (datetime.utcnow(), schedule_type, next_run_at, job_id))

                    except Exception as e:
                        logger.error(f"Failed to process scheduled job {job_id}: {str(e)}")
                        # Mark job as failed but don't stop processing other jobs
                        cursor.execute("""
                            UPDATE scheduled_jobs
                            SET updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s
                        """, (job_id,))

                conn.commit()

        logger.info(f"Processed {len(jobs)} scheduled jobs")
        return {"processed_jobs": len(jobs)}

    except Exception as e:
        logger.error(f"Scheduled job processing failed: {str(e)}")
        raise
