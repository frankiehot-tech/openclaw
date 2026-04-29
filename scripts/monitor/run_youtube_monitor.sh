#!/bin/bash
# YouTube AI 博主动态日报 cron 包装脚本
set -e

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export PYTHONPATH="/Volumes/1TB-M2/openclaw:$PYTHONPATH"

cd "/Volumes/1TB-M2/openclaw"

LOG_DIR="logs/youtube_monitor"
mkdir -p "$LOG_DIR"

echo "=== YouTube 日报开始 $(date) ===" >> "$LOG_DIR/cron.log"

python3 -m scripts.youtube_monitor report >> "$LOG_DIR/cron.log" 2>&1

EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ YouTube 日报完成 $(date)" >> "$LOG_DIR/cron.log"
else
    echo "❌ YouTube 日报失败，退出码: $EXIT_CODE $(date)" >> "$LOG_DIR/cron.log"
fi

exit $EXIT_CODE
