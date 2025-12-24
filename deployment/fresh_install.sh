#!/bin/bash
# Скрипт повного розгортання UPGRADE Studio Bot на чистій ОС
# Використання: bash fresh_install.sh

set -e  # Зупинка при помилках

echo "=== UPGRADE Studio Bot - Розгортання на чистій ОС ==="
echo ""

# Кольори для виводу
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Функція для виводу кроків
print_step() {
    echo -e "${GREEN}[КРОК]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[УВАГА]${NC} $1"
}

print_error() {
    echo -e "${RED}[ПОМИЛКА]${NC} $1"
}

# Перевірка що запущено від root
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
apt install -y software-properties-common

# ==========================================
# 2. ВСТАНОВЛЕННЯ НЕОБХІДНИХ ПАКЕТІВ
# ==========================================
print_step "2. Встановлення необхідних пакетів..."
apt install -y \
    git \
    python3 \
    python3-pip \
    python3-venv \
    nginx \
    certbot \
    python3-certbot-nginx \
    redis-server \
    curl \
    wget \
    ufw \
    fail2ban \
    htop \
    net-tools

# ==========================================
# 3. ВСТАНОВЛЕННЯ NODE.JS
# ==========================================
print_step "3. Встановлення Node.js 18.x..."
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt install -y nodejs

# Перевірка версій
node --version
npm --version

# ==========================================
# 4. НАЛАШТУВАННЯ FIREWALL
# ==========================================
print_step "4. Налаштування firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw --force enable

# ==========================================
# 5. НАЛАШТУВАННЯ FAIL2BAN
# ==========================================
print_step "5. Налаштування fail2ban..."
systemctl enable fail2ban
systemctl start fail2ban

# ==========================================
# 6. КЛОНУВАННЯ РЕПОЗИТОРІЮ
# ==========================================
print_step "6. Клонування репозиторію..."
cd /opt
if [ -d "upgrade-studio-bot" ]; then
    print_warning "Директорія /opt/upgrade-studio-bot вже існує. Видаляю..."
    rm -rf upgrade-studio-bot
fi

git clone https://github.com/bogdoc077/upgrade-studio-bot.git
cd upgrade-studio-bot

# ==========================================
# 7. НАЛАШТУВАННЯ PYTHON VENV
# ==========================================
print_step "7. Налаштування Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Оновлення pip
pip install --upgrade pip

# Встановлення залежностей
pip install -r requirements.txt

# ==========================================
# 8. MYSQL (використовується зовнішня база)
# ==========================================
print_step "8. MySQL - використовується зовнішня база даних..."
print_warning "Локальна MySQL НЕ встановлюється - використовується upgrade.mysql.network"
echo ""

# ==========================================
# 9. СТВОРЕННЯ .env ФАЙЛУ
# ==========================================
print_step "9. Створення .env файлу..."

if [ -f ".env" ]; then
    print_warning ".env вже існує. Створюю резервну копію..."
    cp .env .env.backup
fi

cat > .env << 'ENVEOF'
# ID каналів та чатів (отримати через @userinfobot)
PRIVATE_CHANNEL_ID=-1002747224769
PRIVATE_CHAT_ID=-5046931710
ADMIN_CHAT_ID=578080052

# База даних (зовнішня)
DATABASE_URL=mysql+pymysql://upgrade_studio:92vZE43Zdv@upgrade.mysql.network:10868/upgrade_studio

# Налаштування веб-сервера для вебхуків
WEBHOOK_HOST=0.0.0.0
WEBHOOK_PORT=8000
WEBHOOK_PATH=/webhook
WEBHOOK_URL=https://admin.upgrade21.com/webhook
ENVIRONMENT=production

# Налаштування нагадувань (дні)
REMINDER_INTERVALS=[1,2]
SUBSCRIPTION_REMINDER_DAYS=7
PAYMENT_RETRY_HOURS=24

# Налаштування адмін-панелі
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change_this_password
ADMIN_HOST=0.0.0.0
ADMIN_PORT=8001

# Рівень логування
LOG_LEVEL=INFO

# Додаткові налаштування (якщо потрібні)
API_HOST=0.0.0.0
API_PORT=8001
ADMIN_PANEL_PORT=3000
REDIS_URL=redis://localhost:6379
DB_ENCRYPTION_KEY=$(openssl rand -hex 32)
JWT_SECRET=$(openssl rand -hex 32)
ENVEOF

print_warning "Файл .env створено! Потрібно додати:"
echo "  - TELEGRAM_BOT_TOKEN (від @BotFather)"
echo "  - STRIPE_SECRET_KEY"
echo "  - STRIPE_PUBLISHABLE_KEY"
echo "  - STRIPE_WEBHOOK_SECRET"
echo "  - Змінити ADMIN_PASSWORD"
echo ""
echo "Команда для редагування: nano /opt/upgrade-studio-bot/.env"
echo ""

# ==========================================
# 10. ІНІЦІАЛІЗАЦІЯ БАЗИ ДАНИХ
# ==========================================
print_step "10. Ініціалізація бази даних..."
python3 -c "from database import create_tables; create_tables()"

# Міграція telegram_id до BIGINT
if [ -f "migrate_telegram_id_to_bigint.py" ]; then
    print_step "Виконання міграції telegram_id..."
    python3 migrate_telegram_id_to_bigint.py
