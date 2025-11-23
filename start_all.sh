#!/usr/bin/env zsh
set -euo pipefail

# start_all.sh
# Послідовний запуск всіх сервісів: API, Webhook, Bot, Admin Panel

SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
cd "$SCRIPT_DIR"

mkdir -p logs

echo "=== Запуск всіх сервісів проекту ==="
echo ""

# Активація venv
if [ -f "${SCRIPT_DIR}/venv/bin/activate" ]; then
  source "${SCRIPT_DIR}/venv/bin/activate"
  PY="${SCRIPT_DIR}/venv/bin/python"
  echo "✓ Використовується venv Python"
elif command -v python3 >/dev/null 2>&1; then
  PY=python3
  echo "⚠ venv не знайдено, використовується system python3"
else
  PY=python
  echo "⚠ venv не знайдено, використовується system python"
fi

echo ""

# Функція запуску сервісу в фоні
start_service() {
  local name=$1
  local script=$2
  local logfile=$3
  local port=$4
  
  echo "→ Запуск $name..."
  
  # Перевірка чи існує скрипт
  if [ ! -f "$script" ]; then
    echo "✗ Файл $script не знайдено"
    return 1
  fi
  
  # Звільнення порту якщо зайнятий
  if [ -n "$port" ]; then
    lsof -ti:$port | xargs kill -9 2>/dev/null && echo "  Порт $port звільнено" || true
    sleep 1
  fi
  
  # Запуск
  nohup $PY "$script" >"$logfile" 2>&1 &
  local pid=$!
  echo $pid >"${SCRIPT_DIR}/.pids_${name}"
  
  # Перевірка чи процес запустився
  sleep 2
  if kill -0 $pid 2>/dev/null; then
    echo "✓ $name запущено (PID: $pid)"
    if [ -n "$port" ]; then
      echo "  Порт: $port, Лог: $logfile"
    else
      echo "  Лог: $logfile"
    fi
    return 0
  else
    echo "✗ $name не вдалося запустити (перевірте $logfile)"
    return 1
  fi
}

# 1. API Server (порт 8001)
echo "1. API Server"
start_service "api" "start_api.py" "${SCRIPT_DIR}/logs/api.log" "8001"
echo ""

# 2. Webhook Server (порт 8000)
echo "2. Webhook Server"
start_service "webhook" "webhook_server.py" "${SCRIPT_DIR}/logs/webhook.log" "8000"
echo ""

# 3. Telegram Bot
echo "3. Telegram Bot"
start_service "bot" "main.py" "${SCRIPT_DIR}/logs/bot.log" ""
echo ""

# 4. Admin Panel (Next.js, порт 3000)
echo "4. Admin Panel (Next.js)"
if [ -d "${SCRIPT_DIR}/admin-panel" ]; then
  cd "${SCRIPT_DIR}/admin-panel"
  
  # Перевірка node_modules
  if [ ! -d "node_modules" ]; then
    echo "  node_modules відсутні, запуск npm install..."
    npm install
  fi
  
  # Звільнення порту
  lsof -ti:3000 | xargs kill -9 2>/dev/null && echo "  Порт 3000 звільнено" || true
  sleep 1
  
  # Запуск Next.js
  echo "→ Запуск Admin Panel..."
  nohup npm start >"${SCRIPT_DIR}/logs/admin_panel.log" 2>&1 &
  pid=$!
  echo $pid >"${SCRIPT_DIR}/.pids_admin_panel"
  
  # Очікування запуску (Next.js довше стартує)
  echo "  Очікування запуску Next.js..."
  sleep 5
  
  if kill -0 $pid 2>/dev/null; then
    echo "✓ Admin Panel запущено (PID: $pid)"
    echo "  URL: http://localhost:3000"
    echo "  Лог: ${SCRIPT_DIR}/logs/admin_panel.log"
  else
    echo "✗ Admin Panel не вдалося запустити"
  fi
  
  cd "$SCRIPT_DIR"
else
  echo "✗ Директорія admin-panel не знайдена"
fi

echo ""
echo "=== Статус сервісів ==="
ps aux | grep -E "start_api.py|webhook_server.py|main.py|next dev" | grep -v grep | awk '{print "PID " $2 ": " $11 " " $12 " " $13}' || echo "Жодного процесу не знайдено"

echo ""
echo "=== Запуск завершено ==="
echo "Логи: ${SCRIPT_DIR}/logs/*.log"
echo "PID файли: ${SCRIPT_DIR}/.pids_*"
echo ""
echo "Для зупинки всіх сервісів: ./stop_all.sh"
