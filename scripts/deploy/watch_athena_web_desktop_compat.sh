#!/usr/bin/env zsh
set -euo pipefail

ROOT="${ATHENA_RUNTIME_ROOT:-/Volumes/1TB-M2/openclaw}"
RUN_SCRIPT="$ROOT/scripts/run_athena_web_desktop_compat.sh"
LOG_DIR="$ROOT/logs"
LOG_FILE="$LOG_DIR/athena_web_desktop_compat.watchdog.log"
PORT="${ATHENA_WEB_DESKTOP_PORT:-8080}"
INTERVAL="${ATHENA_COMPAT_WATCH_INTERVAL:-2}"

mkdir -p "$LOG_DIR"

export HOME="/Volumes/1TB-M2/openclaw"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

exec >>"$LOG_FILE" 2>&1
echo "[$(/bin/date '+%Y-%m-%d %H:%M:%S %z')] watchdog started"

listener_pid() {
  (lsof -n -P -iTCP:${PORT} -sTCP:LISTEN 2>/dev/null || true) | awk 'NR==2 { print $2 }'
}

while true; do
  if [[ -n "$(listener_pid)" ]]; then
    sleep "$INTERVAL"
    continue
  fi

  echo "[$(/bin/date '+%Y-%m-%d %H:%M:%S %z')] listener missing, starting Athena compat"
  if ! /bin/zsh -lc "$RUN_SCRIPT"; then
    echo "[$(/bin/date '+%Y-%m-%d %H:%M:%S %z')] Athena compat process exited unexpectedly"
    sleep 2
  fi
done
