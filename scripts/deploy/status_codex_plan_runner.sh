#!/usr/bin/env zsh
set -euo pipefail

ROOT="/Volumes/1TB-M2/openclaw"
PID_FILE="$ROOT/.openclaw/codex_plan_runner.pid"

if [[ -f "$PID_FILE" ]]; then
  PID=$(cat "$PID_FILE" 2>/dev/null | tr -d '\n')
  if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
    echo "running $PID"
    exit 0
  else
    echo "pid_file_stale"
    exit 1
  fi
else
  # Check if process exists via pgrep
  EXISTING_PID="$(pgrep -f "$ROOT/scripts/codex_plan_runner.py" | head -n 1 || true)"
  if [[ -n "${EXISTING_PID:-}" ]]; then
    echo "running_no_pid_file $EXISTING_PID"
    exit 0
  else
    echo "stopped"
    exit 1
  fi
fi