#!/usr/bin/env zsh
set -euo pipefail

ROOT="${ATHENA_RUNTIME_ROOT:-/Volumes/1TB-M2/openclaw}"
LOG_FILE="$ROOT/logs/athena_observability_adapter.log"
ENV_FILE="$ROOT/.openclaw/observability.env"
PORT="${ATHENA_OBSERVABILITY_PORT:-8090}"
VENV_DIR="$ROOT/.venvs/athena-observability"
PYTHON_BIN="/opt/homebrew/bin/python3"

mkdir -p "$ROOT/.openclaw" "$ROOT/logs" "$ROOT/.venvs"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

if [[ -x "$VENV_DIR/bin/python" ]]; then
  PYTHON_BIN="$VENV_DIR/bin/python"
fi

export HOME="/Users/frankie"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

exec >>"$LOG_FILE" 2>&1
echo "[$(/bin/date '+%Y-%m-%d %H:%M:%S %z')] starting Athena Observability Adapter from $ROOT on :${PORT}"

exec "$PYTHON_BIN" "$ROOT/observability/adapter.py" --port "$PORT"
