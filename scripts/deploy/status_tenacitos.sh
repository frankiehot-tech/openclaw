#!/usr/bin/env zsh
set -euo pipefail

LABEL="com.athena.tenacitos"
PORT=3000
SCREEN_NAME="tenacitos"

LAUNCH_STATUS="$(launchctl list | awk '$3 == "'"$LABEL"'" { print $1":"$2":"$3 }')"
LISTENER="$( (lsof -n -P -iTCP:${PORT} -sTCP:LISTEN 2>/dev/null || true) | awk 'NR==2 {print $1" "$2}' )"
SCREEN_STATUS="$( (/usr/bin/screen -ls 2>/dev/null || true) | awk '$1 ~ /[0-9]+\.'"$SCREEN_NAME"'$/ { print $1 }' | paste -sd, - )"

if [[ -n "${LAUNCH_STATUS:-}" ]]; then
  echo "launchd=${LAUNCH_STATUS}"
else
  echo "launchd=missing"
fi

if [[ -n "${LISTENER:-}" ]]; then
  echo "listener=${LISTENER}"
else
  echo "listener=none"
fi

if [[ -n "${SCREEN_STATUS:-}" ]]; then
  echo "screen=${SCREEN_STATUS}"
else
  echo "screen=none"
fi
