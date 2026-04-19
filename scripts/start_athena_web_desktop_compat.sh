#!/usr/bin/env zsh
set -euo pipefail

ROOT="${ATHENA_RUNTIME_ROOT:-/Volumes/1TB-M2/openclaw}"
PID_FILE="$ROOT/.openclaw/athena_web_desktop_compat.pid"
PORT_FILE="$ROOT/mini-agent/.web-port"
SESSION_NAME="athena_compat"
WATCH_SCRIPT="$ROOT/scripts/watch_athena_web_desktop_compat.sh"
PORT="${ATHENA_WEB_DESKTOP_PORT:-8080}"

mkdir -p "$ROOT/.openclaw" "$ROOT/logs" "$ROOT/mini-agent"

screen_session_ids() {
  ({ screen -ls 2>/dev/null || true; } | awk '/[.]'"${SESSION_NAME}"'[[:space:]]/ { print $1 }')
}

listener_pid() {
  (lsof -n -P -iTCP:${PORT} -sTCP:LISTEN 2>/dev/null || true) | awk 'NR==2 { print $2 }'
}

if [[ -n "$(listener_pid)" ]]; then
  echo "Athena compat desktop already listening on :${PORT}"
  exit 0
fi

for session_id in $(screen_session_ids); do
  screen -S "$session_id" -X quit >/dev/null 2>&1 || true
  sleep 1
done

pkill -f "$ROOT/scripts/athena_web_desktop_compat.py" >/dev/null 2>&1 || true

screen -dmS "$SESSION_NAME" /bin/zsh -lc "$WATCH_SCRIPT"
echo "$PORT" >"$PORT_FILE"

for _ in {1..30}; do
  if [[ -n "$(listener_pid)" ]]; then
    SCREEN_PID="$( { screen -ls 2>/dev/null || true; } | awk '/[.]'"${SESSION_NAME}"'[[:space:]]/ { split($1, parts, "."); print parts[1]; exit }')"
    if [[ -n "${SCREEN_PID:-}" ]]; then
      echo "$SCREEN_PID" >"$PID_FILE"
    fi
    echo "Athena compat watchdog online and listener ready on :${PORT}"
    exit 0
  fi
  if [[ -z "$(screen_session_ids)" ]]; then
    break
  fi
  sleep 1
done

echo "Failed to start Athena compat desktop on :${PORT}" >&2
tail -n 60 "$ROOT/logs/athena_web_desktop_compat.log" >&2 2>/dev/null || true
tail -n 60 "$ROOT/logs/athena_web_desktop_compat.watchdog.log" >&2 2>/dev/null || true
exit 1
