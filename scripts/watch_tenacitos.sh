#!/usr/bin/env zsh
set -euo pipefail

ROOT="/Volumes/1TB-M2/openclaw"
RUN_SCRIPT="$ROOT/scripts/run_tenacitos.sh"
LOG_DIR="$ROOT/vendor/tenacitOS/logs"
LOG_FILE="$LOG_DIR/tenacitOS.watchdog.log"
INTERVAL="${TENACITOS_WATCH_INTERVAL:-5}"

mkdir -p "$LOG_DIR"

export HOME="/Users/frankie"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

exec >>"$LOG_FILE" 2>&1
echo "[$(/bin/date '+%Y-%m-%d %H:%M:%S %z')] watchdog started"

listener_pid() {
  (lsof -n -P -iTCP:3000 -sTCP:LISTEN 2>/dev/null || true) | awk 'NR==2 { print $2 }'
}

while true; do
  if [[ -n "$(listener_pid)" ]]; then
    sleep "$INTERVAL"
    continue
  fi

  echo "[$(/bin/date '+%Y-%m-%d %H:%M:%S %z')] listener missing, starting TenacitOS"
  if ! /bin/zsh -lc "$RUN_SCRIPT"; then
    echo "[$(/bin/date '+%Y-%m-%d %H:%M:%S %z')] TenacitOS process exited unexpectedly"
    sleep 2
  fi
done
