#!/usr/bin/env bash
set -euo pipefail

# stop_systemd.sh
# Stop all services using systemd

echo "=== Зупинка всіх сервісів через systemd ==="

# Stop services
sudo systemctl stop upgrade-bot-api
sudo systemctl stop upgrade-bot-webhook
sudo systemctl stop upgrade-bot-main
sudo systemctl stop upgrade-bot-admin

echo ""
echo "=== Всі сервіси зупинено ==="
echo "Перевірка статусу:"
sudo systemctl is-active upgrade-bot-api upgrade-bot-webhook upgrade-bot-main upgrade-bot-admin || true
