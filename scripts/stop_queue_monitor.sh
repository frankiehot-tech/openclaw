#!/bin/bash
# Athena队列监控系统停止脚本
# 优先级P0修复 - 短期监控部署

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

LOG_DIR="$PROJECT_ROOT/logs"
PID_FILE="$LOG_DIR/queue_monitor.pid"
LOG_FILE="$LOG_DIR/queue_monitor_daemon.log"

# 检查日志目录
if [ ! -d "$LOG_DIR" ]; then
    echo "ℹ️ 日志目录不存在，监控系统可能未运行"
    exit 0
fi

# 检查PID文件是否存在
if [ ! -f "$PID_FILE" ]; then
    echo "⚠️ 未找到队列监控系统PID文件: $PID_FILE"
    echo "   监控系统可能未运行"

    # 尝试查找相关进程
    echo "🔍 尝试查找监控进程..."
    MONITOR_PIDS=$(pgrep -f "queue_monitor.py.*daemon" 2>/dev/null || echo "")

    if [ -n "$MONITOR_PIDS" ]; then
        echo "   找到监控进程 (PIDs: $MONITOR_PIDS)"
        echo ""
        echo "🛑 停止监控进程..."
        pkill -f "queue_monitor.py.*daemon"
        sleep 2

        # 确认进程已停止
        if pgrep -f "queue_monitor.py.*daemon" > /dev/null; then
            echo "❌ 无法停止监控进程，尝试强制停止..."
            pkill -9 -f "queue_monitor.py.*daemon"
            sleep 1
        fi

        echo "✅ 队列监控系统已停止"
    else
        echo "✅ 队列监控系统未在运行"
    fi

    exit 0
fi

# 读取PID
PID=$(cat "$PID_FILE" 2>/dev/null || echo "")

# 检查进程是否存在
if [ -n "$PID" ] && ps -p "$PID" > /dev/null 2>&1; then
    echo "🛑 停止队列监控系统 (PID: $PID)..."

    # 发送终止信号
    kill "$PID" 2>/dev/null || true

    # 等待进程结束（最多10秒）
    echo -n "等待进程停止"
    for i in {1..10}; do
        if ps -p "$PID" > /dev/null 2>&1; then
            sleep 1
            echo -n "."
        else
            break
        fi
    done

    echo ""

    # 检查是否已停止
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "⚠️ 进程未正常终止，强制停止..."
        kill -9 "$PID" 2>/dev/null || true
        sleep 1
    fi

    # 清理PID文件
    rm -f "$PID_FILE"

    echo "✅ 队列监控系统已停止"
else
    echo "⚠️ PID $PID 对应的进程不存在"
    echo "   清理PID文件..."
    rm -f "$PID_FILE"
    echo "✅ 清理完成"
fi

# 显示日志最后几行
echo ""
echo "📋 最近日志:"
if [ -f "$LOG_FILE" ]; then
    echo "日志文件: $LOG_FILE"
    echo "文件大小: $(du -h "$LOG_FILE" 2>/dev/null | cut -f1 || echo "N/A")"
    echo "最后几行:"
    tail -10 "$LOG_FILE" 2>/dev/null | sed 's/^/  /' || echo "  无法读取日志"
else
    echo "   日志文件不存在"
fi

echo ""
echo "💡 如需重新启动，请运行:"
echo "   ./scripts/start_queue_monitor.sh [配置文件]"