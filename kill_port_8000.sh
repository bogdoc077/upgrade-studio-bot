#!/bin/bash
# Скрипт для зупинки всіх процесів на порту 8000 та перезапуску сервісів

echo "🔍 Шукаємо процеси на порту 8000..."
lsof -ti:8000 | while read pid; do
    echo "  Вбиваємо процес $pid"
    kill -9 $pid
done

echo ""
echo "🔄 Перезапуск сервісів..."
systemctl restart upgrade-webhook
systemctl restart upgrade-api
systemctl restart upgrade-admin

echo ""
echo "✅ Статус сервісів:"
systemctl status upgrade-webhook --no-pager | head -15
