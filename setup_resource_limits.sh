#!/bin/bash

# Скрипт для налаштування обмеження ресурсів

echo "🔧 Налаштування обмежень ресурсів..."

# Створюємо або оновлюємо systemd unit files з обмеженнями пам'яті

# Bot service
cat > /tmp/upgrade-bot.service << 'EOF'
[Unit]
Description=Upgrade Studio Bot
After=network.target mysql.service
Requires=mysql.service

[Service]
Type=simple
User=admin
WorkingDirectory=/home/admin/upgrade-studio-bot
Environment="PATH=/home/admin/upgrade-studio-bot/venv/bin"
ExecStart=/home/admin/upgrade-studio-bot/venv/bin/python main.py
Restart=always
RestartSec=10

# Обмеження пам'яті
MemoryMax=512M
MemoryHigh=400M

# Обмеження CPU
CPUQuota=50%

# Обмеження процесів
TasksMax=50

[Install]
WantedBy=multi-user.target
EOF

# API service  
cat > /tmp/upgrade-api.service << 'EOF'
[Unit]
Description=Upgrade Studio API
After=network.target mysql.service
Requires=mysql.service

[Service]
Type=simple
User=admin
WorkingDirectory=/home/admin/upgrade-studio-bot
Environment="PATH=/home/admin/upgrade-studio-bot/venv/bin"
ExecStart=/home/admin/upgrade-studio-bot/venv/bin/python start_api.py
Restart=always
RestartSec=10

# Обмеження пам'яті
MemoryMax=512M
MemoryHigh=400M

# Обмеження CPU
CPUQuota=40%

# Обмеження процесів
TasksMax=50

[Install]
WantedBy=multi-user.target
EOF

# Webhook service
cat > /tmp/upgrade-webhook.service << 'EOF'
[Unit]
Description=Upgrade Studio Webhook
After=network.target mysql.service
Requires=mysql.service

[Service]
Type=simple
User=admin
WorkingDirectory=/home/admin/upgrade-studio-bot
Environment="PATH=/home/admin/upgrade-studio-bot/venv/bin"
ExecStart=/home/admin/upgrade-studio-bot/venv/bin/python start_webhook.py
Restart=always
RestartSec=10

# Обмеження пам'яті
MemoryMax=256M
MemoryHigh=200M

# Обмеження CPU
CPUQuota=30%

# Обмеження процесів
TasksMax=30

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Файли конфігурації створено в /tmp"
echo ""
echo "Для застосування виконайте:"
echo "  sudo cp /tmp/upgrade-*.service /etc/systemd/system/"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl restart upgrade-bot upgrade-api upgrade-webhook"
echo ""
echo "Для перевірки статусу:"
echo "  systemctl status upgrade-bot"
echo "  systemctl show upgrade-bot | grep Memory"
