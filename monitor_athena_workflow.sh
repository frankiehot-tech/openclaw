#!/bin/bash
# DEPRECATED: 使用 governance_cli.py health 命令代替
# Athena工作流无人值守监控脚本

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AUTO_FIX_SCRIPT="$SCRIPT_DIR/athena_web_desktop_auto_fix_workflow.py"
LOG_FILE="$SCRIPT_DIR/workflow_monitor.log"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 监控循环
monitor_workflow() {
    while true; do
        log "🔍 检查工作流状态..."
        
        # 运行自动修复脚本
        python3 "$AUTO_FIX_SCRIPT" >> "$LOG_FILE" 2>&1
        
        if [ $? -eq 0 ]; then
            log "✅ 工作流状态正常"
        else
            log "⚠️ 工作流存在问题，已尝试修复"
        fi
        
        # 等待5分钟再次检查
        sleep 300
    done
}

# 启动监控
log "🚀 启动Athena工作流无人值守监控"
monitor_workflow
