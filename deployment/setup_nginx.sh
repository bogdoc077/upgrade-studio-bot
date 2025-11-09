#!/bin/bash

# Nginx and SSL Setup Script
# Domain: admin.upgrade21.com

set -e

echo "🌐 Setting up Nginx and SSL for admin.upgrade21.com..."

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
NGINX_CONFIG="/etc/nginx/sites-available/$DOMAIN"

# Check if domain resolves to this server
log_info "Checking domain resolution..."
DOMAIN_IP=$(dig +short $DOMAIN)
SERVER_IP=$(curl -s ipinfo.io/ip)

if [ "$DOMAIN_IP" != "$SERVER_IP" ]; then
    log_warn "Domain $DOMAIN resolves to $DOMAIN_IP, but server IP is $SERVER_IP"
    log_warn "Make sure DNS is properly configured before continuing"
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Remove default nginx config
sudo rm -f /etc/nginx/sites-enabled/default

# Create nginx configuration
log_info "Creating nginx configuration..."
sudo tee $NGINX_CONFIG > /dev/null << EOF
# Upgrade Studio Bot - Admin Panel Configuration
server {
    listen 80;
    server_name $DOMAIN;

    # Redirect HTTP to HTTPS
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN;

    # SSL Configuration (will be updated by certbot)
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Main admin panel (Next.js)
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        proxy_read_timeout 86400;
    }

    # API endpoints
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        
        # CORS headers for API
        add_header Access-Control-Allow-Origin "https://$DOMAIN" always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Authorization, Content-Type" always;
        
        # Handle preflight requests
        if (\$request_method = 'OPTIONS') {
            add_header Access-Control-Allow-Origin "https://$DOMAIN";
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS";
            add_header Access-Control-Allow-Headers "Authorization, Content-Type";
            add_header Access-Control-Max-Age 1728000;
            add_header Content-Type "text/plain charset=UTF-8";
            add_header Content-Length 0;
            return 204;
        }
    }

    # Telegram webhook endpoint
    location /webhook {
        proxy_pass http://localhost:8000/webhook;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Only allow Telegram IPs (optional security measure)
        # allow 149.154.160.0/20;
        # allow 91.108.4.0/22;
        # deny all;
    }

    # Static files for admin panel
    location /_next/static/ {
        proxy_pass http://localhost:3000;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/json application/xml+rss application/atom+xml image/svg+xml;

    # Client max body size for file uploads
    client_max_body_size 50M;
}
EOF

# Enable the site
sudo ln -sf $NGINX_CONFIG /etc/nginx/sites-enabled/

# Test nginx configuration
log_info "Testing nginx configuration..."
sudo nginx -t

# Obtain SSL certificate
log_info "Obtaining SSL certificate from Let's Encrypt..."
sudo certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email admin@upgrade21.com --redirect

# Start and enable nginx
log_info "Starting nginx..."
sudo systemctl restart nginx
sudo systemctl enable nginx

# Setup auto-renewal for SSL
log_info "Setting up SSL certificate auto-renewal..."
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer

# Create a renewal hook to reload nginx
sudo tee /etc/letsencrypt/renewal-hooks/deploy/nginx-reload.sh > /dev/null << 'EOF'
#!/bin/bash
systemctl reload nginx
EOF

sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/nginx-reload.sh

log_info "✅ Nginx and SSL setup completed!"
log_info "Your admin panel will be available at: https://$DOMAIN"
log_info "API endpoints will be available at: https://$DOMAIN/api/"
log_info "Webhook URL for Telegram: https://$DOMAIN/webhook"

# Test SSL certificate
log_info "Testing SSL certificate..."
curl -I https://$DOMAIN || log_warn "SSL test failed - check domain resolution and certificate"

echo
log_warn "Remember to:"
echo "1. Update your Telegram bot webhook URL to: https://$DOMAIN/webhook"
echo "2. Update Stripe webhook URL if needed"
echo "3. Start your services: sudo systemctl start upgrade-bot upgrade-api upgrade-admin"