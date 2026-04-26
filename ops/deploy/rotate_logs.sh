#!/bin/bash
# Manual log rotation for OpenClaw
# Run as cron job if newsyslog is not configured:
#   */30 * * * * /usr/bin/flock -n /tmp/openclaw-rotate.lock /Volumes/1TB-M2/openclaw/ops/deploy/rotate_logs.sh
set -euo pipefail

LOG_DIR="/Volumes/1TB-M2/openclaw/logs"
MAX_SIZE_MB=100
RETENTION=5

for logfile in "$LOG_DIR"/athena_ai_plan_build_worker.log "$LOG_DIR"/athena_ai_plan_runner.log; do
    [ -f "$logfile" ] || continue

    size_mb=$(( $(stat -f%z "$logfile" 2>/dev/null) / 1048576 ))
    if [ "$size_mb" -ge "$MAX_SIZE_MB" ]; then
        mv "$logfile" "$logfile.$(date +%Y%m%d-%H%M%S)"
        touch "$logfile"
        gzip "$logfile."*".$(date +%Y%m)*" 2>/dev/null || true
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Rotated $logfile ($size_mb MB)" >> "$LOG_DIR/rotation.log"
    fi

    # cleanup old rotations (keep RETENTION most recent)
    ls -t "$logfile".* 2>/dev/null | tail -n +$((RETENTION + 1)) | while read old; do
        rm -f "$old"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Removed old rotation: $old" >> "$LOG_DIR/rotation.log"
    done
done
