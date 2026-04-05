#!/bin/bash

# Скрипт для перегляду логів бота на сервері

SERVER="root@173.242.49.209"

echo "📋 Перегляд логів UPGRADE Studio Bot"
echo "======================================"
echo ""
echo "Виберіть опцію:"
echo "1) Останні 50 рядків логів"
echo "2) Останні 100 рядків логів"
echo "3) Логи в реальному часі (live)"
echo "4) Логи за останню годину"
echo "5) Пошук запитів на приєднання"
echo "6) Пошук схвалених запитів"
echo "7) Статус сервісу"
echo "8) Перезапустити сервіси"
echo ""
read -p "Введіть номер (1-8): " choice

case $choice in
    1)
        echo "📄 Останні 50 рядків логів:"
        ssh $SERVER "journalctl -u upgrade-webhook.service -n 50 --no-pager"
        ;;
    2)
        echo "📄 Останні 100 рядків логів:"
        ssh $SERVER "journalctl -u upgrade-webhook.service -n 100 --no-pager"
        ;;
    3)
        echo "🔴 Логи в реальному часі (Ctrl+C для виходу):"
        ssh $SERVER "journalctl -u upgrade-webhook.service -f"
        ;;
    4)
        echo "⏰ Логи за останню годину:"
        ssh $SERVER "journalctl -u upgrade-webhook.service --since '1 hour ago' --no-pager"
        ;;
    5)
        echo "🔍 Пошук запитів на приєднання:"
        ssh $SERVER "journalctl -u upgrade-webhook.service --since '24 hours ago' --no-pager | grep -E 'Отримано запит на приєднання|subscription_active|has_access'"
        ;;
    6)
        echo "✅ Пошук схвалених запитів:"
        ssh $SERVER "journalctl -u upgrade-webhook.service --since '24 hours ago' --no-pager | grep -E 'схвалено|approved'"
        ;;
    7)
        echo "📊 Статус сервісів:"
        ssh $SERVER "systemctl status upgrade-webhook.service upgrade-api.service upgrade-admin.service --no-pager"
        ;;
    8)
        echo "🔄 Перезапуск сервісів..."
        ssh $SERVER "systemctl restart upgrade-webhook.service upgrade-api.service && systemctl status upgrade-webhook.service --no-pager"
        echo "✅ Сервіси перезапущено"
        ;;
    *)
        echo "❌ Невірний вибір"
        exit 1
        ;;
esac
