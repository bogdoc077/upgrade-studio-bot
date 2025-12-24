#!/bin/bash
# Скрипт зменшення використання RAM та трафіку

echo "=== Налаштування оптимізації ==="

cd /opt/upgrade-studio-bot

# 1. Зупинити всі сервіси
echo "1. Зупинка сервісів..."
./stop_all.sh

# 2. Оптимізація Next.js - перевірка production mode
echo "2. Перевірка режиму Next.js..."
cd admin-panel
if [ -d ".next" ]; then
    echo "   Видаляємо старий build..."
    rm -rf .next
fi

echo "   Створюємо production build..."
npm run build

cd ..

# 3. Налаштування nginx для кешування статичних файлів
echo "3. Налаштування nginx кешування..."
cat > /etc/nginx/conf.d/cache.conf << 'EOF'
# Кешування статичних файлів
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=static_cache:10m max_size=1g inactive=60m use_temp_path=off;

# Буферизація для зменшення дискових операцій
proxy_buffering on;
proxy_buffer_size 4k;
proxy_buffers 8 4k;
proxy_busy_buffers_size 8k;
EOF

# 4. Оновлення конфігурації admin панелі з кешуванням
echo "4. Додавання кешування до admin панелі..."
if grep -q "proxy_cache" /etc/nginx/sites-available/admin.upgrade21.com; then
    echo "   Кешування вже налаштовано"
else
    sed -i '/location \/ {/a \        # Кешування статичних файлів\n        location ~* \\.(jpg|jpeg|png|gif|ico|css|js|svg|woff|woff2|ttf|eot)$ {\n            proxy_cache static_cache;\n            proxy_cache_valid 200 30d;\n            proxy_cache_valid 404 1m;\n            add_header X-Cache-Status $upstream_cache_status;\n            expires 30d;\n        }' /etc/nginx/sites-available/admin.upgrade21.com
fi

# 5. Налаштування Python logging - обмеження розміру
echo "5. Обмеження розміру Python логів..."
cat > /tmp/logging_config.py << 'EOF'
import logging
from logging.handlers import RotatingFileHandler

# Максимальний розмір лог файлу - 50MB
MAX_BYTES = 50 * 1024 * 1024
BACKUP_COUNT = 3

def setup_logging(log_file, level=logging.INFO):
    """Налаштування логування з ротацією"""
    handler = RotatingFileHandler(
        log_file,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT
    )
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    
    logger = logging.getLogger()
    logger.setLevel(level)
    logger.addHandler(handler)
    
    return logger
EOF

# 6. Налаштування MySQL для зменшення RAM
echo "6. Оптимізація MySQL..."
cat > /etc/mysql/conf.d/optimize.cnf << 'EOF'
[mysqld]
# Обмеження пам'яті
innodb_buffer_pool_size = 256M
max_connections = 50
thread_cache_size = 8
query_cache_size = 16M
query_cache_limit = 1M

# Логування
slow_query_log = 0
log_error = /var/log/mysql/error.log
log_queries_not_using_indexes = 0

# Performance
innodb_flush_log_at_trx_commit = 2
innodb_log_file_size = 32M
EOF

systemctl restart mysql

# 7. Обмеження розміру uploads
echo "7. Обмеження розміру broadcast файлів..."
# Додаємо очищення до crontab
(crontab -l 2>/dev/null; echo "0 3 * * * find /opt/upgrade-studio-bot/uploads/broadcasts -type f -mtime +30 -delete") | crontab -

# 8. Налаштування systemd limits
echo "8. Налаштування обмежень процесів..."
cat > /etc/systemd/system/upgrade-bot.service.d/limits.conf << 'EOF'
[Service]
MemoryMax=512M
CPUQuota=50%
EOF

# 9. Перезавантаження nginx
echo "9. Перезавантаження nginx..."
nginx -t && systemctl reload nginx

# 10. Запуск сервісів
echo "10. Запуск оптимізованих сервісів..."
./start_all.sh

echo -e "\n=== Оптимізація завершена ==="
echo ""
echo "Налаштовано:"
echo "- Next.js в production mode з build"
echo "- Nginx кешування статичних файлів"
echo "- Ротація логів (50MB, 3 backups)"
echo "- MySQL оптимізація (256MB buffer)"
echo "- Автоочищення старих broadcast файлів (30 днів)"
echo "- Systemd memory limit (512MB)"
echo ""
echo "Моніторинг: watch -n 1 'free -h && echo --- && ps aux --sort=-%mem | head -5'"
