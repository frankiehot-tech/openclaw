#!/usr/bin/env zsh
set -euo pipefail

ROOT="/Volumes/1TB-M2/openclaw"
PID_FILE="$ROOT/.openclaw/codex_plan_runner.pid"
SESSION_NAME="codex_plan_runner"

mkdir -p "$ROOT/.openclaw" "$ROOT/logs"

# Check if PID file exists and process is alive
if [[ -f "$PID_FILE" ]]; then
  PID=$(cat "$PID_FILE" 2>/dev/null | tr -d '\n')
  if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
    echo "$PID"
    exit 0
  else
    # Stale PID file
    rm -f "$PID_FILE"
  fi
fi

# Check for existing screen session
SCREEN_PID="$( { screen -ls 2>/dev/null || true; } | awk '/[.]'"${SESSION_NAME}"'[[:space:]]/ { split($1, parts, "."); print parts[1]; exit }')"
if [[ -n "${SCREEN_PID:-}" ]]; then
  echo "${SCREEN_PID:-Codex plan runner already running in screen}"
  exit 0
fi

# Check for existing process via pgrep (fallback)
EXISTING_PID="$(pgrep -f "$ROOT/scripts/codex_plan_runner.py" | head -n 1 || true)"
if [[ -n "${EXISTING_PID:-}" ]]; then
  echo "${EXISTING_PID:-Codex plan runner already running}"
  exit 0
fi

# Start new screen session
screen -dmS "$SESSION_NAME" /opt/homebrew/bin/python3 "$ROOT/scripts/codex_plan_runner.py"
sleep 1
SCREEN_PID="$( { screen -ls 2>/dev/null || true; } | awk '/[.]'"${SESSION_NAME}"'[[:space:]]/ { split($1, parts, "."); print parts[1]; exit }')"
echo "Codex plan runner started: ${SCREEN_PID:-unknown}"
