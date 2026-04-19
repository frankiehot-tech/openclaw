#!/usr/bin/env zsh
set -euo pipefail

ROOT="${ATHENA_RUNTIME_ROOT:-/Volumes/1TB-M2/openclaw}"
PLAN_DIR="${ATHENA_PLAN_DIR:-/Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan}"
PID_FILE="$ROOT/.openclaw/openhuman_24h_stress_runner.pid"
SESSION_NAME="openhuman_24h_stress_runner"
REPORT_PATH="$PLAN_DIR/OpenHuman-Athena-24小时压力测试执行报告.md"
OUTPUT_ROOT="$ROOT/workspace/stress_test"
LOG_FILE="$ROOT/logs/openhuman_24h_stress_runner.log"

mkdir -p "$ROOT/.openclaw" "$ROOT/logs" "$OUTPUT_ROOT"

if [[ -f "$PID_FILE" ]]; then
  PID=$(cat "$PID_FILE" 2>/dev/null | tr -d '\n')
  if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
    echo "$PID"
    exit 0
  else
    rm -f "$PID_FILE"
  fi
fi

SCREEN_PID="$( { screen -ls 2>/dev/null || true; } | awk '/[.]'"${SESSION_NAME}"'[[:space:]]/ { split($1, parts, "."); print parts[1]; exit }')"
if [[ -n "${SCREEN_PID:-}" ]]; then
  echo "${SCREEN_PID:-OpenHuman 24h stress runner already running in screen}"
  exit 0
fi

EXISTING_PID="$(pgrep -f "$ROOT/scripts/openhuman_24h_stress_runner.py" | head -n 1 || true)"
if [[ -n "${EXISTING_PID:-}" ]]; then
  echo "${EXISTING_PID:-OpenHuman 24h stress runner already running}"
  exit 0
fi

screen -dmS "$SESSION_NAME" /bin/zsh -lc "\
  export ATHENA_AUTORESEARCH_ENABLED=1; \
  export ATHENA_AUTORESEARCH_DRY_RUN=1; \
  export PYTHONUNBUFFERED=1; \
  /opt/homebrew/bin/python3 '$ROOT/scripts/openhuman_24h_stress_runner.py' \
    --duration-hours 24 \
    --sample-seconds 300 \
    --performance-seconds 900 \
    --stability-seconds 900 \
    --autoresearch-seconds 3600 \
    --report-path '$REPORT_PATH' \
    --output-root '$OUTPUT_ROOT' \
    --write-pid >> '$LOG_FILE' 2>&1"
sleep 1
if [[ -f "$PID_FILE" ]]; then
  echo "$(cat "$PID_FILE" 2>/dev/null | tr -d '\n')"
  exit 0
fi

SCREEN_PID="$( { screen -ls 2>/dev/null || true; } | awk '/[.]'"${SESSION_NAME}"'[[:space:]]/ { split($1, parts, "."); print parts[1]; exit }')"
if [[ -n "${SCREEN_PID:-}" ]]; then
  echo "${SCREEN_PID}"
  exit 0
fi

echo "Failed to start OpenHuman 24h stress runner" >&2
exit 1
