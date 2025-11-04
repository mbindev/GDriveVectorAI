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

        # Update status to processing
        update_document_status(drive_file_id, 'processing')
        add_processing_log(drive_file_id, 'info', f"Started processing {file_name}", job_id)

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
            full_text_length=full_text_length
        )

        add_processing_log(drive_file_id, 'info', "Successfully completed processing", job_id)
        logger.info(f"Successfully processed and embedded document: {file_name}")

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
