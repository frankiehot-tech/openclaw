#!/usr/bin/env zsh
set -euo pipefail

ROOT="${ATHENA_RUNTIME_ROOT:-/Volumes/1TB-M2/openclaw}"
ENV_FILE="$ROOT/.openclaw/observability.env"
PORT="${ATHENA_OBSERVABILITY_PORT:-8090}"
SCREEN_NAME="athena_observability"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

LISTENER="$( (lsof -n -P -iTCP:${PORT} -sTCP:LISTEN 2>/dev/null || true) | awk 'NR==2 {print $1 " " $2}' )"
SCREEN_STATUS="$( (/usr/bin/screen -ls 2>/dev/null || true) | awk '$1 ~ /[0-9]+\.'"$SCREEN_NAME"'$/ { print $1 }' | paste -sd, - )"
PID_FILE="$ROOT/.openclaw/athena_observability_adapter.pid"
STATUS_FILE="$ROOT/.openclaw/athena_observability_adapter.status.json"
PID_VALUE=""

if [[ -f "$PID_FILE" ]]; then
  PID_VALUE="$(tr -d '\n' < "$PID_FILE")"
fi

if [[ -n "${LISTENER:-}" ]]; then
  echo "listener=${LISTENER}"
else
  echo "listener=none"
fi

if [[ -n "${SCREEN_STATUS:-}" ]]; then
  echo "screen=${SCREEN_STATUS}"
else
  echo "screen=none"
fi

if [[ -n "${PID_VALUE:-}" ]]; then
  echo "pid_file=${PID_VALUE}"
else
  echo "pid_file=missing"
fi

if [[ -f "$STATUS_FILE" ]]; then
  echo "status_file=$STATUS_FILE"
  jq -c '{service, port, runtime_root, observability}' "$STATUS_FILE" 2>/dev/null || cat "$STATUS_FILE"
else
  echo "status_file=missing"
fi
