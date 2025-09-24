#!/bin/bash
# Maintenance script for Hyperliquid Scraper
# Usage: ./maintenance.sh [backup|cleanup|update|status|restart]

set -e

PROJECT_NAME="hyperliquid-scraper"
BACKUP_DIR="backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

show_usage() {
    echo "Usage: ./maintenance.sh [command]"
    echo ""
    echo "Commands:"
    echo "  backup    - Create backup of logs and exports"
    echo "  cleanup   - Clean old logs and unused Docker resources"
    echo "  update    - Update containers to latest version"
    echo "  status    - Show detailed system status"
    echo "  restart   - Restart all services"
    echo "  logs      - Show recent logs"
    echo "  health    - Perform health check"
    echo ""
}

backup_data() {
    print_status "Creating backup..."

    mkdir -p $BACKUP_DIR

    # Create backup archive
    BACKUP_FILE="$BACKUP_DIR/hyperliquid_backup_$DATE.tar.gz"

    tar -czf $BACKUP_FILE \
        logs/ \
        exports/ \
        screenshots/ \
        .env \
        docker-compose.yml 2>/dev/null

    print_success "Backup created: $BACKUP_FILE"

    # Keep only last 5 backups
    ls -t $BACKUP_DIR/hyperliquid_backup_*.tar.gz | tail -n +6 | xargs -r rm
    print_status "Old backups cleaned (keeping last 5)"
}

cleanup_system() {
    print_status "Cleaning up system..."

    # Clean old logs (keep last 7 days)
    find logs/ -name "*.log*" -mtime +7 -delete 2>/dev/null || true
    print_status "Old logs cleaned"

    # Clean old exports (keep last 30 days)
    find exports/ -name "*" -mtime +30 -delete 2>/dev/null || true
    print_status "Old exports cleaned"

    # Clean old screenshots (keep last 3 days)
    find screenshots/ -name "*.png" -mtime +3 -delete 2>/dev/null || true
    print_status "Old screenshots cleaned"

    # Clean Docker resources
    docker system prune -f --volumes
    print_status "Docker resources cleaned"

    print_success "System cleanup completed"
}

update_containers() {
    print_status "Updating containers..."

    # Pull latest images
    docker-compose -p $PROJECT_NAME pull

    # Rebuild with latest code
    docker-compose -p $PROJECT_NAME build --no-cache

    # Restart services
    docker-compose -p $PROJECT_NAME down
    docker-compose -p $PROJECT_NAME up -d

    # Wait for health check
    sleep 30

    if check_health; then
        print_success "Update completed successfully"
    else
        print_warning "Update completed but health check failed"
    fi
}

show_status() {
    print_status "System Status Report"
    echo "===================="

    # Container status
    echo ""
    print_status "Container Status:"
    docker-compose -p $PROJECT_NAME ps

    # Health status
    echo ""
    print_status "Health Status:"
    if curl -sf http://localhost:8080/health >/dev/null 2>&1; then
        print_success "✅ Health endpoint accessible"
    else
        print_error "❌ Health endpoint not accessible"
    fi

    # Resource usage
    echo ""
    print_status "Resource Usage:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" 2>/dev/null | head -n 5

    # Disk usage
    echo ""
    print_status "Disk Usage:"
    df -h . | tail -n 1 | awk '{print "Available: " $4 " (" $5 " used)"}'

    # Recent activity
    echo ""
    print_status "Recent Activity (last 5 log entries):"
    docker-compose -p $PROJECT_NAME logs --tail=5 scraper | tail -n 5

    # Database status (if accessible)
    echo ""
    print_status "Database Status:"
    if docker-compose -p $PROJECT_NAME exec -T scraper python -c "from src.database.supabase_client import SupabaseClient; client = SupabaseClient(); print('✅ Database connected' if client.test_connection() else '❌ Database connection failed')" 2>/dev/null; then
        echo "Database connection verified"
    else
        print_warning "Could not verify database connection"
    fi
}

restart_services() {
    print_status "Restarting services..."

    docker-compose -p $PROJECT_NAME restart

    # Wait for services to be ready
    sleep 20

    if check_health; then
        print_success "Services restarted successfully"
    else
        print_warning "Services restarted but health check failed"
    fi
}

show_logs() {
    print_status "Recent logs (last 50 lines):"
    echo "================================"
    docker-compose -p $PROJECT_NAME logs --tail=50 scraper
}

check_health() {
    local max_attempts=10
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -sf http://localhost:8080/health >/dev/null 2>&1; then
            return 0
        fi
        sleep 5
        ((attempt++))
    done

    return 1
}

perform_health_check() {
    print_status "Performing comprehensive health check..."

    # Check container status
    if docker-compose -p $PROJECT_NAME ps | grep -q "Up"; then
        print_success "✅ Containers are running"
    else
        print_error "❌ Containers are not running"
        return 1
    fi

    # Check health endpoint
    if curl -sf http://localhost:8080/health >/dev/null 2>&1; then
        print_success "✅ Health endpoint responding"
    else
        print_error "❌ Health endpoint not responding"
    fi

    # Check database connection
    if docker-compose -p $PROJECT_NAME exec -T scraper python -c "from src.database.supabase_client import SupabaseClient; SupabaseClient().test_connection()" >/dev/null 2>&1; then
        print_success "✅ Database connection working"
    else
        print_error "❌ Database connection failed"
    fi

    # Check recent activity
    if docker-compose -p $PROJECT_NAME logs --tail=20 scraper | grep -q "Scraping job completed"; then
        print_success "✅ Recent scraping activity detected"
    else
        print_warning "⚠️  No recent scraping activity detected"
    fi

    # Check disk space
    DISK_USAGE=$(df . | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ $DISK_USAGE -lt 90 ]; then
        print_success "✅ Disk space OK ($DISK_USAGE% used)"
    else
        print_error "❌ Disk space critical ($DISK_USAGE% used)"
    fi

    print_status "Health check completed"
}

# Main script logic
case "$1" in
    backup)
        backup_data
        ;;
    cleanup)
        cleanup_system
        ;;
    update)
        update_containers
        ;;
    status)
        show_status
        ;;
    restart)
        restart_services
        ;;
    logs)
        show_logs
        ;;
    health)
        perform_health_check
        ;;
    *)
        show_usage
        exit 1
        ;;
esac