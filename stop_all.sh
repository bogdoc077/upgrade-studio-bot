#!/usr/bin/env bash
set -euo pipefail

# stop_all.sh
# Зупинка всіх сервісів: API, Webhook, Admin Panel

SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Зупинка всіх сервісів ==="
echo ""

# Функція для зупинки процесів за PID файлом
stop_by_pidfile() {
  local pidfile=$1
  local name=$2
  
  if [ -f "$pidfile" ]; then
    pid=$(cat "$pidfile")
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      echo "→ Зупинка $name (PID: $pid)"
      kill -TERM "$pid" 2>/dev/null || kill -9 "$pid" 2>/dev/null || echo "  Не вдалося зупинити $pid"
      sleep 1
    fi
    rm -f "$pidfile"
  fi
}

# Зупинка за PID файлами
echo "1. Зупинка за PID файлами..."
stop_by_pidfile ".pids_api" "API Server"
stop_by_pidfile ".pids_webhook" "Webhook Server"
stop_by_pidfile ".pids_admin_panel" "Admin Panel"
echo ""

# Зупинка залишкових процесів
echo "2. Перевірка залишкових процесів..."

# API Server
if ps aux | grep "start_api.py" | grep -v grep >/dev/null; then
  ps aux | grep "start_api.py" | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null && echo "✓ Зупинено API Server" || true
fi

# Webhook Server
if ps aux | grep "webhook_server.py" | grep -v grep >/dev/null; then
  ps aux | grep "webhook_server.py" | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null && echo "✓ Зупинено Webhook Server" || true
fi

# ВАЖЛИВО: НЕ зупиняємо main.py оскільки він більше не використовується (webhooks замість polling)
# Якщо main.py запущено - це помилка, попереджаємо
if ps aux | grep "main.py" | grep -v grep >/dev/null; then
  echo "⚠️  Знайдено main.py (polling режим) - зупиняємо..."
  ps aux | grep "main.py" | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null && echo "✓ Зупинено main.py (polling не рекомендується!)" || true
fi

# Next.js Admin Panel
echo "→ Зупинка Next.js процесів..."
pkill -f "next dev" 2>/dev/null && echo "  ✓ next dev" || true
pkill -f "next start" 2>/dev/null && echo "  ✓ next start" || true
pkill -f "next-server" 2>/dev/null && echo "  ✓ next-server" || true
ps aux | grep "node.*admin-panel" | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null && echo "  ✓ Node.js admin-panel" || true
echo ""

# Звільнення портів
echo "3. Звільнення портів..."
lsof -ti:8001 | xargs kill -9 2>/dev/null && echo "✓ Порт 8001 (API) звільнено" || true
lsof -ti:8000 | xargs kill -9 2>/dev/null && echo "✓ Порт 8000 (Webhook) звільнено" || true
lsof -ti:3000 | xargs kill -9 2>/dev/null && echo "✓ Порт 3000 (Admin) звільнено" || true
echo ""

echo "=== Всі сервіси зупинено ==="
echo ""
echo "Перевірка процесів:"
if ps aux | grep -E "start_api.py|webhook_server.py|main.py|next" | grep -v grep >/dev/null; then
  echo "⚠️  Деякі процеси все ще працюють:"
  ps aux | grep -E "start_api.py|webhook_server.py|main.py|next" | grep -v grep | awk '{print "  PID " $2 ": " $11}'
else
  echo "✓ Всі процеси зупинено"
fi
echo ""
echo "Логи зберігаються в: ${SCRIPT_DIR}/logs/"
