# DriveVectorAI

AI-powered document search and chat assistant that integrates Google Drive with vector embeddings and large language models.

## 🚀 Features

- **Google Drive Integration**: Scan and ingest documents from Google Drive folders
- **AI-Powered Search**: Semantic search using vector embeddings (Vertex AI)
- **Conversational AI**: Chat with your documents using RAG (Retrieval-Augmented Generation)
- **Multi-format Support**: PDF, DOCX, and TXT file processing
- **Modern Web UI**: React dashboard with Material-UI
- **Scalable Architecture**: Docker containerized with async processing via Celery

## 🏗️ Architecture

- **Backend**: FastAPI (Python) with PostgreSQL + pgvector
- **Frontend**: React + TypeScript with Material-UI
- **AI Services**: Google Vertex AI (Embeddings + LLMs)
- **Async Processing**: Celery + Redis
- **Containerization**: Docker Compose

## 📋 Prerequisites

- Docker and Docker Compose
- Google Cloud Project with billing enabled
- Service Account with required permissions
- PostgreSQL instance (Cloud SQL recommended)

## 🔧 Google Cloud Setup

### 1. Create Google Cloud Project
```bash
# Enable required APIs
gcloud services enable drive.googleapis.com
gcloud services enable aiplatform.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable sqladmin.googleapis.com
```

### 2. Create Service Account
```bash
# Create service account
gcloud iam service-accounts create drivevectorai-sa \
    --description="Service account for DriveVectorAI" \
    --display-name="DriveVectorAI Service Account"

# Grant necessary roles
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:drivevectorai-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/iam.serviceAccountTokenCreator"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:drivevectorai-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/drive.viewer"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:drivevectorai-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:drivevectorai-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:drivevectorai-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/cloudsql.client"

# Download service account key
gcloud iam service-accounts keys create credentials.json \
    --iam-account=drivevectorai-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

### 3. Create Cloud SQL PostgreSQL Instance
```bash
gcloud sql instances create drivevectorai-db \
    --database-version=POSTGRES_16 \
    --tier=db-f1-micro \
    --region=us-central1

# Create database and user
gcloud sql databases create drivevectorai --instance=drivevectorai-db
gcloud sql users create drivevectorai_user \
    --instance=drivevectorai-db \
    --password=YOUR_SECURE_PASSWORD
```

### 4. Enable pgvector Extension
```bash
# Connect to your Cloud SQL instance and run:
CREATE EXTENSION IF NOT EXISTS vector;
```

### 5. Store Database Credentials in Secret Manager
```bash
# Create secret for database credentials
echo -n '{
  "host": "YOUR_CLOUD_SQL_IP",
  "port": 5432,
  "dbname": "drivevectorai",
  "user": "drivevectorai_user",
  "password": "YOUR_DB_PASSWORD"
}' | gcloud secrets create db-credentials --data-file=-
```

## 🚀 Local Development Setup

### 1. Clone and Setup
```bash
git clone <your-repo-url>
cd DriveVectorAI

# Copy environment template
cp .env.example .env

# Edit .env with your values
nano .env
```

### 2. Start Services
```bash
# Build and start all services
docker-compose up --build -d

# View logs
docker-compose logs -f
```

### 3. Access Application
- **Frontend Dashboard**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 📁 Project Structure

```
DriveVectorAI/
├── backend/                 # FastAPI backend
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py         # FastAPI app entry point
│       ├── routers/        # API endpoints
│       │   ├── ingest.py   # Document ingestion
│       │   ├── search.py   # Vector search
│       │   ├── llm.py      # AI chat
│       │   └── settings.py # Settings management
│       └── services/       # Business logic
│           ├── drive_service.py     # Google Drive integration
│           ├── embedding_service.py # Vertex AI embeddings
│           └── vector_db_service.py # PostgreSQL + pgvector
├── frontend/                # React dashboard
│   ├── Dockerfile
│   ├── package.json
│   ├── nginx.conf
│   └── src/
│       ├── pages/          # React pages
│       │   ├── Dashboard.tsx
│       │   ├── SettingsPage.tsx
│       │   ├── IngestionPage.tsx
│       │   ├── SearchPage.tsx
│       │   └── ChatPage.tsx
│       └── services/
│           └── api.ts       # Axios configuration
├── db/                     # Database initialization
│   └── init.sql
├── docker-compose.yml      # Container orchestration
├── deploy.sh              # Deployment script
└── .env.example           # Environment template
```

## 🔄 Usage Workflow

### 1. Configure Settings
1. Open the dashboard at http://localhost:3000
2. Go to Settings tab
3. Enter your Google Cloud Project ID, Drive Folder ID, and other configurations
4. Save settings

### 2. Ingest Documents
1. Go to Ingestion tab
2. Click "Start Drive Scan & Ingest"
3. The system will:
   - Scan your specified Google Drive folder
   - Download supported files (PDF, DOCX, TXT)
   - Extract text content
   - Generate vector embeddings
   - Store everything in the vector database

### 3. Search Documents
1. Go to Search tab
2. Enter your search query
3. View results with similarity scores
4. Click links to view original files in Google Drive

### 4. Chat with AI
1. Go to Chat tab
2. Ask questions about your documents
3. Enable RAG for context-aware responses
4. Select different AI models

## 🔧 API Endpoints

### Ingestion
- `POST /ingest/start` - Start document ingestion from Drive folder

### Search
- `POST /search/` - Semantic search with vector similarity

### AI Chat
- `POST /llm/chat` - Conversational AI with optional RAG
- `GET /llm/models` - List available AI models

### Settings
- `POST /settings/` - Update application settings

### Health
- `GET /health` - Health check endpoint

## 🔒 Security Considerations

- Store service account keys securely (Secret Manager in production)
- Use environment variables for sensitive configuration
- Implement authentication for production deployment
- Regular security updates for all dependencies
- Network segmentation with Docker networks

## 📊 Monitoring & Troubleshooting

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f db
```

### Database Access
```bash
# Connect to PostgreSQL
docker-compose exec db psql -U drivevectorai_user -d drivevectorai

# Check documents table
SELECT COUNT(*) FROM documents;
```

### Common Issues
1. **Permission Denied**: Check service account roles and Drive folder sharing
2. **Database Connection Failed**: Verify Cloud SQL configuration and Secret Manager
3. **Embedding Generation Failed**: Check Vertex AI API enablement and quotas
4. **Build Failures**: Ensure all environment variables are set correctly

## 🚀 Production Deployment

### Automated Deployment
```bash
# Run deployment script on Ubuntu server
./deploy.sh
```

### Manual Deployment Steps
1. Provision Ubuntu server
2. Install Docker and Docker Compose
3. Clone repository
4. Configure environment variables
5. Run `docker-compose up -d --build`
6. Set up Nginx reverse proxy (optional)
7. Configure SSL with Certbot (optional)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review Docker logs for error details
3. Verify Google Cloud configuration
4. Open an issue on GitHub

---

**Happy Document AI! 🤖📄**
