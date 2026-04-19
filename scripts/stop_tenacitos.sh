#!/usr/bin/env zsh
set -euo pipefail

ROOT="/Volumes/1TB-M2/openclaw"
SCREEN_NAME="tenacitos"
PORT=3000

for session_id in $( (/usr/bin/screen -ls 2>/dev/null || true) | awk '$1 ~ /[0-9]+\.'"$SCREEN_NAME"'$/ { print $1 }'); do
  /usr/bin/screen -S "$session_id" -X quit >/dev/null 2>&1 || true
done

LISTENER_PID="$( (lsof -n -P -iTCP:${PORT} -sTCP:LISTEN 2>/dev/null || true) | awk 'NR==2 { print $2 }' )"
if [[ -n "${LISTENER_PID:-}" ]]; then
  kill -TERM "$LISTENER_PID" 2>/dev/null || true
fi

pkill -f '/Volumes/1TB-M2/openclaw/vendor/tenacitOS/node_modules/.bin/next start -H 0.0.0.0' || true
pkill -f '/Volumes/1TB-M2/openclaw/vendor/tenacitOS/.*/next-server' || true

echo "TenacitOS stopped"
