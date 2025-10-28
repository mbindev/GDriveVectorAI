from app.main import get_db_connection
import psycopg2.extras
from typing import List, Dict, Tuple

def init_db():
    """Initialize the database with pgvector extension and documents table."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Enable pgvector extension
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                
                # Create documents table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS documents (
                        id SERIAL PRIMARY KEY,
                        drive_file_id TEXT UNIQUE NOT NULL,
                        file_name TEXT NOT NULL,
                        mime_type TEXT NOT NULL,
                        drive_url TEXT,
                        extracted_text_snippet TEXT,
                        embedding VECTOR(768)
                    );
                """)
                
                # Create index on embedding for similarity search
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS documents_embedding_idx 
                    ON documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
                """)
                
                conn.commit()
    except Exception as e:
        print(f"Warning: Could not initialize database: {e}")
        # Don't raise exception - allow app to start even if DB isn't ready

def insert_document(drive_file_id: str, file_name: str, mime_type: str, 
                   drive_url: str, text_snippet: str, embedding: List[float]):
    """Insert a document with its embedding into the database."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO documents (drive_file_id, file_name, mime_type, drive_url, 
                                     extracted_text_snippet, embedding)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (drive_file_id) DO UPDATE SET
                    file_name = EXCLUDED.file_name,
                    mime_type = EXCLUDED.mime_type,
                    drive_url = EXCLUDED.drive_url,
                    extracted_text_snippet = EXCLUDED.extracted_text_snippet,
                    embedding = EXCLUDED.embedding;
            """, (drive_file_id, file_name, mime_type, drive_url, text_snippet, embedding))
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
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
            """, (query_embedding, query_embedding, limit))
            
            return [dict(row) for row in cursor.fetchall()]
