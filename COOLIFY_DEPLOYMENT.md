# Coolify Deployment Guide for DriveVectorAI

This guide explains how to deploy DriveVectorAI on Coolify, a self-hosted PaaS platform.

## Prerequisites

1. Coolify instance running and accessible
2. Google Cloud Project with:
   - Vertex AI API enabled
   - Drive API enabled
   - Service account with appropriate permissions
3. Google Drive folder with documents to ingest

## Deployment Steps

### 1. Create a New Service in Coolify

1. Log into your Coolify dashboard
2. Create a new **Docker Compose** service
3. Connect your Git repository or upload the project

### 2. Configure Environment Variables

In Coolify's environment settings, add the following variables:

#### Required Variables

```env
# Database Configuration (Coolify will inject these automatically if using managed DB)
DB_NAME=drivevectorai
DB_USER=postgres
DB_PASSWORD=<generate-secure-password>
DB_HOST=db
DB_PORT=5432

# Google Cloud Project ID (REQUIRED)
GOOGLE_PROJECT_ID=your-gcp-project-id
```

#### Optional Variables

```env
# If using Google Cloud Secret Manager for DB credentials
SECRET_MANAGER_DB_SECRET_ID=db-credentials

# Google Drive folder ID (can be set per-job in UI)
DRIVE_FOLDER_ID=your-default-folder-id

# Google Cloud Storage bucket
GCS_BUCKET_NAME=your-bucket-name

# Redis configuration (default is usually fine)
REDIS_BROKER_URL=redis://redis:6379/0

# Celery worker concurrency
CELERY_CONCURRENCY=4

# Service ports (usually handled by Coolify)
FRONTEND_PORT=3000
BACKEND_PORT=8000
```

### 3. Google Cloud Authentication

Coolify needs access to your Google Cloud service account. Choose one method:

#### Option A: Service Account Key (Simpler for testing)

1. Create a service account key JSON file in Google Cloud Console
2. In Coolify, add the contents as a **Secret** or **File**
3. Mount it in the docker-compose.yml:
   ```yaml
   backend:
     volumes:
       - /path/to/credentials.json:/app/credentials.json:ro
     environment:
       GOOGLE_APPLICATION_CREDENTIALS: /app/credentials.json
   ```

#### Option B: Workload Identity (Recommended for production)

Configure GKE Workload Identity if running on GKE, or use Google's Application Default Credentials.

### 4. Deploy

1. Click **Deploy** in Coolify
2. Coolify will:
   - Build the Docker images
   - Create the necessary containers (db, backend, frontend, redis, celery_worker)
   - Apply health checks
   - Set up networking

### 5. Verify Deployment

Once deployed, verify the services are running:

1. **Frontend**: Access the main URL assigned by Coolify
2. **Backend Health**: Access `/health` endpoint (e.g., `https://your-domain.com/health`)
3. **API Docs**: Access `/docs` for FastAPI Swagger UI

### 6. Initial Setup

1. Navigate to the **Folders** tab
2. Add your Google Drive folder ID
3. Go to **Ingestion** tab
4. Start your first ingestion job
5. Monitor progress in the **Jobs** tab

## Architecture Overview

The application consists of 5 services:

- **db**: PostgreSQL 16 with pgvector extension
- **redis**: Redis for Celery task queue
- **backend**: FastAPI application (Python 3.11)
- **celery_worker**: Async document processing worker
- **frontend**: React application with Nginx

## Health Checks

All services include health checks:

- **Backend**: `http://backend:8000/health`
- **Frontend**: `http://frontend:3000`
- **Database**: `pg_isready` check
- **Redis**: `redis-cli ping`
- **Celery**: `celery inspect ping`

## Monitoring

### Application Logs

Access logs in Coolify's log viewer for each service:

- Backend logs: API requests, errors
- Celery logs: Document processing progress
- Frontend logs: Nginx access logs

### Job Monitoring

Use the built-in dashboard:

1. **Overview Tab**: System statistics and health
2. **Jobs Tab**: Real-time job progress with auto-refresh
3. **Documents Tab**: Document library with status filters
4. **Statistics Tab**: Analytics and success rates

## Scaling

### Horizontal Scaling

Increase the number of Celery workers:

```env
CELERY_CONCURRENCY=8  # Default is 4
```

Or scale the entire celery_worker service in Coolify.

### Database Scaling

For production, consider:
- Using Google Cloud SQL (managed PostgreSQL)
- Enabling connection pooling
- Setting up read replicas

## Troubleshooting

### Common Issues

#### 1. Database Connection Errors

**Symptom**: Backend fails to start with connection errors

**Solution**:
- Verify `DB_*` environment variables are set
- Check database service is healthy
- Ensure PostgreSQL has pgvector extension installed

#### 2. Google Cloud Authentication Errors

**Symptom**: "Could not authenticate with Google Cloud"

**Solution**:
- Verify `GOOGLE_PROJECT_ID` is correct
- Check service account has required permissions:
  - Vertex AI User
  - Drive Reader
  - Secret Manager Secret Accessor (if using Secret Manager)
- Ensure credentials file is properly mounted

#### 3. Celery Workers Not Processing

**Symptom**: Jobs stuck in "running" status

**Solution**:
- Check Celery worker logs in Coolify
- Verify Redis connection is working
- Ensure Celery workers have access to database

#### 4. Frontend Can't Reach Backend

**Symptom**: API calls fail from frontend

**Solution**:
- Verify Nginx proxy configuration in `frontend/nginx.conf`
- Check backend service is accessible on port 8000
- Review Coolify's network configuration

### Debug Mode

To enable debug logging:

1. Add to backend environment:
   ```env
   LOG_LEVEL=DEBUG
   ```

2. Check logs in Coolify's log viewer

## Backup and Restore

### Database Backup

```bash
# Backup
docker exec drivevectorai_db pg_dump -U postgres drivevectorai > backup.sql

# Restore
docker exec -i drivevectorai_db psql -U postgres drivevectorai < backup.sql
```

### Export Documents

Use the Documents tab to export document metadata and embeddings.

## Security Considerations

1. **Secrets Management**: Use Coolify's secret management or Google Secret Manager
2. **Network Security**: Enable Coolify's built-in SSL/TLS
3. **Database Security**: Use strong passwords, restrict network access
4. **API Authentication**: Consider adding authentication layer for production
5. **Service Account Permissions**: Follow principle of least privilege

## Performance Tuning

### Backend

- Adjust `CELERY_CONCURRENCY` based on CPU cores
- Enable database connection pooling for high load
- Consider caching frequently accessed data

### Frontend

- Nginx already configured with gzip compression
- Static assets cached for 1 hour
- Consider CDN for static assets in production

### Database

- Monitor and optimize indexes
- Regular VACUUM operations
- Consider increasing PostgreSQL `shared_buffers` for large datasets

## Support

For issues or questions:

1. Check application logs in Coolify
2. Review [main README](README.md) for architecture details
3. Check [GitHub Issues](https://github.com/your-repo/issues)

## Next Steps

After successful deployment:

1. Set up regular database backups
2. Configure monitoring and alerting
3. Optimize Celery concurrency for your workload
4. Set up multiple Drive folders for different document sources
5. Explore the Chat feature with RAG for intelligent document Q&A
