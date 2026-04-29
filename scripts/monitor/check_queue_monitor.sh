#!/bin/bash
# 队列监控守护进程检查脚本
# 检查队列监控守护进程是否运行，如果未运行则自动重启

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

LOG_DIR="$PROJECT_ROOT/logs"
PID_FILE="$LOG_DIR/queue_monitor.pid"
CONFIG_FILE="scripts/queue_monitor_config.yaml"
START_SCRIPT="scripts/start_queue_monitor.sh"
LOG_FILE="$LOG_DIR/queue_monitor_watchdog.log"

# 创建日志目录
mkdir -p "$LOG_DIR"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# 检查守护进程状态
check_monitor() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE" 2>/dev/null || echo "")
        if [ -n "$PID" ] && ps -p "$PID" > /dev/null 2>&1; then
            log "✅ 队列监控守护进程正在运行 (PID: $PID)"
            return 0
        else
            log "⚠️ PID文件存在但进程未运行 (PID: $PID)"
            rm -f "$PID_FILE"
            return 1
        fi
    else
        # 检查是否有进程通过其他方式运行
        MONITOR_PIDS=$(pgrep -f "queue_monitor.py.*daemon" 2>/dev/null || echo "")
        if [ -n "$MONITOR_PIDS" ]; then
            log "✅ 队列监控守护进程正在运行 (PIDs: $MONITOR_PIDS)"
            # 创建PID文件以便后续管理
            echo "$MONITOR_PIDS" | awk '{print $1}' > "$PID_FILE"
            return 0
        else
            log "❌ 队列监控守护进程未运行"
            return 1
        fi
    fi
}

# 启动守护进程
start_monitor() {
    log "🚀 启动队列监控守护进程..."

    # 检查配置文件是否存在
    if [ ! -f "$CONFIG_FILE" ]; then
        log "❌ 配置文件不存在: $CONFIG_FILE"
        return 1
    fi

    # 使用启动脚本启动
    if "$START_SCRIPT" start; then
        log "✅ 队列监控守护进程启动成功"
        return 0
    else
        log "❌ 队列监控守护进程启动失败"
        return 1
    fi
}

# 主逻辑
main() {
    log "🔍 检查队列监控守护进程状态..."

    if check_monitor; then
        log "✅ 队列监控守护进程状态正常"
    else
        log "🔄 尝试重启队列监控守护进程..."
        if start_monitor; then
            log "✅ 队列监控守护进程重启成功"
        else
            log "❌ 队列监控守护进程重启失败，请手动检查"
        fi
    fi

    # 记录日志大小
    if [ -f "$LOG_FILE" ]; then
        LOG_SIZE=$(du -h "$LOG_FILE" 2>/dev/null | cut -f1 || echo "N/A")
        log "📄 检查脚本日志大小: $LOG_SIZE"
    fi

    log "✅ 检查完成"
}

# 执行主函数
main "$@"