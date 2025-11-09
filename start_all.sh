#!/usr/bin/env zsh
set -euo pipefail

# start_all.sh
# Starts migrations, API server, webhook server, bot and admin-panel (Next.js) in background.
# Writes simple pid files (.pids_*) and logs to ./logs/*. You can stop everything with ./stop_all.sh

SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
cd "$SCRIPT_DIR"

mkdir -p logs

echo "== Starting project from: $SCRIPT_DIR =="

# Detect Python command
if command -v python3 >/dev/null 2>&1; then
  PY=python3
else
  PY=python
fi

# Helper to start a service in background and record PID
start_bg() {
  name=$1
  shift
  logfile=$1
  shift
  echo "Starting $name (log: $logfile)"
  nohup "$@" >"$logfile" 2>&1 &
  pid=$!
  echo $pid >"${SCRIPT_DIR}/.pids_${name}"
  echo "$name pid: $pid"
}

# Start API server
if [ -f "${SCRIPT_DIR}/start_api.py" ]; then
  start_bg api "${SCRIPT_DIR}/logs/api.log" $PY start_api.py
else
  echo "start_api.py not found; skip API start"
fi

# Start webhook server if present
if [ -f "${SCRIPT_DIR}/start_webhook.py" ]; then
  start_bg webhook "${SCRIPT_DIR}/logs/webhook.log" $PY start_webhook.py
else
  echo "start_webhook.py not found; skip webhook start"
fi

# Start bot (main.py)
if [ -f "${SCRIPT_DIR}/main.py" ]; then
  start_bg bot "${SCRIPT_DIR}/logs/bot.log" $PY main.py
else
  echo "main.py not found; skip bot start"
fi

# Start Next.js admin panel
if [ -d "${SCRIPT_DIR}/admin-panel" ]; then
  cd "${SCRIPT_DIR}/admin-panel"
  if [ ! -d "node_modules" ]; then
    echo "node_modules missing in admin-panel. Running npm install (this may take a while)..."
    npm install
  fi
  # Use start_bg function for consistency
  start_bg admin_panel "${SCRIPT_DIR}/logs/admin_panel.log" npm run dev
  cd "$SCRIPT_DIR"
else
  echo "admin-panel directory not found; skip admin-panel start"
fi


echo "\nAll requested services started (where available)."
echo "Logs: $SCRIPT_DIR/logs/*.log"
echo "PID files: $SCRIPT_DIR/.pids_*"
echo "To stop everything run: ./stop_all.sh"

echo "Done."
