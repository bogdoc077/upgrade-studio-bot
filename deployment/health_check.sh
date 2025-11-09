#!/bin/bash

# Health Check Script for upgrade-studio-bot
# Monitors all services and sends alerts if something is wrong

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

DOMAIN="admin.upgrade21.com"
APP_DIR="/opt/upgrade-studio-bot"

echo "🏥 Health Check for upgrade-studio-bot"
echo "======================================"

# Check if running on server
if [ ! -d "$APP_DIR" ]; then
    log_error "Not running on production server ($APP_DIR not found)"
    exit 1
fi

ISSUES=0

# 1. Check systemd services
log_info "Checking systemd services..."
SERVICES=("upgrade-bot" "upgrade-api" "upgrade-admin" "nginx" "postgresql")

for service in "${SERVICES[@]}"; do
    if sudo systemctl is-active --quiet $service; then
        echo "  ✅ $service is running"
    else
        echo "  ❌ $service is NOT running"
        ((ISSUES++))
    fi
done

# 2. Check ports
log_info "Checking port availability..."
PORTS=("3000:Admin Panel" "8000:API Server" "80:HTTP" "443:HTTPS" "5432:PostgreSQL")

for port_info in "${PORTS[@]}"; do
    PORT=$(echo $port_info | cut -d':' -f1)
    NAME=$(echo $port_info | cut -d':' -f2)
    
    if sudo netstat -tlnp | grep ":$PORT " > /dev/null; then
        echo "  ✅ $NAME (port $PORT) is listening"
    else
        echo "  ❌ $NAME (port $PORT) is NOT listening"
        ((ISSUES++))
    fi
done

# 3. Check HTTP endpoints
log_info "Checking HTTP endpoints..."

# Local admin panel
if curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 http://localhost:3000 | grep -q "200\|301\|302"; then
    echo "  ✅ Admin panel (localhost:3000) is responding"
else
    echo "  ❌ Admin panel (localhost:3000) is NOT responding"
    ((ISSUES++))
fi

# Local API
if curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 http://localhost:8000/health | grep -q "200"; then
    echo "  ✅ API server (localhost:8000) is responding"
else
    echo "  ❌ API server (localhost:8000) is NOT responding"
    ((ISSUES++))
fi

# External HTTPS
if curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 https://$DOMAIN | grep -q "200\|301\|302"; then
    echo "  ✅ External HTTPS (https://$DOMAIN) is responding"
else
    echo "  ❌ External HTTPS (https://$DOMAIN) is NOT responding"
    ((ISSUES++))
fi

# 4. Check SSL certificate
log_info "Checking SSL certificate..."
SSL_EXPIRY=$(echo | openssl s_client -connect $DOMAIN:443 -servername $DOMAIN 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)

if [ -n "$SSL_EXPIRY" ]; then
    SSL_EXPIRY_EPOCH=$(date -d "$SSL_EXPIRY" +%s)
    CURRENT_EPOCH=$(date +%s)
    DAYS_LEFT=$(( (SSL_EXPIRY_EPOCH - CURRENT_EPOCH) / 86400 ))
    
    if [ $DAYS_LEFT -gt 30 ]; then
        echo "  ✅ SSL certificate expires in $DAYS_LEFT days"
    elif [ $DAYS_LEFT -gt 7 ]; then
        echo "  ⚠️  SSL certificate expires in $DAYS_LEFT days (renew soon)"
        ((ISSUES++))
    else
        echo "  ❌ SSL certificate expires in $DAYS_LEFT days (URGENT)"
        ((ISSUES++))
    fi
else
    echo "  ❌ Could not check SSL certificate"
    ((ISSUES++))
fi

# 5. Check database connection
log_info "Checking database connection..."
cd $APP_DIR
if source venv/bin/activate && python -c "
import os
import sys
sys.path.append('.')
from database.models import init_db
try:
    init_db()
    print('  ✅ Database connection successful')
except Exception as e:
    print(f'  ❌ Database connection failed: {e}')
    exit(1)
"; then
    echo "Database check passed"
else
    echo "  ❌ Database connection failed"
    ((ISSUES++))
fi

# 6. Check disk space
log_info "Checking disk space..."
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -lt 80 ]; then
    echo "  ✅ Disk usage: ${DISK_USAGE}%"
elif [ $DISK_USAGE -lt 90 ]; then
    echo "  ⚠️  Disk usage: ${DISK_USAGE}% (getting high)"
else
    echo "  ❌ Disk usage: ${DISK_USAGE}% (CRITICAL)"
    ((ISSUES++))
fi

# 7. Check memory usage
log_info "Checking memory usage..."
MEMORY_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/$2 }')
if [ $MEMORY_USAGE -lt 80 ]; then
    echo "  ✅ Memory usage: ${MEMORY_USAGE}%"
elif [ $MEMORY_USAGE -lt 90 ]; then
    echo "  ⚠️  Memory usage: ${MEMORY_USAGE}% (getting high)"
else
    echo "  ❌ Memory usage: ${MEMORY_USAGE}% (CRITICAL)"
    ((ISSUES++))
fi

# 8. Check log file sizes
log_info "Checking log file sizes..."
LOG_SIZE=$(sudo journalctl --disk-usage | grep -oE '[0-9]+\.[0-9]+[KMGT]' | head -1)
echo "  📄 Journal log size: $LOG_SIZE"

# Summary
echo
echo "======================================"
if [ $ISSUES -eq 0 ]; then
    log_info "🎉 All systems are healthy! ($ISSUES issues found)"
    exit 0
elif [ $ISSUES -le 2 ]; then
    log_warn "⚠️  Minor issues detected ($ISSUES issues found)"
    exit 1
else
    log_error "🚨 Critical issues detected ($ISSUES issues found)"
    exit 2
fi