#!/usr/bin/env zsh
set -euo pipefail

ROOT="${ATHENA_RUNTIME_ROOT:-/Volumes/1TB-M2/openclaw}"
PID_FILE="$ROOT/.openclaw/athena_web_desktop_compat.pid"
SESSION_NAME="athena_compat"

SCREEN_IDS="$( { screen -ls 2>/dev/null || true; } | awk '/[.]'"${SESSION_NAME}"'[[:space:]]/ { print $1 }')"
if [[ -n "${SCREEN_IDS//[[:space:]]/}" ]]; then
  while IFS= read -r screen_id; do
    [[ -z "${screen_id:-}" ]] && continue
    screen -S "$screen_id" -X quit || true
  done <<< "$SCREEN_IDS"
  echo "Stopped Athena compat desktop session: $SESSION_NAME"
fi

pkill -f "$ROOT/scripts/athena_web_desktop_compat.py" || true

rm -f "$PID_FILE"
