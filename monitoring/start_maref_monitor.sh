#!/bin/bash
# MAREF调度器监控启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="/Volumes/1TB-M2/openclaw"
STATE_FILE="${1:-/tmp/hetu_luoshu_state.json}"
LOG_DIR="${SCRIPT_DIR}/logs"
INTERVAL="${2:-60}"

echo "🚀 启动MAREF调度器监控系统"
echo "========================================"
echo "状态文件: ${STATE_FILE}"
echo "日志目录: ${LOG_DIR}"
echo "监控间隔: ${INTERVAL} 秒"
echo ""

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3未安装"
    exit 1
fi

# 检查状态文件目录是否存在
STATE_DIR=$(dirname "${STATE_FILE}")
if [ ! -d "${STATE_DIR}" ]; then
    echo "📁 创建状态文件目录: ${STATE_DIR}"
    mkdir -p "${STATE_DIR}"
fi

# 创建日志目录
mkdir -p "${LOG_DIR}"

# 检查监控脚本是否存在
MONITOR_SCRIPT="${SCRIPT_DIR}/maref_scheduler_monitor.py"
if [ ! -f "${MONITOR_SCRIPT}" ]; then
    echo "❌ 监控脚本不存在: ${MONITOR_SCRIPT}"
    exit 1
fi

echo "🔍 运行环境检查..."
python3 -c "
import sys
sys.path.insert(0, '${PROJECT_ROOT}/mini-agent')
try:
    from agent.core.maref_quality.hetu_luoshu_scheduler import HetuLuoshuScheduler
    print('✅ 调度器模块导入成功')
except Exception as e:
    print(f'❌ 调度器模块导入失败: {e}')
    sys.exit(1)
"

echo ""
echo "📊 启动监控循环..."
cd "${SCRIPT_DIR}"
python3 maref_scheduler_monitor.py \
    --state-file "${STATE_FILE}" \
    --log-dir "${LOG_DIR}" \
    --monitor \
    --interval "${INTERVAL}"