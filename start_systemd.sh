#!/usr/bin/env bash
set -euo pipefail

# start_systemd.sh
# Start all services using systemd

echo "=== Запуск всіх сервісів через systemd ==="

# Start services
sudo systemctl start upgrade-bot-api
sudo systemctl start upgrade-bot-webhook
sudo systemctl start upgrade-bot-main
sudo systemctl start upgrade-bot-admin

# Wait for services to start
sleep 3

echo ""
echo "=== Статус сервісів ==="
sudo systemctl status upgrade-bot-api --no-pager -l | head -10
echo ""
sudo systemctl status upgrade-bot-webhook --no-pager -l | head -10
echo ""
sudo systemctl status upgrade-bot-main --no-pager -l | head -10
echo ""
sudo systemctl status upgrade-bot-admin --no-pager -l | head -10

echo ""
echo "=== Використання ресурсів ==="
sudo systemctl status upgrade-bot-* --no-pager | grep -E "upgrade-bot-|Memory:"

echo ""
echo "=== Сервіси запущені ==="
echo "Для перегляду логів: journalctl -u upgrade-bot-<service> -f"
echo "Для зупинки: sudo systemctl stop upgrade-bot-<service>"
echo "Для перезапуску: sudo systemctl restart upgrade-bot-<service>"
