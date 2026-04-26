#!/usr/bin/env zsh
set -euo pipefail

ROOT="${ATHENA_RUNTIME_ROOT:-/Volumes/1TB-M2/openclaw}"
PORT="${ATHENA_WEB_DESKTOP_PORT:-8080}"
SCREEN_NAME="athena_compat"

LISTENER="$( (lsof -n -P -iTCP:${PORT} -sTCP:LISTEN 2>/dev/null || true) | awk 'NR==2 {print $1" "$2}' )"
SCREEN_STATUS="$( (/usr/bin/screen -ls 2>/dev/null || true) | awk '$1 ~ /[0-9]+\.'"$SCREEN_NAME"'$/ { print $1 }' | paste -sd, - )"
PID_FILE="$ROOT/.openclaw/athena_web_desktop_compat.pid"
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
