#!/usr/bin/env zsh
set -euo pipefail

# stop_all.sh
# Stops processes started by start_all.sh by reading pid files (.pids_*)

SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
cd "$SCRIPT_DIR"

pids=(.pids_api .pids_webhook .pids_bot .pids_admin_panel)

for pf in "${pids[@]}"; do
  if [ -f "$pf" ]; then
    pid=$(cat "$pf")
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      echo "Stopping $pid (from $pf)"
      kill "$pid" || echo "Could not kill $pid"
    else
      echo "No running pid found in $pf"
    fi
    rm -f "$pf"
  fi
done

# Зупиняємо залишені процеси за назвами (fallback)
echo "Checking for remaining processes..."

# Зупиняємо FastAPI процеси
pkill -f "start_api.py" 2>/dev/null && echo "Stopped remaining API processes" || true

# Зупиняємо webhook процеси
pkill -f "start_webhook.py" 2>/dev/null && echo "Stopped remaining webhook processes" || true

# Зупиняємо bot процеси
pkill -f "main.py.*telegram" 2>/dev/null && echo "Stopped remaining bot processes" || true

# Зупиняємо Next.js процеси
pkill -f "npm run dev" 2>/dev/null && echo "Stopped remaining npm dev processes" || true
pkill -f "next dev" 2>/dev/null && echo "Stopped remaining next dev processes" || true

echo "Finished stopping known services. Check ./logs for output or manually inspect running processes if something remains."
