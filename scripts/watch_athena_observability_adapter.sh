#!/usr/bin/env zsh
set -euo pipefail

ROOT="${ATHENA_RUNTIME_ROOT:-/Volumes/1TB-M2/openclaw}"
RUN_SCRIPT="$ROOT/scripts/run_athena_observability_adapter.sh"
LOG_DIR="$ROOT/logs"
LOG_FILE="$LOG_DIR/athena_observability_adapter.watchdog.log"
ENV_FILE="$ROOT/.openclaw/observability.env"
PORT="${ATHENA_OBSERVABILITY_PORT:-8090}"
INTERVAL="${ATHENA_OBSERVABILITY_WATCH_INTERVAL:-2}"

mkdir -p "$LOG_DIR"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

export HOME="/Users/frankie"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

exec >>"$LOG_FILE" 2>&1
echo "[$(/bin/date '+%Y-%m-%d %H:%M:%S %z')] watchdog started"

listener_pid() {
  (lsof -n -P -iTCP:${PORT} -sTCP:LISTEN 2>/dev/null || true) | awk 'NR==2 { print $2 }'
}

while true; do
  if [[ -n "$(listener_pid)" ]]; then
    sleep "$INTERVAL"
    continue
  fi

  echo "[$(/bin/date '+%Y-%m-%d %H:%M:%S %z')] listener missing, starting Athena observability adapter"
  if ! /bin/zsh -lc "$RUN_SCRIPT"; then
    echo "[$(/bin/date '+%Y-%m-%d %H:%M:%S %z')] Athena observability adapter exited unexpectedly"
    sleep 2
  fi
done
