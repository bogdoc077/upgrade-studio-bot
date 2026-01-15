#!/usr/bin/env bash
set -euo pipefail

# restart_all.sh
# Перезапуск всіх сервісів

SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Перезапуск всіх сервісів ==="
echo ""

# Зупинка
echo "1. Зупинка сервісів..."
./stop_all.sh
echo ""

# Пауза
echo "2. Очікування 3 секунди..."
sleep 3
echo ""

# Запуск
echo "3. Запуск сервісів..."
./start_all.sh
