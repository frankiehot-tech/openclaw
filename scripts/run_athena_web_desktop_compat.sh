#!/usr/bin/env zsh
set -euo pipefail

ROOT="${ATHENA_RUNTIME_ROOT:-/Volumes/1TB-M2/openclaw}"
LOG_FILE="$ROOT/logs/athena_web_desktop_compat.log"

mkdir -p "$ROOT/.openclaw" "$ROOT/logs" "$ROOT/mini-agent"

export HOME="/Users/frankie"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

exec >>"$LOG_FILE" 2>&1
echo "[$(/bin/date '+%Y-%m-%d %H:%M:%S %z')] starting Athena Web Desktop compat from $ROOT"

exec /opt/homebrew/bin/python3 "$ROOT/scripts/athena_web_desktop_compat.py"
