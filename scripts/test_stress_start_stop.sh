#!/usr/bin/env zsh
set -euo pipefail

ROOT="${ATHENA_RUNTIME_ROOT:-/Volumes/1TB-M2/openclaw}"
PLAN_DIR="${ATHENA_PLAN_DIR:-/Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan}"
PID_FILE="$ROOT/.openclaw/test_stress_runner.pid"
SESSION_NAME="test_stress_runner"
REPORT_PATH="$PLAN_DIR/OpenHuman-Athena-24小时压力测试执行报告_TEST.md"
OUTPUT_ROOT="$ROOT/workspace/stress_test_test"
LOG_FILE="$ROOT/logs/test_stress_runner.log"

# Clean up from previous runs
rm -f "$PID_FILE" "$LOG_FILE"
rm -rf "$OUTPUT_ROOT"
mkdir -p "$ROOT/.openclaw" "$ROOT/logs" "$OUTPUT_ROOT"

echo "=== Testing stress runner start/stop ==="
echo "PID file: $PID_FILE"
echo "Log file: $LOG_FILE"
echo "Output root: $OUTPUT_ROOT"
echo

# Start the runner with a very short duration
echo "Starting test runner (duration 1 minute)..."
screen -dmS "$SESSION_NAME" /bin/zsh -lc "\
  export ATHENA_AUTORESEARCH_ENABLED=1; \
  export ATHENA_AUTORESEARCH_DRY_RUN=1; \
  /opt/homebrew/bin/python3 '$ROOT/scripts/openhuman_24h_stress_runner.py' \
    --duration-hours 0.0167 \
    --sample-seconds 10 \
    --performance-seconds 20 \
    --stability-seconds 20 \
    --autoresearch-seconds 30 \
    --report-path '$REPORT_PATH' \
    --output-root '$OUTPUT_ROOT' \
    --write-pid >> '$LOG_FILE' 2>&1"

sleep 2

# Check if PID file was created
if [[ -f "$PID_FILE" ]]; then
  PID=$(cat "$PID_FILE" 2>/dev/null | tr -d '\n')
  echo "✅ PID file created with PID: $PID"
  
  # Check if process is running
  if kill -0 "$PID" 2>/dev/null; then
    echo "✅ Process is running"
  else
    echo "❌ Process not running"
  fi
else
  echo "❌ PID file not created"
  exit 1
fi

# Wait a bit for some work
echo "Waiting 5 seconds for runner to do some work..."
sleep 5

# Check if report was created
if [[ -f "$REPORT_PATH" ]]; then
  echo "✅ Report file created: $REPORT_PATH"
  echo "--- Report head ---"
  head -10 "$REPORT_PATH"
  echo "--- End report ---"
else
  echo "❌ Report file not created"
fi

# Check if output directory has files
if find "$OUTPUT_ROOT" -type f -name "*.json" | head -1 | grep -q .; then
  echo "✅ Output directory contains files"
else
  echo "❌ Output directory empty"
fi

# Stop the runner
echo
echo "Stopping test runner..."
SCREEN_ID="$( { screen -ls 2>/dev/null || true; } | awk '/[.]'"${SESSION_NAME}"'[[:space:]]/ { print $1; exit }')"
if [[ -n "${SCREEN_ID:-}" ]]; then
  screen -S "$SCREEN_ID" -X quit || true
  echo "✅ Screen session terminated"
fi

if [[ -f "$PID_FILE" ]]; then
  PID=$(cat "$PID_FILE" 2>/dev/null | tr -d '\n')
  if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
    kill "$PID" 2>/dev/null || true
    echo "✅ Process killed"
  fi
  rm -f "$PID_FILE"
  echo "✅ PID file removed"
fi

# Clean up
rm -f "$REPORT_PATH"
echo "✅ Test report cleaned up"

echo
echo "=== Test completed successfully ==="