#!/bin/bash

# DriveVectorAI Deployment Script

set -e

echo "🚀 Starting DriveVectorAI deployment..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "🐳 Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo "Please log out and back in, then re-run this script."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "📦 Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.18.1/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# Clone or update repository (replace with your actual repo URL)
REPO_URL="https://github.com/yourusername/DriveVectorAI.git"
if [ ! -d "DriveVectorAI" ]; then
    echo "📥 Cloning repository..."
    git clone $REPO_URL
    cd DriveVectorAI
else
    cd DriveVectorAI
    echo "🔄 Pulling latest changes..."
    git pull origin main
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit the .env file with your actual configuration values."
    echo "   Required: DB_PASSWORD, GOOGLE_PROJECT_ID, SECRET_MANAGER_DB_SECRET_ID, DRIVE_FOLDER_ID"
    read -p "Press enter when you've updated the .env file..."
fi

# Build and start services
echo "🏗️  Building Docker images..."
docker-compose build

echo "🚀 Starting services..."
docker-compose up -d

echo "⏳ Waiting for services to be ready..."
sleep 30

# Health check
echo "🔍 Checking service health..."
if curl -f http://localhost:8000/health &> /dev/null; then
    echo "✅ Backend is healthy!"
else
    echo "❌ Backend health check failed. Check logs with: docker-compose logs backend"
fi

if curl -f http://localhost:3000 &> /dev/null; then
    echo "✅ Frontend is accessible!"
else
    echo "❌ Frontend health check failed. Check logs with: docker-compose logs frontend"
fi

echo ""
echo "🎉 Deployment completed!"
echo "🌐 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8000"
echo "📊 API Docs: http://localhost:8000/docs"
echo ""
echo "📋 Next steps:"
echo "1. Configure your Google Cloud Project and enable required APIs"
echo "2. Set up Secret Manager with database credentials"
echo "3. Update DRIVE_FOLDER_ID in .env with your Google Drive folder ID"
echo "4. Access the frontend to start configuring and ingesting documents"
echo ""
echo "📖 For production deployment:"
echo "   - Configure Nginx reverse proxy for domain access"
echo "   - Set up SSL certificates with Certbot"
echo "   - Configure firewall rules"
echo "   - Set up monitoring and logging"
