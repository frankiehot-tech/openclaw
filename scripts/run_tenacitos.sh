#!/usr/bin/env zsh
set -euo pipefail

ROOT="/Volumes/1TB-M2/openclaw"
APP_DIR="$ROOT/vendor/tenacitOS"
LOG_FILE="$APP_DIR/logs/tenacitOS.runtime.log"

mkdir -p "$APP_DIR/logs"
cd "$APP_DIR"

export HOME="/Users/frankie"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export NODE_ENV="production"
export PORT="3000"

exec >>"$LOG_FILE" 2>&1
echo "[$(/bin/date '+%Y-%m-%d %H:%M:%S %z')] starting TenacitOS from $APP_DIR"

exec /Volumes/1TB-M2/openclaw/vendor/tenacitOS/node_modules/.bin/next start -H 0.0.0.0
