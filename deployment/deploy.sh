#!/bin/bash

# Quick Deployment Script
# Use this script to deploy updates to the production server

set -e

echo "🚀 Deploying upgrade-studio-bot updates..."

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

APP_DIR="/opt/upgrade-studio-bot"
BRANCH="${1:-main}"

# Check if we're in the right directory
if [ ! -d "$APP_DIR" ]; then
    log_error "Application directory $APP_DIR not found!"
    exit 1
fi

cd $APP_DIR

# Stop services
log_info "Stopping services..."
sudo systemctl stop upgrade-bot upgrade-api upgrade-admin

# Backup current version
log_info "Creating backup..."
BACKUP_DIR="/opt/backups/upgrade-studio-bot-$(date +%Y%m%d-%H%M%S)"
sudo mkdir -p /opt/backups
sudo cp -r $APP_DIR $BACKUP_DIR
log_info "Backup created at: $BACKUP_DIR"

# Pull latest changes
log_info "Pulling latest changes from branch: $BRANCH"
git fetch origin
git checkout $BRANCH
git pull origin $BRANCH

# Update Python dependencies
log_info "Updating Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Update Node.js dependencies and rebuild admin panel
log_info "Updating admin panel..."
cd admin-panel
npm install
npm run build
cd ..

# Run database migrations
log_info "Running database migrations..."
source venv/bin/activate
python migrate_database.py || log_warn "Migration failed or no new migrations"

# Restart services
log_info "Starting services..."
sudo systemctl start upgrade-api
sleep 5  # Wait for API to start

sudo systemctl start upgrade-admin
sleep 5  # Wait for admin panel to start

sudo systemctl start upgrade-bot

# Check service status
log_info "Checking service status..."
sleep 10

for service in upgrade-bot upgrade-api upgrade-admin; do
    if sudo systemctl is-active --quiet $service; then
        log_info "✅ $service is running"
    else
        log_error "❌ $service failed to start"
        sudo journalctl -u $service --no-pager -n 20
    fi
done

# Test endpoints
log_info "Testing endpoints..."

# Test admin panel
if curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 | grep -q "200\|301\|302"; then
    log_info "✅ Admin panel is responding"
else
    log_warn "⚠️  Admin panel might not be responding correctly"
fi

# Test API
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health | grep -q "200"; then
    log_info "✅ API is responding"
else
    log_warn "⚠️  API might not be responding correctly"
fi

log_info "🎉 Deployment completed!"
log_info "Visit your admin panel at: https://admin.upgrade21.com"

# Show recent logs
log_info "Recent logs (last 20 lines):"
echo "--- Bot Logs ---"
sudo journalctl -u upgrade-bot --no-pager -n 10
echo "--- API Logs ---"
sudo journalctl -u upgrade-api --no-pager -n 10