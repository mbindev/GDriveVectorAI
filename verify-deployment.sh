#!/bin/bash

# ===============================================================
# DriveVectorAI Deployment Verification Script
# ===============================================================
# This script verifies that all services are running correctly
# ===============================================================

set -e

echo "🔍 DriveVectorAI Deployment Verification"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check service health
check_service() {
    local service_name=$1
    local url=$2
    local max_attempts=30
    local attempt=1
    
    echo -n "🔍 Checking $service_name... "
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Healthy${NC}"
            return 0
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            echo -e "${RED}❌ Failed after $max_attempts attempts${NC}"
            return 1
        fi
        
        echo -n "."
        sleep 2
        ((attempt++))
    done
}

# Function to check Docker container
check_container() {
    local container_name=$1
    echo -n "🔍 Checking container $container_name... "
    
    if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "$container_name.*Up"; then
        echo -e "${GREEN}✅ Running${NC}"
        return 0
    else
        echo -e "${RED}❌ Not running${NC}"
        return 1
    fi
}

echo ""
echo "📦 Checking Docker Containers..."
echo "==============================="

containers=(
    "drivevectorai_db"
    "drivevectorai_redis"
    "drivevectorai_backend"
    "drivevectorai_celery_worker"
    "drivevectorai_celery_beat"
    "drivevectorai_frontend"
)

all_containers_healthy=true

for container in "${containers[@]}"; do
    if ! check_container "$container"; then
        all_containers_healthy=false
    fi
done

echo ""
echo "🌐 Checking Service Health..."
echo "============================="

services=(
    "Database:postgresql://localhost:5432"
    "Backend:http://localhost:8000/health"
    "Frontend:http://localhost:3000"
)

all_services_healthy=true

for service in "${services[@]}"; do
    IFS=':' read -r name url <<< "$service"
    if ! check_service "$name" "$url"; then
        all_services_healthy=false
    fi
done

echo ""
echo "🔧 Checking API Endpoints..."
echo "==========================="

# Check backend API endpoints
endpoints=(
    "Health:http://localhost:8000/health"
    "Auth:http://localhost:8000/api/auth/me"
    "Brands:http://localhost:8000/api/brands/"
    "Campaigns:http://localhost:8000/api/campaigns/"
    "Tags:http://localhost:8000/api/tags/statistics"
)

all_endpoints_healthy=true

for endpoint in "${endpoints[@]}"; do
    IFS=':' read -r name url <<< "$endpoint"
    echo -n "🔍 Checking $name endpoint... "
    
    if curl -f -s "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Accessible${NC}"
    else
        echo -e "${YELLOW}⚠️  Not accessible (may require auth)${NC}"
    fi
done

echo ""
echo "📊 Final Status"
echo "================"

if [ "$all_containers_healthy" = true ] && [ "$all_services_healthy" = true ]; then
    echo -e "${GREEN}🎉 DEPLOYMENT SUCCESSFUL!${NC}"
    echo ""
    echo "🌐 Access your application:"
    echo "   Frontend: http://localhost:3000"
    echo "   Backend API: http://localhost:8000"
    echo "   API Docs: http://localhost:8000/docs"
    echo ""
    echo "🔍 To check logs:"
    echo "   docker logs drivevectorai_backend"
    echo "   docker logs drivevectorai_frontend"
    echo "   docker logs drivevectorai_celery_worker"
    echo ""
    exit 0
else
    echo -e "${RED}❌ DEPLOYMENT FAILED!${NC}"
    echo ""
    echo "🔍 Troubleshooting:"
    echo "   Check container logs: docker logs [container_name]"
    echo "   Check container status: docker ps -a"
    echo "   Restart services: docker-compose restart"
    echo ""
    exit 1
fi
