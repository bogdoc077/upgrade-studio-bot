#!/bin/bash
# БЕЗПЕЧНИЙ скрипт розгортання з захистом від блокування SSH
# Використання: bash safe_deploy.sh

set -e

echo "=== БЕЗПЕЧНЕ РОЗГОРТАННЯ UPGRADE Studio Bot ==="
echo ""

# Кольори
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_step() {
    echo -e "${GREEN}[КРОК]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[УВАГА]${NC} $1"
}

print_error() {
    echo -e "${RED}[ПОМИЛКА]${NC} $1"
}

# Перевірка root
if [[ $EUID -ne 0 ]]; then
   print_error "Цей скрипт потрібно запускати від root"
   exit 1
fi

# ==========================================
# 1. ОНОВЛЕННЯ СИСТЕМИ
# ==========================================
print_step "1. Оновлення системи..."
apt update
apt upgrade -y

# ==========================================
# 2. ВСТАНОВЛЕННЯ БАЗОВИХ ПАКЕТІВ
# ==========================================
print_step "2. Встановлення базових пакетів..."
apt install -y \
    git \
    python3 \
    python3-pip \
    python3-venv \
    nginx \
    certbot \
    python3-certbot-nginx \
    curl \
    wget \
    htop \
    net-tools

# ==========================================
# 3. БЕЗПЕЧНЕ НАЛАШТУВАННЯ FIREWALL
# ==========================================
print_step "3. БЕЗПЕЧНЕ налаштування firewall..."
print_warning "Застосовуємо правила firewall з захистом від самоблокування..."

# КРИТИЧНО: Спочатку дозволяємо SSH!
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp

# Тільки тепер блокуємо інші порти
ufw default deny incoming
ufw default allow outgoing

# Активуємо firewall
ufw --force enable

# Перевіряємо що SSH дозволено
if ! ufw status | grep -q "22/tcp.*ALLOW"; then
    print_error "КРИТИЧНА ПОМИЛКА: SSH не дозволено в firewall!"
    print_warning "Вимикаю firewall для безпеки..."
    ufw disable
    exit 1
fi

print_warning "✓ Firewall налаштовано БЕЗ блокування SSH"

# ==========================================
# 4. ВСТАНОВЛЕННЯ NODE.JS
# ==========================================
print_step "4. Встановлення Node.js 20..."
# Перевіряємо чи вже встановлено
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt install -y nodejs
else
    print_warning "Node.js вже встановлено"
fi

node --version
npm --version

# ==========================================
# 5. КЛОНУВАННЯ РЕПОЗИТОРІЮ (якщо ще немає)
# ==========================================
print_step "5. Перевірка репозиторію..."
if [ ! -d "/opt/upgrade-studio-bot" ]; then
    print_step "Клонування репозиторію..."
    cd /opt
    git clone https://github.com/bogdoc077/upgrade-studio-bot.git
else
    print_warning "Репозиторій вже існує, оновлюю..."
    cd /opt/upgrade-studio-bot
    git fetch origin
    git reset --hard origin/main
fi

cd /opt/upgrade-studio-bot

# ==========================================
# 6. НАЛАШТУВАННЯ PYTHON VENV
# ==========================================
print_step "6. Налаштування Python environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# ==========================================
# 7. .ENV ФАЙЛ
# ==========================================
print_step "7. Перевірка .env файлу..."
if [ ! -f ".env" ]; then
    print_warning ".env файл не знайдено!"
    print_warning "Створіть його вручну або скопіюйте з .env.example"
    echo ""
    echo "Приклад створення:"
    echo "  nano /opt/upgrade-studio-bot/.env"
    echo ""
else
    print_warning "✓ .env файл існує"
fi

# ==========================================
# 8. ADMIN PANEL
# ==========================================
print_step "8. Збірка Admin Panel..."
cd admin-panel
if [ ! -d "node_modules" ]; then
    npm install
fi
npm run build
cd ..

# ==========================================
# 9. СТВОРЕННЯ ДИРЕКТОРІЙ
# ==========================================
print_step "9. Створення директорій..."
mkdir -p logs uploads/broadcasts
chmod 755 logs uploads
chmod 755 uploads/broadcasts

# ==========================================
# 10. SYSTEMD СЕРВІСИ
# ==========================================
print_step "10. Створення systemd сервісів..."

# API Service
cat > /etc/systemd/system/upgrade-api.service << 'EOF'
[Unit]
Description=UPGRADE Studio API Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/upgrade-studio-bot
ExecStart=/opt/upgrade-studio-bot/venv/bin/python start_api.py
Restart=always
RestartSec=10
Environment="PATH=/opt/upgrade-studio-bot/venv/bin"

[Install]
WantedBy=multi-user.target
EOF

# Webhook Service
cat > /etc/systemd/system/upgrade-webhook.service << 'EOF'
[Unit]
Description=UPGRADE Studio Webhook Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/upgrade-studio-bot
ExecStart=/opt/upgrade-studio-bot/venv/bin/python webhook_server.py
Restart=always
RestartSec=10
Environment="PATH=/opt/upgrade-studio-bot/venv/bin"

[Install]
WantedBy=multi-user.target
EOF

# Admin Panel Service
cat > /etc/systemd/system/upgrade-admin.service << 'EOF'
[Unit]
Description=UPGRADE Studio Admin Panel
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/upgrade-studio-bot/admin-panel
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=10
Environment="NODE_ENV=production"

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload

# ==========================================
# 11. NGINX КОНФІГУРАЦІЯ
# ==========================================
print_step "11. Налаштування Nginx..."

cat > /etc/nginx/sites-available/admin.upgrade21.com << 'EOF'
server {
    listen 80;
    server_name admin.upgrade21.com;
    
    client_max_body_size 10m;
    
    # API
    location /api/ {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Stripe Webhook
    location /webhook {
        proxy_pass http://localhost:8000/webhook;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 10m;
    }
    
    # Telegram Webhook  
    location /telegram-webhook {
        proxy_pass http://localhost:8000/telegram-webhook;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 10m;
    }
    
    # Admin Panel
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

ln -sf /etc/nginx/sites-available/admin.upgrade21.com /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

nginx -t && systemctl restart nginx

# ==========================================
# ЗАВЕРШЕННЯ
# ==========================================
echo ""
echo "=============================================="
echo -e "${GREEN}✅ Базове встановлення завершено!${NC}"
echo "=============================================="
echo ""
echo "НАСТУПНІ КРОКИ:"
echo ""
echo "1. Перевірте .env файл:"
echo "   nano /opt/upgrade-studio-bot/.env"
echo ""
echo "2. Отримайте SSL сертифікат:"
echo "   certbot --nginx -d admin.upgrade21.com --non-interactive --agree-tos --email admin@upgrade21.com --redirect"
echo ""
echo "3. Запустіть сервіси:"
echo "   systemctl enable upgrade-api upgrade-webhook upgrade-admin"
echo "   systemctl start upgrade-api upgrade-webhook upgrade-admin"
echo ""
echo "4. Перевірте статус:"
echo "   systemctl status upgrade-api upgrade-webhook upgrade-admin"
echo ""
echo "=============================================="
