#!/usr/bin/env bash
set -euo pipefail

# stop_all.sh
# Stops all project services: API, Webhook, Bot, Admin Panel

SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Зупинка всіх сервісів ==="

# Функція для зупинки процесів за PID файлом
stop_by_pidfile() {
  local pidfile=$1
  local name=$2
  
  if [ -f "$pidfile" ]; then
    pid=$(cat "$pidfile")
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      echo "Зупинка $name (PID: $pid)"
      kill -9 "$pid" 2>/dev/null || echo "Не вдалося зупинити $pid"
    fi
    rm -f "$pidfile"
  fi
}

# Зупинка за PID файлами
stop_by_pidfile ".pids_api" "API Server"
stop_by_pidfile ".pids_webhook" "Webhook Server"
stop_by_pidfile ".pids_bot" "Telegram Bot"
stop_by_pidfile ".pids_admin_panel" "Admin Panel"

# Зупинка процесів за назвами (fallback)
echo "Перевірка залишкових процесів..."

# API Server
ps aux | grep "start_api.py" | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null && echo "✓ Зупинено API Server" || true

# Webhook Server
ps aux | grep "webhook_server.py" | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null && echo "✓ Зупинено Webhook Server" || true

# Bot
ps aux | grep "main.py" | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null && echo "✓ Зупинено Telegram Bot" || true

# Next.js Admin Panel
pkill -f "next dev" 2>/dev/null && echo "✓ Зупинено Admin Panel (dev)" || true
pkill -f "next start" 2>/dev/null && echo "✓ Зупинено Admin Panel (production)" || true
pkill -f "npm run dev" 2>/dev/null && echo "✓ Зупинено npm dev" || true
pkill -f "npm start" 2>/dev/null && echo "✓ Зупинено npm start" || true

# Звільнення портів (додаткова перевірка)
echo "Звільнення портів..."
lsof -ti:8001 | xargs kill -9 2>/dev/null && echo "✓ Порт 8001 звільнено" || true
lsof -ti:8000 | xargs kill -9 2>/dev/null && echo "✓ Порт 8000 звільнено" || true
lsof -ti:3000 | xargs kill -9 2>/dev/null && echo "✓ Порт 3000 звільнено" || true

echo ""
echo "=== Всі сервіси зупинено ==="
echo "Перевірте логи в ./logs/ якщо потрібно"
