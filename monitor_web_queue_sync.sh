#!/bin/bash
# Web界面与队列状态同步监控脚本

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SYNC_SCRIPT="$SCRIPT_DIR/fix_web_queue_mismatch.py"
LOG_FILE="$SCRIPT_DIR/web_queue_sync.log"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 同步检查循环
monitor_sync() {
    while true; do
        log "🔍 检查Web界面与队列状态同步..."
        
        # 运行同步检查脚本
        python3 "$SYNC_SCRIPT" --check-only >> "$LOG_FILE" 2>&1
        
        if [ $? -eq 0 ]; then
            log "✅ Web界面与队列状态同步正常"
        else:
            log "⚠️ Web界面与队列状态同步异常，尝试修复"
            
            # 运行修复脚本
            python3 "$SYNC_SCRIPT" --fix-only >> "$LOG_FILE" 2>&1
            
            if [ $? -eq 0 ]; then
                log "✅ Web界面与队列状态同步修复成功"
            else:
                log "❌ Web界面与队列状态同步修复失败"
            fi
        fi
        
        # 等待5分钟再次检查
        sleep 300
    done
}

# 启动监控
log "🔄 启动Web界面与队列状态同步监控"
monitor_sync
