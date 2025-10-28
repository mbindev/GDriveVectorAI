from celery import Celery
from app.main import settings
from app.services.drive_service import download_file
from app.services.embedding_service import get_text_embedding
from app.services.vector_db_service import insert_document
import logging
import PyPDF2
import docx
import io

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
    return text[:5000]  # Limit to first 5000 characters

def extract_text_from_docx(content: bytes) -> str:
    """Extract text from DOCX content."""
    docx_file = io.BytesIO(content)
    doc = docx.Document(docx_file)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text[:5000]  # Limit to first 5000 characters

def extract_text_from_txt(content: bytes) -> str:
    """Extract text from TXT content."""
    return content.decode('utf-8', errors='ignore')[:5000]

@app.task
def process_and_embed_document(drive_file_id: str, file_name: str, mime_type: str, drive_url: str):
    """Process a document: download, extract text, generate embedding, and store."""
    try:
        logger.info(f"Processing document: {file_name}")
        
        # Download the file
        content = download_file(drive_file_id, file_name)
        
        # Extract text based on mime type
        if mime_type == 'application/pdf':
            text = extract_text_from_pdf(content)
        elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            text = extract_text_from_docx(content)
        elif mime_type.startswith('text/'):
            text = extract_text_from_txt(content)
        else:
            logger.warning(f"Unsupported mime type: {mime_type} for file {file_name}")
            return
        
        if not text.strip():
            logger.warning(f"No text extracted from {file_name}")
            return
        
        # Generate embedding
        embedding = get_text_embedding(text)
        
        # Store in database
        insert_document(drive_file_id, file_name, mime_type, drive_url, text[:500], embedding)
        
        logger.info(f"Successfully processed and embedded document: {file_name}")
        
    except Exception as e:
        logger.error(f"Failed to process document {file_name}: {str(e)}")
        raise
