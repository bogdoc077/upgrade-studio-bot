#!/usr/bin/env bash
set -euo pipefail

# restart_systemd.sh
# Restart all services using systemd

echo "=== Перезапуск всіх сервісів через systemd ==="

# Restart services
sudo systemctl restart upgrade-bot-api
sudo systemctl restart upgrade-bot-webhook
sudo systemctl restart upgrade-bot-main
sudo systemctl restart upgrade-bot-admin

# Wait for services to start
sleep 3

echo ""
echo "=== Статус сервісів ==="
sudo systemctl status upgrade-bot-* --no-pager | grep -E "upgrade-bot-|Active:|Memory:"

echo ""
echo "=== Сервіси перезапущено ==="
