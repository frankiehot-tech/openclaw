#!/bin/bash
# 每周执行一次24小时稳定性监控

# 参数配置
MONITOR_SCRIPT="monitor_long_term_stability.py"
HOURS=24
INTERVAL=300  # 5分钟
LOG_DIR="logs/weekly_monitor"

# 创建日志目录
mkdir -p "$LOG_DIR"

# 生成时间戳
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/weekly_monitor_${TIMESTAMP}.log"
REPORT_FILE="$LOG_DIR/weekly_report_${TIMESTAMP}.json"

# 执行监控
echo "=== 开始每周稳定性监控 ===" | tee -a "$LOG_FILE"
echo "时间: $(date)" | tee -a "$LOG_FILE"
echo "时长: $HOURS 小时" | tee -a "$LOG_FILE"
echo "间隔: $INTERVAL 秒" | tee -a "$LOG_FILE"

# 启动监控
python3 "$MONITOR_SCRIPT" --hours "$HOURS" --interval "$INTERVAL" >> "$LOG_FILE" 2>&1

# 监控结束后分析数据
if [ $? -eq 0 ]; then
    echo "监控完成，开始分析数据..." | tee -a "$LOG_FILE"

    # 查找最新的监控完成文件
    LATEST_COMPLETE=$(ls -t logs/long_term_monitor_complete_*.json | head -1)

    if [ -f "$LATEST_COMPLETE" ]; then
        # 使用分析脚本
        python3 analyze_long_term_monitor.py --input "$LATEST_COMPLETE" --output "$REPORT_FILE"
        echo "分析报告已生成: $REPORT_FILE" | tee -a "$LOG_FILE"
    else
        echo "警告: 未找到监控完成文件" | tee -a "$LOG_FILE"
    fi
else
    echo "监控执行失败，请检查日志: $LOG_FILE" | tee -a "$LOG_FILE"
    exit 1
fi

echo "=== 每周稳定性监控完成 ===" | tee -a "$LOG_FILE"