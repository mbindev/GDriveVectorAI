# DriveVectorAI Changelog

## Version 2.0.0 - Complete System Overhaul

### Major Features Added

#### 1. Comprehensive Document Management System
- **Document Library**: Full CRUD operations for documents
  - View all documents with pagination
  - Filter by status (pending, processing, completed, failed)
  - Delete documents from the system
  - View processing logs for each document
  - Direct links to Google Drive
- **Document Status Tracking**: Real-time status updates for each document
- **Error Reporting**: Detailed error messages and logs for failed documents

#### 2. Job Monitoring & Progress Tracking
- **Job Dashboard**: Real-time monitoring of ingestion jobs
  - Live progress bars showing completion percentage
  - Auto-refresh for running jobs
  - Detailed job statistics (total, processed, failed files)
  - Duration tracking
- **Job History**: View all past jobs with status and results
- **Job Logs**: Comprehensive logging for each job with filterable log levels

#### 3. Multi-Folder Management
- **Folder Registry**: Manage multiple Google Drive folders
  - Add/edit/delete folder configurations
  - Store folder metadata (name, description, folder_id)
  - Track folder status (active/inactive)
- **Folder Selection**: Choose from registered folders during ingestion
- **Per-Folder Statistics**: Track documents by folder

#### 4. Statistics & Analytics Dashboard
- **System Overview**: Real-time statistics
  - Total documents, jobs, and folders
  - Success rates and completion percentages
  - Document status breakdown (completed, failed, pending, processing)
  - Job status breakdown
- **Storage Statistics**: Track total and average document sizes
- **Auto-Refresh**: Statistics update automatically every 30 seconds

#### 5. Enhanced Ingestion System
- **Improved UI**: User-friendly ingestion interface
  - Folder selection dropdown
  - Metadata input (name, description)
  - Real-time file listing
  - Direct navigation to job monitoring
- **Better Error Handling**: Clear error messages and validation
- **Job Tracking**: Every ingestion creates a tracked job

### Backend Improvements

#### Database Schema Enhancements
- **New Tables**:
  - `drive_folders`: Multi-folder management
  - `ingestion_jobs`: Job tracking and progress
  - `processing_logs`: Detailed processing logs with JSONB details
- **Enhanced Documents Table**:
  - Added status tracking (pending, processing, completed, failed)
  - Added error_message field
  - Added folder_id and job_id foreign keys
  - Added timestamps (created_at, updated_at, processed_at)
  - Added full_text_length tracking
- **Indexes**: Optimized indexes for better query performance

#### New API Endpoints
- **Documents API** (`/api/documents`):
  - `GET /` - List documents with pagination and filters
  - `GET /{id}` - Get document details
  - `DELETE /{id}` - Delete document
  - `GET /{id}/logs` - Get document processing logs

- **Jobs API** (`/api/jobs`):
  - `GET /` - List all jobs
  - `GET /{id}` - Get job status and progress
  - `GET /{id}/logs` - Get job logs

- **Folders API** (`/api/folders`):
  - `GET /` - List all folders
  - `POST /` - Create folder
  - `PUT /{id}` - Update folder
  - `DELETE /{id}` - Delete folder

- **Statistics API** (`/api/statistics`):
  - `GET /` - Get system statistics

#### Enhanced Celery Task System
- **Automatic Status Updates**: Tasks update document status in real-time
- **Progress Tracking**: Job progress updated after each document
- **Error Tracking**: Failed tasks log detailed error information
- **Retry Logic**: Automatic retries (up to 3 attempts) for failed tasks
- **Job Completion Detection**: Automatic job completion when all files processed
- **Celery Signals**: Monitoring hooks for task lifecycle events

#### Database Service Improvements
- 20+ new database functions for CRUD operations
- Support for job management, folder management, and logging
- Statistics aggregation functions
- Optimized queries with proper indexing

### Frontend Enhancements

#### New Pages
1. **StatisticsPage**: System overview with metrics and analytics
2. **DocumentsPage**: Document library with full management
3. **JobsPage**: Job monitoring with real-time updates
4. **FoldersPage**: Folder management interface
5. **Enhanced IngestionPage**: Better UX with folder selection

