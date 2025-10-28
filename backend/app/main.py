from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import psycopg2
from google.cloud import secretmanager_v1 as secretmanager
import os
from contextlib import contextmanager

app = FastAPI(title="DriveVectorAI Backend", version="1.0.0")

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    try:
        from app.services.vector_db_service import init_db
        init_db()
    except Exception as e:
        print(f"Warning: Could not initialize database on startup: {e}")
        # Don't fail startup if DB is not ready yet

# Pydantic Settings for configuration
class Settings(BaseModel):
    google_project_id: str = os.getenv("GOOGLE_PROJECT_ID", "")
    secret_manager_db_secret_id: str = os.getenv("SECRET_MANAGER_DB_SECRET_ID", "")
    drive_folder_id: str = os.getenv("DRIVE_FOLDER_ID", "")
    gcs_bucket_name: Optional[str] = os.getenv("GCS_BUCKET_NAME")
    redis_broker_url: str = os.getenv("REDIS_BROKER_URL", "redis://redis:6379/0")

settings = Settings()

# Global database connection cache
db_credentials = None

def get_secret(secret_id: str) -> str:
    """Fetch a secret from Google Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{settings.google_project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

def refresh_db_credentials():
    """Refresh database credentials from Secret Manager."""
    global db_credentials
    try:
        db_secret = get_secret(settings.secret_manager_db_secret_id)
        # Assuming the secret is a JSON string with keys: host, port, dbname, user, password
        import json
        db_credentials = json.loads(db_secret)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh DB credentials: {str(e)}")

@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    if db_credentials is None:
        refresh_db_credentials()

    conn = psycopg2.connect(
        host=db_credentials["host"],
        port=db_credentials.get("port", 5432),
        dbname=db_credentials["dbname"],
        user=db_credentials["user"],
        password=db_credentials["password"]
    )
    try:
        yield conn
    finally:
        conn.close()

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

@app.post("/secrets/refresh")
async def refresh_secrets():
    """Manually trigger refresh of database credentials."""
    try:
        refresh_db_credentials()
        return {"message": "Database credentials refreshed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Import and include routers
from app.routers import ingest, search, llm, settings

app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(llm.router, prefix="/llm", tags=["llm"])
app.include_router(settings.router, prefix="/settings", tags=["settings"])