fi

# ==========================================
# 11. ВСТАНОВЛЕННЯ ADMIN PANEL
# ==========================================
print_step "11. Встановлення Admin Panel (Next.js)..."
cd admin-panel
npm install
npm run build
cd ..

# ==========================================
# 12. НАЛАШТУВАННЯ NGINX
# ==========================================
print_step "12. Налаштування Nginx..."

cat > /etc/nginx/sites-available/admin.upgrade21.com << 'NGINXEOF'
server {
    listen 80;
    server_name admin.upgrade21.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name admin.upgrade21.com;

    # SSL certificates (will be configured by certbot)
    ssl_certificate /etc/letsencrypt/live/admin.upgrade21.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/admin.upgrade21.com/privkey.pem;

    # SSL optimization
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Compression для зменшення трафіку
    gzip on;
    gzip_vary on;
    gzip_min_length 1000;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript 
               application/json application/javascript application/xml+rss 
               application/x-javascript image/svg+xml;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=api:10m rate=5r/s;
    limit_req zone=general burst=20 nodelay;

    # Кешування статичних файлів
    location ~* \.(jpg|jpeg|png|gif|ico|css|js|svg|woff|woff2|ttf|eot)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # API
    location /api/ {
        limit_req zone=api burst=10 nodelay;
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Webhook
    location /webhook {
        limit_req zone=api burst=50 nodelay;
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        client_max_body_size 10m;
    }

    # Admin Panel (Next.js)
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Логування з буферизацією
    access_log /var/log/nginx/admin.upgrade21.com.access.log combined buffer=32k flush=5m;
    error_log /var/log/nginx/admin.upgrade21.com.error.log warn;
}
NGINXEOF

# Активація конфігурації
ln -sf /etc/nginx/sites-available/admin.upgrade21.com /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Перевірка конфігурації
nginx -t

# ==========================================
# 13. НАЛАШТУВАННЯ LOGROTATE
# ==========================================
print_step "13. Налаштування ротації логів..."
cat > /etc/logrotate.d/upgrade-studio-bot << 'LOGEOF'
/opt/upgrade-studio-bot/logs/*.log {
    daily
    rotate 3
    compress
    delaycompress
    missingok
    notifempty
    create 0644 root root
    maxsize 50M
}
LOGEOF

# ==========================================
# 14. НАЛАШТУВАННЯ CRON JOBS
# ==========================================
print_step "14. Налаштування cron jobs..."
(crontab -l 2>/dev/null; echo "0 3 * * * find /opt/upgrade-studio-bot/uploads/broadcasts -type f -mtime +30 -delete") | crontab -
(crontab -l 2>/dev/null; echo "0 4 * * * journalctl --vacuum-time=3d") | crontab -

# ==========================================
# 15. СТВОРЕННЯ SYSTEMD СЕРВІСІВ (опціонально)
# ==========================================
print_step "15. Створення systemd сервісів..."

#Bot service
cat > /etc/systemd/system/upgrade-bot.service << 'SERVICEEOF'
[Unit]
Description=UPGRADE Studio Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/upgrade-studio-bot
ExecStart=/opt/upgrade-studio-bot/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=append:/opt/upgrade-studio-bot/logs/bot.log
StandardError=append:/opt/upgrade-studio-bot/logs/bot.log

[Install]
WantedBy=multi-user.target
SERVICEEOF

# API service
cat > /etc/systemd/system/upgrade-api.service << 'SERVICEEOF'
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
StandardOutput=append:/opt/upgrade-studio-bot/logs/api.log
StandardError=append:/opt/upgrade-studio-bot/logs/api.log

[Install]
WantedBy=multi-user.target
SERVICEEOF

# Webhook service
cat > /etc/systemd/system/upgrade-webhook.service << 'SERVICEEOF'
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
StandardOutput=append:/opt/upgrade-studio-bot/logs/webhook.log
StandardError=append:/opt/upgrade-studio-bot/logs/webhook.log

[Install]
WantedBy=multi-user.target
SERVICEEOF

# Admin Panel service
cat > /etc/systemd/system/upgrade-admin.service << 'SERVICEEOF'
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
StandardOutput=append:/opt/upgrade-studio-bot/logs/admin_panel.log
StandardError=append:/opt/upgrade-studio-bot/logs/admin_panel.log

[Install]
WantedBy=multi-user.target
SERVICEEOF

systemctl daemon-reload

print_warning "Systemd сервіси створено, але НЕ запущено."
print_warning "Використовуйте ./start_all.sh або systemctl для керування."

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
echo "1. Відредагуйте .env файл:"
echo "   nano /opt/upgrade-studio-bot/.env"
echo ""
echo "2. Налаштуйте DNS для домену admin.upgrade21.com"
echo "   A запис: admin.upgrade21.com -> $(curl -s ifconfig.me)"
echo ""
echo "3. Отримайте SSL сертифікат:"
echo "   certbot --nginx -d admin.upgrade21.com"
echo ""
echo "4. Запустіть сервіси:"
echo "   cd /opt/upgrade-studio-bot"
echo "   ./start_all.sh"
echo ""
echo "5. Перевірте статус:"
echo "   systemctl status nginx"
echo "   tail -f /opt/upgrade-studio-bot/logs/*.log"
echo ""
echo "=============================================="
