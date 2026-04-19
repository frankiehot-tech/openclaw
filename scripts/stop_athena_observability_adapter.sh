#!/usr/bin/env zsh
set -euo pipefail

ROOT="${ATHENA_RUNTIME_ROOT:-/Volumes/1TB-M2/openclaw}"
ENV_FILE="$ROOT/.openclaw/observability.env"
PORT="${ATHENA_OBSERVABILITY_PORT:-8090}"
SCREEN_NAME="athena_observability"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

for session_id in $( (/usr/bin/screen -ls 2>/dev/null || true) | awk '$1 ~ /[0-9]+\.'"$SCREEN_NAME"'$/ { print $1 }' ); do
  /usr/bin/screen -S "$session_id" -X quit >/dev/null 2>&1 || true
done

pkill -f "$ROOT/observability/adapter.py" >/dev/null 2>&1 || true

LISTENER_PID="$( (lsof -n -P -iTCP:${PORT} -sTCP:LISTEN 2>/dev/null || true) | awk 'NR==2 { print $2 }' )"
if [[ -n "${LISTENER_PID:-}" ]]; then
  kill "$LISTENER_PID" >/dev/null 2>&1 || true
fi

rm -f "$ROOT/.openclaw/athena_observability_adapter.pid" \
  "$ROOT/.openclaw/athena_observability_adapter.port" \
  "$ROOT/.openclaw/athena_observability_adapter.status.json"

echo "Athena observability adapter stopped"
