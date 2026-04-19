#!/bin/bash
# MAREF生产环境停止脚本

echo "=== MAREF生产环境停止 ==="
echo "时间: $(date)"

# 查找相关进程
PIDS=$(ps aux | grep -E "run_maref_daily|maref_monitor" | grep -v grep | awk '{print $2}')

if [ -z "$PIDS" ]; then
    echo "✅ 没有找到运行中的MAREF进程"
    exit 0
fi

echo "找到进程: $PIDS"

# 发送停止信号
for PID in $PIDS; do
    echo "停止进程 $PID..."
    kill -TERM $PID 2>/dev/null || kill -KILL $PID 2>/dev/null
done

# 等待进程停止
sleep 2

# 确认进程已停止
REMAINING=$(ps aux | grep -E "run_maref_daily|maref_monitor" | grep -v grep | wc -l)
if [ "$REMAINING" -eq 0 ]; then
    echo "✅ 所有MAREF进程已停止"
else
    echo "⚠️  仍有 $REMAINING 个进程在运行，强制停止..."
    ps aux | grep -E "run_maref_daily|maref_monitor" | grep -v grep | awk '{print $2}' | xargs kill -KILL 2>/dev/null
fi

echo "停止完成"