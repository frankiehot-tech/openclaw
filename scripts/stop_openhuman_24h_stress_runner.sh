#!/usr/bin/env zsh
set -euo pipefail

ROOT="${ATHENA_RUNTIME_ROOT:-/Volumes/1TB-M2/openclaw}"
PID_FILE="$ROOT/.openclaw/openhuman_24h_stress_runner.pid"
SESSION_NAME="openhuman_24h_stress_runner"

if [[ -f "$PID_FILE" ]]; then
  PID=$(cat "$PID_FILE" 2>/dev/null | tr -d '\n')
  if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
    kill "$PID" 2>/dev/null || true
    sleep 1
    if kill -0 "$PID" 2>/dev/null; then
      kill -9 "$PID" 2>/dev/null || true
    fi
  fi
  rm -f "$PID_FILE"
fi

SCREEN_ID="$( { screen -ls 2>/dev/null || true; } | awk '/[.]'"${SESSION_NAME}"'[[:space:]]/ { print $1; exit }')"
if [[ -n "${SCREEN_ID:-}" ]]; then
  screen -S "$SCREEN_ID" -X quit || true
fi

EXISTING_PIDS=("${(@f)$(pgrep -f "$ROOT/scripts/openhuman_24h_stress_runner.py" || true)}")
for pid in "${EXISTING_PIDS[@]:-}"; do
  if [[ -n "$pid" ]]; then
    kill "$pid" 2>/dev/null || true
  fi
done

echo "OpenHuman 24h stress runner stopped"
