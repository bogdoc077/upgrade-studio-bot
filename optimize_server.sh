#!/bin/bash
# Скрипт оптимізації сервера

echo "=== Діагностика сервера ==="

# 1. Перевірка RAM
echo "1. Використання RAM:"
free -h

# 2. Перевірка диску
echo -e "\n2. Використання диску:"
df -h

# 3. Топ процесів по пам'яті
echo -e "\n3. Топ процесів по RAM:"
ps aux --sort=-%mem | head -10

# 4. Топ процесів по CPU
echo -e "\n4. Топ процесів по CPU:"
ps aux --sort=-%cpu | head -10

# 5. Розмір логів
echo -e "\n5. Розмір файлів логів:"
du -sh /opt/upgrade-studio-bot/logs/* 2>/dev/null || echo "Немає логів"

# 6. Розмір uploads
echo -e "\n6. Розмір uploads:"
du -sh /opt/upgrade-studio-bot/uploads/* 2>/dev/null || echo "Немає uploads"

# 7. Мережевий трафік (якщо є vnstat)
echo -e "\n7. Мережевий трафік:"
if command -v vnstat &> /dev/null; then
    vnstat -d
else
    echo "vnstat не встановлено"
fi

echo -e "\n=== Оптимізація ==="

# 8. Ротація логів
echo "8. Налаштування ротації логів..."
cat > /etc/logrotate.d/upgrade-studio-bot << 'EOF'
/opt/upgrade-studio-bot/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 root root
    maxsize 100M
}
EOF

# 9. Очищення старих логів (старше 7 днів)
echo "9. Очищення старих логів..."
find /opt/upgrade-studio-bot/logs -name "*.log" -mtime +7 -exec truncate -s 0 {} \;

# 10. Очищення старих broadcast файлів (старше 30 днів)
echo "10. Очищення старих broadcast файлів..."
find /opt/upgrade-studio-bot/uploads/broadcasts -type f -mtime +30 -delete 2>/dev/null || echo "Немає старих файлів"

# 11. Перевірка MySQL
echo -e "\n11. Оптимізація MySQL..."
mysql -e "SHOW VARIABLES LIKE 'max_connections';"
mysql -e "SHOW VARIABLES LIKE 'innodb_buffer_pool_size';"

# 12. Очищення apt кешу
echo -e "\n12. Очищення apt кешу..."
apt-get clean
apt-get autoclean
apt-get autoremove -y

# 13. Очищення journalctl
echo -e "\n13. Очищення journalctl (залишаємо 3 дні)..."
journalctl --vacuum-time=3d

echo -e "\n=== Оптимізація завершена ==="
echo "Рекомендація: перезапустіть сервіси ./stop_all.sh && ./start_all.sh"
