#!/bin/bash
# 全域压力测试实时监控脚本

echo "🔍 全域压力测试实时监控启动"
echo "================================"

while true; do
    clear
    echo "🔄 压力测试实时状态 ($(date))"
    echo "================================"
    
    # 检查压力测试进程
    if pgrep -f "openhuman_24h_stress_runner" > /dev/null; then
        echo "✅ 压力测试运行器: 运行中"
    else
        echo "❌ 压力测试运行器: 停止"
    fi
    
    # 检查队列运行器
    if pgrep -f "athena_ai_plan_runner" > /dev/null; then
        echo "✅ 队列运行器: 运行中"
    else
        echo "❌ 队列运行器: 停止"
    fi
    
    # 检查Claude Code Router
    curl -s http://127.0.0.1:3000/health > /dev/null
    if [ $? -eq 0 ]; then
        echo "✅ Claude Code Router: 健康"
    else
        echo "❌ Claude Code Router: 异常"
    fi
    
    # 系统资源监控
    echo ""
    echo "📊 系统资源使用情况:"
    python3 -c "
import psutil
import datetime

print(f'  CPU使用率: {psutil.cpu_percent(interval=1)}%')
print(f'  内存使用率: {psutil.virtual_memory().percent}%')
print(f'  磁盘使用率: {psutil.disk_usage(\"/\").percent}%')
print(f'  进程数量: {len(psutil.pids())}')
print(f'  当前时间: {datetime.datetime.now().strftime(\"%H:%M:%S\")}')
"
    
    echo ""
    echo "⏰ 下次更新: 30秒后..."
    sleep 30
done