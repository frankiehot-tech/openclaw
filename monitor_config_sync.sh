#!/bin/bash
# Athena Web配置与队列状态同步监控脚本

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SYNC_SCRIPT="$SCRIPT_DIR/fix_web_config_sync.py"
LOG_FILE="$SCRIPT_DIR/config_sync_monitor.log"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 检查配置同步状态
check_sync() {
    log "🔍 检查配置同步状态..."
    
    # 运行同步检查脚本
    python3 "$SYNC_SCRIPT" --check-only >> "$LOG_FILE" 2>&1
    
    if [ $? -eq 0 ]; then
        log "✅ 配置同步正常"
        return 0
    else
        log "⚠️ 配置同步异常，尝试修复"
        
        # 运行修复脚本
        python3 "$SYNC_SCRIPT" --fix-only >> "$LOG_FILE" 2>&1
        
        if [ $? -eq 0 ]; then
            log "✅ 配置同步修复成功"
        else
            log "❌ 配置同步修复失败"
        fi
        
        return 1
    fi
}

# 监控循环
monitor_sync() {
    while true; do
        check_sync
        
        # 等待10分钟再次检查
        sleep 600
    done
}

# 启动监控
log "🚀 启动Athena Web配置同步监控"
monitor_sync
