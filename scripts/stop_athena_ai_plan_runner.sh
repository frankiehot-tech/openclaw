#!/usr/bin/env zsh
set -euo pipefail

ROOT="${ATHENA_RUNTIME_ROOT:-/Volumes/1TB-M2/openclaw}"
PID_FILE="$ROOT/.openclaw/athena_ai_plan_runner.pid"
SESSION_NAME="athena_plan_runner"

# Kill process from PID file if it exists
if [[ -f "$PID_FILE" ]]; then
  PID=$(cat "$PID_FILE" 2>/dev/null | tr -d '\n')
  if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
    kill "$PID" 2>/dev/null || true
    sleep 0.5
    if kill -0 "$PID" 2>/dev/null; then
      kill -9 "$PID" 2>/dev/null || true
    fi
  fi
fi

# Stop screen sessions
SCREEN_IDS="$( { screen -ls 2>/dev/null || true; } | awk '/[.]'"${SESSION_NAME}"'[[:space:]]/ { print $1 }')"
if [[ -n "${SCREEN_IDS//[[:space:]]/}" ]]; then
  while IFS= read -r screen_id; do
    [[ -z "${screen_id:-}" ]] && continue
    screen -S "$screen_id" -X quit || true
  done <<< "$SCREEN_IDS"
  echo "Stopped Athena AI plan runner sessions."
fi

# Final cleanup via pgrep (fallback)
pkill -f "$ROOT/scripts/athena_ai_plan_runner.py" 2>/dev/null || true

rm -f "$PID_FILE"
