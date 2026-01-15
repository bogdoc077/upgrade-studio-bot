#!/usr/bin/env bash
set -euo pipefail

# status.sh
# Перевірка статусу всіх сервісів

SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Статус сервісів ==="
echo ""

# Функція перевірки процесу
check_process() {
  local name=$1
  local pattern=$2
  local port=$3
  
  echo "→ $name"
  
  if ps aux | grep "$pattern" | grep -v grep >/dev/null; then
    pid=$(ps aux | grep "$pattern" | grep -v grep | awk '{print $2}' | head -1)
    cpu=$(ps aux | grep "$pattern" | grep -v grep | awk '{print $3}' | head -1)
    mem=$(ps aux | grep "$pattern" | grep -v grep | awk '{print $4}' | head -1)
    echo "  ✓ Запущено (PID: $pid, CPU: $cpu%, RAM: $mem%)"
    
    if [ -n "$port" ]; then
      if lsof -ti:$port >/dev/null 2>&1; then
        echo "  ✓ Порт $port: відкритий"
      else
        echo "  ✗ Порт $port: не доступний"
      fi
    fi
  else
    echo "  ✗ Не запущено"
  fi
  echo ""
}

# Перевірка сервісів
check_process "API Server" "start_api.py" "8001"
check_process "Webhook Server (Telegram + Stripe)" "webhook_server.py" "8000"
check_process "Admin Panel (Next.js)" "next.*3000" "3000"

# Перевірка polling bot (не має бути запущеним)
echo "→ Telegram Bot Polling (має бути вимкнено)"
if ps aux | grep "main.py" | grep -v grep >/dev/null; then
  echo "  ⚠️  УВАГА: main.py запущено (polling режим)"
  echo "     Це створює конфлікт з webhooks!"
  echo "     Зупиніть: ps aux | grep main.py | grep -v grep | awk '{print \$2}' | xargs kill"
else
  echo "  ✓ Не запущено (правильно, використовується webhook)"
fi
echo ""

# Загальна статистика
echo "=== Використання ресурсів ==="
echo ""

# CPU та RAM
if command -v top >/dev/null 2>&1; then
  if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    echo "CPU: $(top -l 1 | grep "CPU usage" | awk '{print $3}' | sed 's/%//')"
    echo "RAM: $(top -l 1 | grep "PhysMem" | awk '{print $2}')"
  else
    # Linux
    cpu_idle=$(top -bn1 | grep "Cpu(s)" | awk '{print $8}' | sed 's/%id,//')
    cpu_used=$(echo "100 - $cpu_idle" | bc 2>/dev/null || echo "N/A")
    echo "CPU використано: $cpu_used%"
    free -h | grep "Mem:" | awk '{print "RAM: " $3 " / " $2 " (" int($3/$2*100) "%)"}'
  fi
fi
echo ""

# Порти
echo "=== Відкриті порти ==="
lsof -iTCP -sTCP:LISTEN -P -n 2>/dev/null | grep -E ":8000|:8001|:3000" | awk '{print $1 " (PID " $2 "): " $9}' | sort -u || echo "Порти не знайдено"
echo ""

# Логи
echo "=== Останні помилки в логах ==="
if [ -d "${SCRIPT_DIR}/logs" ]; then
  for log in ${SCRIPT_DIR}/logs/*.log; do
    if [ -f "$log" ]; then
      errors=$(grep -i "error\|exception\|failed" "$log" 2>/dev/null | tail -3 || true)
      if [ -n "$errors" ]; then
        echo "$(basename $log):"
        echo "$errors"
        echo ""
      fi
    fi
  done
else
  echo "Директорія logs/ не знайдена"
fi

echo "=== Кінець статусу ==="
