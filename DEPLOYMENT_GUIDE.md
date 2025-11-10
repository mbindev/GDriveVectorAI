# 🚀 DriveVectorAI v3.0.0 - Production Deployment Guide

## 📋 Overview

This guide provides step-by-step instructions for deploying DriveVectorAI v3.0.0 to production using Docker Compose or Coolify.

---

## ✅ Prerequisites

### Required Services
- **Docker** (v20.10+)
- **Docker Compose** (v2.0+)
- **PostgreSQL** (v16+) - with pgvector extension
- **Redis** (v7+)
- **Domain name** (for production SSL)

### Required API Keys
- **Google Cloud Platform** - Project ID, Service Account, Secret Manager
- **Google Drive API** - Folder ID, OAuth credentials
- **OpenAI API** - For AI features
- **SSL Certificate** - For HTTPS (production)

---

## 🔧 Environment Configuration

### 1. Create Environment File
```bash
cp .env.production .env
```

### 2. Update Required Variables
Edit `.env` with your actual values:

```bash
# Database (Required)
DB_PASSWORD=your_secure_password_here

# JWT (Required - Change in Production!)
JWT_SECRET_KEY=your_very_secure_secret_key_32_chars_minimum

# Google Cloud (Required for Drive integration)
GOOGLE_PROJECT_ID=your-gcp-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
DRIVE_FOLDER_ID=your-google-drive-folder-id

# OpenAI (Required for AI features)
OPENAI_API_KEY=your-openai-api-key

# Service URLs (Update for your domain)
SERVICE_URL_FRONTEND=https://your-domain.com
SERVICE_FQDN_FRONTEND=your-domain.com
```

---

## 🐳 Docker Compose Deployment

### 1. Build and Start Services
```bash
# Build all services
docker-compose build --no-cache

# Start all services
docker-compose up -d

# Verify deployment
./verify-deployment.sh
```

### 2. Initialize Database
```bash
# Run database migrations
docker-compose exec backend alembic upgrade head

# Create admin user (optional)
docker-compose exec backend python -c "
from app.services.auth_service import create_user
create_user('admin', 'admin@example.com', 'admin_password', is_admin=True)
print('Admin user created')
"
```

### 3. Verify Services
```bash
# Check all containers
docker-compose ps

# Check service health
curl http://localhost:8000/health
curl http://localhost:3000

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

---

## ☁️ Coolify Deployment

### 1. Repository Setup
- Push code to GitHub repository
- Ensure all files are committed (including `.env.production` template)

### 2. Coolify Configuration
In Coolify dashboard:

#### Database Service
- **Type**: PostgreSQL
- **Version**: 16-alpine
- **Database**: drivevectorai
- **User**: postgres
- **Password**: Use environment variable

#### Redis Service
- **Type**: Redis
- **Version**: 7-alpine

#### Backend Service
- **Source**: GitHub repository
- **Build Context**: `./backend`
- **Port**: 8000
- **Health Check**: `/health`
- **Environment Variables**: All from `.env.production`

#### Frontend Service
- **Source**: GitHub repository
- **Build Context**: `./frontend`
- **Port**: 3000
- **Health Check**: `/`
- **Environment Variables**: `REACT_APP_API_URL=/api`

#### Celery Services
- **Worker**: Command `celery -A app.tasks worker --loglevel=info`
- **Beat**: Command `celery -A app.tasks beat --loglevel=info`

### 3. Environment Variables in Coolify
Add all variables from `.env.production` to your Coolify environment:

**Critical Variables:**
- `DB_PASSWORD` (required)
- `JWT_SECRET_KEY` (required, change in production)
- `GOOGLE_PROJECT_ID` (required for Drive integration)
- `OPENAI_API_KEY` (required for AI features)

**Optional Variables:**
- `GOOGLE_APPLICATION_CREDENTIALS` (if using Secret Manager)
- `DRIVE_FOLDER_ID` (specific folder to scan)
- `GCS_BUCKET_NAME` (if using GCS storage)

---

## 🔍 Verification Steps

### 1. Health Checks
```bash
# Backend health
curl https://your-domain.com/api/health

# Frontend accessible
curl https://your-domain.com

