#!/bin/bash

# VPS Server Setup Script for upgrade-studio-bot
# Domain: admin.upgrade21.com

set -e  # Exit on any error

echo "🚀 Starting VPS setup for upgrade-studio-bot..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DOMAIN="admin.upgrade21.com"
APP_DIR="/opt/upgrade-studio-bot"
USER="ubuntu"  # Change if needed
NODE_VERSION="18"

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   log_error "This script should not be run as root. Run as regular user with sudo access."
   exit 1
fi

# Update system packages
log_info "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install essential packages
log_info "Installing essential packages..."
sudo apt install -y curl wget git build-essential software-properties-common \
    nginx postgresql postgresql-contrib redis-server certbot python3-certbot-nginx \
    python3-pip python3-venv python3-dev libpq-dev supervisor ufw fail2ban

# Configure firewall
log_info "Configuring firewall..."
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw --force enable

# Install Node.js
log_info "Installing Node.js ${NODE_VERSION}..."
curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | sudo -E bash -
sudo apt-get install -y nodejs

# Create application directory
log_info "Creating application directory..."
sudo mkdir -p $APP_DIR
sudo chown $USER:$USER $APP_DIR

# Clone repository
log_info "Cloning repository..."
if [ -d "$APP_DIR/.git" ]; then
    log_info "Repository already exists, pulling latest changes..."
    cd $APP_DIR
    git pull origin main
else
    git clone https://github.com/bogdoc077/upgrade-studio-bot.git $APP_DIR
    cd $APP_DIR
fi

# Setup Python virtual environment
log_info "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Install Node.js dependencies for admin panel
log_info "Installing Node.js dependencies..."
cd admin-panel
npm install
npm run build
cd ..

# Setup PostgreSQL database
log_info "Setting up PostgreSQL database..."
sudo -u postgres psql -c "CREATE DATABASE upgrade_studio_bot;" || log_warn "Database might already exist"
sudo -u postgres psql -c "CREATE USER bot_user WITH PASSWORD 'secure_password_123';" || log_warn "User might already exist"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE upgrade_studio_bot TO bot_user;"

# Create environment file
log_info "Creating environment configuration..."
cat > .env << EOF
# Database Configuration
DATABASE_URL=postgresql://bot_user:secure_password_123@localhost/upgrade_studio_bot

# Bot Configuration (will be managed via admin panel)
BOT_TOKEN=your_bot_token_here
WEBHOOK_URL=https://${DOMAIN}/webhook

# Stripe Configuration (will be managed via admin panel)
STRIPE_PUBLISHABLE_KEY=your_stripe_pk_here
STRIPE_SECRET_KEY=your_stripe_sk_here
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret_here

# Admin Panel Configuration
JWT_SECRET=your_jwt_secret_here_$(openssl rand -base64 32)
ADMIN_DEFAULT_PASSWORD=admin123

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
ADMIN_PANEL_PORT=3000

# Redis Configuration
REDIS_URL=redis://localhost:6379

# Environment
ENVIRONMENT=production
EOF

log_info "Environment file created. Please update with your actual values."

# Run database migrations
log_info "Running database migrations..."
source venv/bin/activate
python migrate_database.py

# Create systemd services
log_info "Creating systemd services..."

# Bot service
sudo tee /etc/systemd/system/upgrade-bot.service > /dev/null << EOF
[Unit]
Description=Upgrade Studio Bot
After=network.target postgresql.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
ExecStart=$APP_DIR/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# API service
sudo tee /etc/systemd/system/upgrade-api.service > /dev/null << EOF
[Unit]
Description=Upgrade Studio API
After=network.target postgresql.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
ExecStart=$APP_DIR/venv/bin/python start_api.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Admin panel service
sudo tee /etc/systemd/system/upgrade-admin.service > /dev/null << EOF
[Unit]
Description=Upgrade Studio Admin Panel
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR/admin-panel
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=10
Environment=NODE_ENV=production
Environment=PORT=3000

[Install]
WantedBy=multi-user.target
EOF

# Enable services
sudo systemctl daemon-reload
sudo systemctl enable upgrade-bot upgrade-api upgrade-admin

log_info "✅ Server setup completed!"
log_warn "Next steps:"
echo "1. Update .env file with your actual credentials"
echo "2. Run: sudo ./setup_nginx.sh to configure nginx and SSL"
echo "3. Start services: sudo systemctl start upgrade-bot upgrade-api upgrade-admin"
echo "4. Check logs: sudo journalctl -u upgrade-bot -f"