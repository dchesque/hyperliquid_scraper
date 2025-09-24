#!/bin/bash
# Deployment script for VPS/EasyPanel
# Usage: ./deploy.sh [production|staging]

set -e

ENVIRONMENT=${1:-production}
PROJECT_NAME="hyperliquid-scraper"
COMPOSE_FILE="docker-compose.yml"

echo "=========================================="
echo "🚀 Hyperliquid Scraper Deployment"
echo "=========================================="
echo "Environment: $ENVIRONMENT"
echo "Project: $PROJECT_NAME"
echo "=========================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
print_status "Creating directories..."
mkdir -p logs exports screenshots monitoring

# Check if .env file exists
if [ ! -f ".env" ]; then
    if [ -f ".env.production" ]; then
        print_warning ".env not found. Copying from .env.production"
        cp .env.production .env
    else
        print_error ".env file not found. Please create one based on .env.example"
        exit 1
    fi
fi

# Validate required environment variables
print_status "Validating environment configuration..."
if ! grep -q "SUPABASE_URL=" .env || grep -q "your_supabase_url_here" .env; then
    print_error "SUPABASE_URL not configured in .env file"
    exit 1
fi

if ! grep -q "SUPABASE_KEY=" .env || grep -q "your_supabase_anon_key_here" .env; then
    print_error "SUPABASE_KEY not configured in .env file"
    exit 1
fi

print_success "Environment configuration validated"

# Stop existing containers
print_status "Stopping existing containers..."
docker-compose -p $PROJECT_NAME down 2>/dev/null || true

# Remove old images (optional, for clean deployment)
if [ "$ENVIRONMENT" = "production" ]; then
    print_status "Cleaning old images..."
    docker image prune -f --filter "label=project=$PROJECT_NAME" 2>/dev/null || true
fi

# Build new image
print_status "Building Docker image..."
docker-compose -p $PROJECT_NAME build --no-cache

# Start services
print_status "Starting services..."
if [ "$ENVIRONMENT" = "production" ]; then
    docker-compose -p $PROJECT_NAME up -d
else
    # For staging, include monitoring services
    docker-compose -p $PROJECT_NAME --profile monitoring up -d
fi

# Wait for services to be healthy
print_status "Waiting for services to be healthy..."
sleep 30

# Check health
check_health() {
    local container_name=$1
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if docker inspect $container_name --format='{{.State.Health.Status}}' 2>/dev/null | grep -q "healthy"; then
            return 0
        fi

        if [ $attempt -eq 1 ]; then
            print_status "Waiting for $container_name to become healthy..."
        fi

        sleep 10
        ((attempt++))
    done

    return 1
}

# Check main scraper health
if check_health "${PROJECT_NAME}-scraper-1" || check_health "hyperliquid-scraper"; then
    print_success "Scraper service is healthy!"
else
    print_warning "Scraper service health check timed out. Checking logs..."
    docker-compose -p $PROJECT_NAME logs --tail=20 scraper
fi

# Show running containers
print_status "Running containers:"
docker-compose -p $PROJECT_NAME ps

# Show useful information
echo ""
echo "=========================================="
print_success "Deployment completed!"
echo "=========================================="

print_status "Service URLs:"
echo "  📊 Health Dashboard: http://localhost:8080"
echo "  🔍 Health Check: http://localhost:8080/health"
echo "  📈 API Status: http://localhost:8080/api/status"
echo "  📋 Logs: http://localhost:8080/logs/"
echo "  💾 Exports: http://localhost:8080/exports/"

print_status "Useful commands:"
echo "  View logs: docker-compose -p $PROJECT_NAME logs -f scraper"
echo "  Stop services: docker-compose -p $PROJECT_NAME down"
echo "  Restart: docker-compose -p $PROJECT_NAME restart scraper"
echo "  Shell access: docker-compose -p $PROJECT_NAME exec scraper /bin/bash"

print_status "Monitoring:"
echo "  Container health: docker inspect hyperliquid-scraper --format='{{.State.Health.Status}}'"
echo "  Resource usage: docker stats hyperliquid-scraper"

# Final health check
echo ""
print_status "Performing final health check..."
if curl -f http://localhost:8080/health >/dev/null 2>&1; then
    print_success "✅ All systems operational!"

    # Get current status from logs
    if docker-compose -p $PROJECT_NAME logs scraper --tail=5 | grep -q "Scraping job completed"; then
        print_success "✅ Scraper is actively collecting data"
    fi
else
    print_warning "⚠️  Health check endpoint not accessible"
    print_status "This might be normal if monitoring service is not enabled"
fi

echo ""
echo "🎉 Deployment successful! Your Hyperliquid scraper is now running."
echo "📱 Monitor your deployment and check logs for any issues."