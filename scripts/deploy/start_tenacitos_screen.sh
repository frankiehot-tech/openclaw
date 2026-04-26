#!/usr/bin/env zsh
set -euo pipefail

ROOT="/Volumes/1TB-M2/openclaw"
WATCH_SCRIPT="$ROOT/scripts/watch_tenacitos.sh"
SCREEN_NAME="tenacitos"
PORT=3000
LOG_DIR="$ROOT/vendor/tenacitOS/logs"

mkdir -p "$LOG_DIR"

screen_session_ids() {
  (/usr/bin/screen -ls 2>/dev/null || true) | awk '$1 ~ /[0-9]+\.'"$SCREEN_NAME"'$/ { print $1 }'
}

listener_pid() {
  (lsof -n -P -iTCP:${PORT} -sTCP:LISTEN 2>/dev/null || true) | awk 'NR==2 { print $2 }'
}

if [[ -n "$(screen_session_ids)" ]]; then
  echo "TenacitOS watchdog already running"
  exit 0
fi

for session_id in $(screen_session_ids); do
  /usr/bin/screen -S "$session_id" -X quit >/dev/null 2>&1 || true
  sleep 1
done

/usr/bin/screen -dmS "$SCREEN_NAME" /bin/zsh -lc "$WATCH_SCRIPT"

for _ in {1..30}; do
  if [[ -n "$(listener_pid)" ]]; then
    echo "TenacitOS watchdog online and listener ready on :${PORT}"
    exit 0
  fi
  if [[ -z "$(screen_session_ids)" ]]; then
    break
  fi
  sleep 1
done

echo "Failed to start TenacitOS on :${PORT}" >&2
if [[ -f "$LOG_DIR/tenacitOS.runtime.log" ]]; then
  tail -n 40 "$LOG_DIR/tenacitOS.runtime.log" >&2 || true
fi
if [[ -f "$LOG_DIR/tenacitos.watchdog.log" ]]; then
  tail -n 40 "$LOG_DIR/tenacitos.watchdog.log" >&2 || true
fi
exit 1
