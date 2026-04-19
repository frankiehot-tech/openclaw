#!/bin/bash
# 全面队列保护监控脚本

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROTECT_SCRIPT="$SCRIPT_DIR/protect_all_queues.py"
LOG_FILE="$SCRIPT_DIR/all_queues_protection.log"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 保护监控循环
monitor_protection() {
    while true; do
        log "🔍 检查所有队列状态保护..."
        
        # 运行保护脚本
        python3 "$PROTECT_SCRIPT" >> "$LOG_FILE" 2>&1
        
        if [ $? -eq 0 ]; then
            log "✅ 所有队列状态保护正常"
        else:
            log "⚠️ 队列状态保护异常"
        fi
        
        # 等待2分钟再次检查
        sleep 120
    done
}

# 启动监控
log "🛡️ 启动全面队列状态保护监控"
monitor_protection