#### Improved Dashboard
- 8 tabs with icons: Overview, Folders, Ingestion, Jobs, Documents, Search, Chat, Settings
- Scrollable tab bar for better mobile experience
- Better visual hierarchy and organization

#### UI/UX Improvements
- Material-UI icons throughout
- Consistent color scheme for status indicators
- Progress bars for job monitoring
- Pagination for large data sets
- Real-time updates with auto-refresh
- Responsive design for all screen sizes
- Delete confirmations and error handling
- Loading states and skeleton screens

### Deployment & Infrastructure

#### Coolify-Ready Configuration
- **No .env File Required**: All configuration via environment variables
- **Environment Variable Fallbacks**: Sensible defaults for all settings
- **Flexible Database Configuration**:
  - Support for Google Secret Manager
  - Direct environment variable configuration
  - Automatic fallback between methods
- **Updated .env.example**: Comprehensive documentation with Coolify notes

#### Docker Compose Improvements
- **Health Checks**: All services now have proper health checks
  - Database: `pg_isready` check
  - Redis: `redis-cli ping`
  - Backend: HTTP health endpoint
  - Frontend: HTTP availability check
  - Celery: Worker ping check
- **Service Dependencies**: Proper dependency chains with health conditions
- **Port Configurability**: All ports configurable via environment variables
- **Security**: Non-root user in backend container
- **Volume Management**: Named volumes with explicit drivers

#### Enhanced Dockerfiles
- **Backend Dockerfile**:
  - Added curl for health checks
  - Non-root user (appuser)
  - Integrated health check
  - Smaller image size with cleanup
- **Better Layer Caching**: Optimized build steps

#### Production-Ready Features
- Configurable Celery concurrency
- Adjustable ports for all services
- Health check intervals and timeouts
- Restart policies (unless-stopped)
- Resource limits (can be added)

### Documentation

#### New Documentation Files
1. **COOLIFY_DEPLOYMENT.md**: Complete Coolify deployment guide
   - Step-by-step deployment instructions
   - Environment variable configuration
   - Google Cloud authentication setup
   - Troubleshooting guide
   - Security considerations
   - Performance tuning tips

2. **Enhanced .env.example**: Comprehensive configuration template
   - Organized by category
   - Coolify-specific notes
   - Required vs optional variables clearly marked

### Breaking Changes
- Database schema has changed significantly - migration required for existing deployments
- API endpoints have been reorganized (old endpoints still work)
- Environment variable naming standardized

### Migration Guide
For existing deployments:

1. **Backup Your Database**:
   ```bash
   docker exec drivevectorai_db pg_dump -U postgres drivevectorai > backup.sql
   ```

2. **Update Database Schema**:
   - Apply new schema from `db/init.sql` (creates new tables)
   - Existing documents table will be altered to add new columns

3. **Update Environment Variables**:
   - Add `DB_HOST`, `DB_PORT` variables
   - Optionally set `CELERY_CONCURRENCY`
   - Review `.env.example` for new variables

4. **Rebuild Containers**:
   ```bash
   docker-compose down
   docker-compose build
   docker-compose up -d
   ```

### Security Improvements
- Non-root container users
- Fallback authentication methods
- Improved error handling (no sensitive data in errors)
- Health check endpoints don't expose sensitive information

### Performance Improvements
- Database indexes for faster queries
- Connection health checks prevent stale connections
- Optimized React components (pagination, lazy loading)
- Auto-refresh intervals prevent excessive API calls

### Bug Fixes
- Fixed document status not updating during processing
- Fixed job completion detection
- Improved error handling in Celery tasks
- Better handling of missing environment variables

## Version 1.0.0 - Initial Release

### Features
- Basic document ingestion from Google Drive
- Vector similarity search with pgvector
- LLM chat with RAG support
- FastAPI backend with Vertex AI integration
- React frontend with Material-UI
- Docker Compose deployment

---

## Upgrade Instructions

To upgrade from v1.0.0 to v2.0.0:

1. Pull the latest code
2. Review COOLIFY_DEPLOYMENT.md for new environment variables
3. Backup your database
4. Run `docker-compose down`
5. Update your `.env` file with new variables
6. Run `docker-compose up -d --build`
7. Verify all services are healthy: `docker-compose ps`

The system will automatically create new tables and update existing schemas on startup.
