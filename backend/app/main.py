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
    # Google Cloud Configuration
    google_project_id: str = os.getenv("GOOGLE_PROJECT_ID", "")
    secret_manager_db_secret_id: Optional[str] = os.getenv("SECRET_MANAGER_DB_SECRET_ID")
    drive_folder_id: str = os.getenv("DRIVE_FOLDER_ID", "")
    gcs_bucket_name: Optional[str] = os.getenv("GCS_BUCKET_NAME")

    # Redis Configuration
    redis_broker_url: str = os.getenv("REDIS_BROKER_URL", "redis://redis:6379/0")

    # Direct Database Configuration (fallback if Secret Manager not used)
    db_host: Optional[str] = os.getenv("DB_HOST")
    db_port: int = int(os.getenv("DB_PORT", "5432"))
    db_name: Optional[str] = os.getenv("DB_NAME")
    db_user: Optional[str] = os.getenv("DB_USER")
    db_password: Optional[str] = os.getenv("DB_PASSWORD")

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
    """Refresh database credentials from Secret Manager or environment variables."""
    global db_credentials

    # Try Secret Manager first if configured
    if settings.secret_manager_db_secret_id and settings.google_project_id:
        try:
            db_secret = get_secret(settings.secret_manager_db_secret_id)
            # Assuming the secret is a JSON string with keys: host, port, dbname, user, password
            import json
            db_credentials = json.loads(db_secret)
            print("Database credentials loaded from Secret Manager")
            return
        except Exception as e:
            print(f"Warning: Could not load credentials from Secret Manager: {e}")
            print("Falling back to environment variables...")

    # Fallback to direct environment variables
    if all([settings.db_host, settings.db_name, settings.db_user, settings.db_password]):
        db_credentials = {
            "host": settings.db_host,
            "port": settings.db_port,
            "dbname": settings.db_name,
            "user": settings.db_user,
            "password": settings.db_password
        }
        print("Database credentials loaded from environment variables")
        return

    raise HTTPException(
        status_code=500,
        detail="Database credentials not configured. Set either SECRET_MANAGER_DB_SECRET_ID or direct DB environment variables."
    )

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

# Add rate limiting middleware (optional, can be enabled via env var)
import os
if os.getenv("ENABLE_RATE_LIMITING", "false").lower() == "true":
    from app.middleware.rate_limiter import RateLimitMiddleware
    app.add_middleware(RateLimitMiddleware)

# Import and include routers
from app.routers import ingest, search, llm, settings, documents, jobs, folders, statistics, auth, notifications, scheduled_jobs, enrichment, analytics, versions

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(ingest.router, prefix="/api/ingest", tags=["ingest"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(llm.router, prefix="/api/llm", tags=["llm"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(folders.router, prefix="/api/folders", tags=["folders"])
app.include_router(statistics.router, prefix="/api/statistics", tags=["statistics"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
app.include_router(scheduled_jobs.router, prefix="/api/scheduled-jobs", tags=["scheduled-jobs"])
app.include_router(enrichment.router, prefix="/api/enrichment", tags=["enrichment"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(versions.router, prefix="/api/versions", tags=["versions"])
