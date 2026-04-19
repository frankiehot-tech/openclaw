#!/bin/bash
# 启动2分钟间隔队列监控检查器

set -e

cd "$(dirname "$0")/.."

echo "🚀 启动2分钟间隔队列监控检查器..."
echo "工作目录: $(pwd)"
echo "时间: $(date)"

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3未安装"
    exit 1
fi

# 检查依赖
echo "📦 检查Python依赖..."
python3 -c "import requests, psutil, json" 2>/dev/null || {
    echo "⚠️ 缺少依赖，尝试安装..."
    pip3 install requests psutil || {
        echo "❌ 安装依赖失败"
        exit 1
    }
}

# 创建日志目录
mkdir -p logs

# 检查是否已在运行
MONITOR_PID_FILE="logs/two_minute_monitor.pid"
if [ -f "$MONITOR_PID_FILE" ]; then
    OLD_PID=$(cat "$MONITOR_PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "⚠️ 监控器已在运行 (PID: $OLD_PID)"
        echo "   停止旧进程..."
        kill "$OLD_PID" 2>/dev/null
        sleep 2
    fi
fi

# 启动监控器（后台运行）
echo "▶️ 启动新的监控器进程..."
nohup python3 scripts/two_minute_queue_monitor.py > logs/two_minute_monitor.out 2>&1 &

# 获取进程ID
MONITOR_PID=$!
echo $MONITOR_PID > "$MONITOR_PID_FILE"

echo "✅ 监控器已启动 (PID: $MONITOR_PID)"
echo "📝 输出日志: logs/two_minute_monitor.out"
echo "📊 检查日志: logs/two_minute_checks.jsonl"
echo "⚠️ 问题日志: logs/queue_problems.jsonl"
echo "📋 总结报告: logs/queue_summary_report.md"

# 等待几秒后检查状态
sleep 3
if kill -0 "$MONITOR_PID" 2>/dev/null; then
    echo "✅ 监控器运行正常"
    echo ""
    echo "💡 监控器将:"
    echo "   • 每2分钟检查所有队列状态"
    echo "   • 自动拉起pending任务"
    echo "   • 记录执行问题和错误"
    echo "   • 当所有队列完成后生成总结报告"
    echo ""
    echo "🛑 停止监控: kill $(cat $MONITOR_PID_FILE) && rm $MONITOR_PID_FILE"
else
    echo "❌ 监控器启动失败，请检查日志"
    rm -f "$MONITOR_PID_FILE"
    exit 1
fi