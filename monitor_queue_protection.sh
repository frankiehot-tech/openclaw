#!/bin/bash
# DEPRECATED: 使用 governance_cli.py queue protect 命令代替
# 队列状态保护监控脚本

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROTECT_SCRIPT="$SCRIPT_DIR/protect_queue_state.py"
LOG_FILE="$SCRIPT_DIR/queue_protection.log"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 保护监控循环
monitor_protection() {
    while true; do
        log "🔍 检查队列状态保护..."
        
        # 运行保护脚本
        python3 "$PROTECT_SCRIPT" >> "$LOG_FILE" 2>&1
        
        if [ $? -eq 0 ]; then
            log "✅ 队列状态保护正常"
        else:
            log "⚠️ 队列状态保护异常"
        fi
        
        # 等待3分钟再次检查
        sleep 180
    done
}

# 启动监控
log "🛡️ 启动队列状态保护监控"
monitor_protection
