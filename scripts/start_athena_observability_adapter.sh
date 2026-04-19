#!/usr/bin/env zsh
set -euo pipefail

ROOT="${ATHENA_RUNTIME_ROOT:-/Volumes/1TB-M2/openclaw}"
PID_FILE="$ROOT/.openclaw/athena_observability_adapter.pid"
PORT_FILE="$ROOT/.openclaw/athena_observability_adapter.port"
SESSION_NAME="athena_observability"
WATCH_SCRIPT="$ROOT/scripts/watch_athena_observability_adapter.sh"
ENV_FILE="$ROOT/.openclaw/observability.env"
PORT="${ATHENA_OBSERVABILITY_PORT:-8090}"

mkdir -p "$ROOT/.openclaw" "$ROOT/logs"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

screen_session_ids() {
  ({ screen -ls 2>/dev/null || true; } | awk '/[.]'"${SESSION_NAME}"'[[:space:]]/ { print $1 }')
}

listener_pid() {
  (lsof -n -P -iTCP:${PORT} -sTCP:LISTEN 2>/dev/null || true) | awk 'NR==2 { print $2 }'
}

if [[ -n "$(listener_pid)" ]]; then
  echo "Athena observability adapter already listening on :${PORT}"
  exit 0
fi

for session_id in $(screen_session_ids); do
  screen -S "$session_id" -X quit >/dev/null 2>&1 || true
  sleep 1
done

pkill -f "$ROOT/observability/adapter.py" >/dev/null 2>&1 || true

screen -dmS "$SESSION_NAME" /bin/zsh -lc "$WATCH_SCRIPT"
echo "$PORT" >"$PORT_FILE"

for _ in {1..30}; do
  if [[ -n "$(listener_pid)" ]]; then
    SCREEN_PID="$( { screen -ls 2>/dev/null || true; } | awk '/[.]'"${SESSION_NAME}"'[[:space:]]/ { split($1, parts, "."); print parts[1]; exit }')"
    if [[ -n "${SCREEN_PID:-}" ]]; then
      echo "$SCREEN_PID" >"$PID_FILE"
    fi
    echo "Athena observability watchdog online and listener ready on :${PORT}"
    exit 0
  fi
  if [[ -z "$(screen_session_ids)" ]]; then
    break
  fi
  sleep 1
done

echo "Failed to start Athena observability adapter on :${PORT}" >&2
tail -n 60 "$ROOT/logs/athena_observability_adapter.log" >&2 2>/dev/null || true
tail -n 60 "$ROOT/logs/athena_observability_adapter.watchdog.log" >&2 2>/dev/null || true
exit 1
