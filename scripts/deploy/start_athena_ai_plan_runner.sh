#!/usr/bin/env zsh
set -euo pipefail

ROOT="${ATHENA_RUNTIME_ROOT:-/Volumes/1TB-M2/openclaw}"
PID_FILE="$ROOT/.openclaw/athena_ai_plan_runner.pid"
SESSION_NAME="athena_plan_runner"

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
  echo "${SCREEN_PID:-Athena AI plan runner already running in screen}"
  exit 0
fi

# Check for existing process via pgrep (fallback)
EXISTING_PID="$(pgrep -f "$ROOT/scripts/athena_ai_plan_runner.py" | head -n 1 || true)"
if [[ -n "${EXISTING_PID:-}" ]]; then
  echo "${EXISTING_PID:-Athena AI plan runner already running}"
  exit 0
fi

# Start new screen session
# Python's load_dotenv() loads .env directly - no need to pass DASHSCOPE_API_KEY
# Passing env var explicitly would override .env, breaking key rotation
screen -dmS "$SESSION_NAME" /opt/homebrew/bin/python3 "$ROOT/scripts/athena_ai_plan_runner.py"
sleep 1
SCREEN_PID="$( { screen -ls 2>/dev/null || true; } | awk '/[.]'"${SESSION_NAME}"'[[:space:]]/ { split($1, parts, "."); print parts[1]; exit }')"
echo "Athena AI plan runner started: ${SCREEN_PID:-unknown}"
