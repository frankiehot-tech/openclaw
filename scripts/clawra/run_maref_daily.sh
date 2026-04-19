#!/bin/bash
# MAREF日报生成包装脚本
# 用于cron任务或其他调度系统

set -e

# 进入脚本目录
cd "$(dirname "$0")"

# 设置环境变量
export PYTHONPATH="$PYTHONPATH:$(pwd)"
export MAREF_MODE="standalone"  # 默认为独立模式，可改为integration连接实际系统

# 日志文件
LOG_DIR="logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/maref_cron_$(date +%Y%m%d).log"

# 运行Python脚本
echo "=== MAREF日报生成任务开始 $(date) ===" >> "$LOG_FILE"
python3 run_maref_daily_report.py "$@" 2>&1 | tee -a "$LOG_FILE"

# 检查退出码
EXIT_CODE=${PIPESTATUS[0]}
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ 任务成功完成 $(date)" >> "$LOG_FILE"
else
    echo "❌ 任务失败，退出码: $EXIT_CODE $(date)" >> "$LOG_FILE"
fi

exit $EXIT_CODE