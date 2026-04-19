#!/bin/bash
# MAREF性能监控cron包装脚本
# 设置正确的环境变量供cron使用

set -e

# 设置环境变量
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export PYTHONPATH="/Volumes/1TB-M2/openclaw/scripts/clawra:/Volumes/1TB-M2/openclaw/scripts/clawra/external/ROMA:$PYTHONPATH"

# 切换到脚本目录
cd "/Volumes/1TB-M2/openclaw/scripts/clawra"

# 创建日志目录
mkdir -p logs/performance_monitor

# 生成时间戳
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="logs/performance_monitor/performance_${TIMESTAMP}.log"

# 记录开始时间
echo "=== MAREF性能监控开始 $(date) ===" > "$LOG_FILE"
echo "日志文件: $LOG_FILE" >> "$LOG_FILE"

# 运行性能监控
echo "运行性能指标收集..." >> "$LOG_FILE"
python3 collect_performance_metrics.py >> "$LOG_FILE" 2>&1

# 记录结束状态
EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ MAREF性能监控成功 $(date)" >> "$LOG_FILE"
else
    echo "❌ MAREF性能监控失败，退出码: $EXIT_CODE $(date)" >> "$LOG_FILE"
    echo "=== 错误详情 ===" >> "$LOG_FILE"
    tail -20 "$LOG_FILE" >> "$LOG_FILE"
fi

# 记录执行时间
END_TIME=$(date +%s)
START_TIME=$(date -r "$LOG_FILE" +%s 2>/dev/null || date +%s)
DURATION=$((END_TIME - START_TIME))
echo "执行时间: ${DURATION}秒" >> "$LOG_FILE"

exit $EXIT_CODE