# API documentation
open https://your-domain.com/docs
```

### 2. Authentication Test
```bash
# Register new user
curl -X POST https://your-domain.com/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"testpass123","full_name":"Test User"}'

# Login
curl -X POST https://your-domain.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass123"}'
```

### 3. Feature Testing
- Access frontend at `https://your-domain.com`
- Login with created user
- Create brands and campaigns
- Test document tagging
- Verify scanner functionality

---

## 🛠️ Troubleshooting

### Common Issues

#### 1. Container Won't Start
```bash
# Check logs
docker-compose logs [service_name]

# Check container status
docker-compose ps

# Restart specific service
docker-compose restart [service_name]
```

#### 2. Database Connection Failed
```bash
# Verify database is healthy
docker-compose exec db pg_isready -U postgres

# Check database logs
docker-compose logs db

# Verify credentials in .env
grep DB_ .env
```

#### 3. Frontend Build Failed
```bash
# Check Node.js version in build logs
docker-compose logs frontend

# Verify package.json dependencies
cat frontend/package.json

# Rebuild frontend
docker-compose build --no-cache frontend
```

#### 4. Celery Workers Not Starting
```bash
# Check Redis connection
docker-compose exec redis redis-cli ping

# Check Celery logs
docker-compose logs celery_worker
docker-compose logs celery_beat

# Restart Celery services
docker-compose restart celery_worker celery_beat
```

#### 5. Google Drive API Issues
```bash
# Verify credentials
docker-compose exec backend python -c "
from google.oauth2 import service_account
import json
try:
    with open('/app/credentials.json') as f:
        json.load(f)
    print('Credentials file valid')
except Exception as e:
    print(f'Credentials error: {e}')
"

# Test Drive API access
docker-compose exec backend python -c "
from googleapiclient.discovery import build
try:
    service = build('drive', 'v3')
    print('Drive API accessible')
except Exception as e:
    print(f'Drive API error: {e}')
"
```

---

## 📊 Monitoring

### Health Endpoints
- **Backend**: `/health`
- **Frontend**: `/` (nginx health check)
- **Database**: PostgreSQL health check
- **Redis**: `redis-cli ping`

### Log Locations
- **Backend**: `/app/logs/`
- **Nginx**: `/var/log/nginx/`
- **PostgreSQL**: PostgreSQL logs
- **Celery**: Celery worker logs

### Monitoring Commands
```bash
# Real-time logs
docker-compose logs -f

# Resource usage
docker stats

# Container status
docker-compose ps
```

---

## 🔒 Security Considerations

### Production Security
1. **Change default passwords** in `.env`
2. **Use strong JWT secret key** (32+ characters)
3. **Enable HTTPS** with SSL certificates
4. **Restrict database access** to internal network
5. **Regularly update dependencies**
6. **Monitor access logs**

### Environment Security
- Never commit `.env` files to version control
- Use Secret Manager for sensitive data
- Rotate API keys regularly
- Use read-only service accounts where possible

---

## 📈 Performance Optimization

### Database Optimization
```sql
-- Check slow queries
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

-- Analyze table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Application Optimization
- Monitor Celery queue length
- Adjust worker concurrency based on load
- Enable Redis persistence for critical data
- Use CDN for static assets in production

---

## 🔄 Updates and Maintenance

### Updating Application
```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose build --no-cache
docker-compose up -d

# Run migrations
docker-compose exec backend alembic upgrade head
```

### Backup Strategy
```bash
# Database backup
docker-compose exec db pg_dump -U postgres drivevectorai > backup.sql

# Volume backup
docker run --rm -v drivevectorai_db_data:/data -v $(pwd):/backup alpine tar czf /backup/db_data.tar.gz -C /data .

# Restore backup
docker-compose exec -T db psql -U postgres drivevectorai < backup.sql
```

---

## 📞 Support

If you encounter issues during deployment:

1. Check the troubleshooting section above
2. Review container logs for error messages
3. Verify all environment variables are set correctly
4. Ensure all prerequisites are installed
5. Check network connectivity between services

**Deployment Status**: ✅ Ready for production

**Last Updated**: November 10, 2025  
**Version**: v3.0.0
