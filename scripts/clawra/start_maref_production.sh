#!/bin/bash
# MAREF生产环境启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== MAREF生产环境启动 ==="
echo "时间: $(date)"
echo "目录: $SCRIPT_DIR"

# 加载配置文件
if [ -f "config/production_config.py" ]; then
    echo "✅ 生产配置文件存在"
else
    echo "⚠️  生产配置文件不存在，使用默认配置"
fi

# 检查环境
echo "检查环境..."
python3 check_production_environment.py
if [ $? -ne 0 ]; then
    echo "❌ 环境检查失败，请修复问题后重试"
    exit 1
fi

# 创建日志目录
mkdir -p logs

# 启动MAREF日报系统（示例）
echo "启动MAREF日报系统..."
python3 run_maref_daily_report.py --mode production --verbose >> logs/startup_$(date +%Y%m%d_%H%M%S).log 2>&1 &

# 启动监控器（示例）
echo "启动监控器..."
python3 -c "
import sys
sys.path.insert(0, '.')
from maref_monitor import MAREFMonitor
from maref_memory_integration import init_memory_manager, wrap_monitor_collect_metrics

# 初始化
memory_manager = init_memory_manager(performance_mode=True)
monitor = MAREFMonitor()
wrap_monitor_collect_metrics(monitor, memory_manager)

print('监控器启动成功，开始采集...')
import time
while True:
    metrics = monitor.collect_all_metrics()
    time.sleep(60)
" >> logs/monitor_$(date +%Y%m%d_%H%M%S).log 2>&1 &

echo "✅ MAREF生产环境启动完成"
echo "进程信息:"
ps aux | grep -E "run_maref_daily|maref_monitor" | grep -v grep || echo "无相关进程"

echo "日志目录: $SCRIPT_DIR/logs"
echo "使用 'tail -f logs/*.log' 查看实时日志"