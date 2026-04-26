#!/bin/bash
# 启动基因管理队列执行脚本

echo "============================================================"
echo "🧬 启动 Athena/Open Human 基因管理 Agent 队列执行"
echo "============================================================"

# 设置队列状态
QUEUE_STATE_FILE="/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_gene_management_20260405.json"
QUEUE_FILE="/Volumes/1TB-M2/openclaw/Documents/Athena 知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/OpenHuman-AIPlan-基因管理队列.queue.json"

echo "📁 队列状态文件：$QUEUE_STATE_FILE"
echo "📁 队列清单文件：$QUEUE_FILE"

# 检查文件是否存在
if [ ! -f "$QUEUE_STATE_FILE" ]; then
    echo "❌ 队列状态文件不存在"
    exit 1
fi

if [ ! -f "$QUEUE_FILE" ]; then
    echo "❌ 队列清单文件不存在"
    exit 1
fi

# 检查 runner 是否运行
if ps aux | grep -q "athena_ai_plan_runner.py" | grep -v grep; then
    echo "✅ athena_ai_plan_runner 正在运行 (PID: $(pgrep -f athena_ai_plan_runner.py))"
else
    echo "⚠️  athena_ai_plan_runner 未运行，需要手动启动"
    echo "启动命令：python3 /Volumes/1TB-M2/openclaw/scripts/athena_ai_plan_runner.py"
fi

# 显示队列状态
echo ""
echo "📊 当前队列状态:"
python3 -c "
import json
with open('$QUEUE_STATE_FILE', 'r', encoding='utf-8') as f:
    state = json.load(f)
    print(f\"  队列 ID: {state['queue_id']}\")
    print(f\"  队列名称：{state['name']}\")
    print(f\"  队列状态：{state['queue_status']}\")
    print(f\"  当前任务：{state['current_item_id']}\")
    print(f\"  任务计数：pending={state['counts']['pending']}, running={state['counts']['running']}, completed={state['counts']['completed']}\")
"

echo ""
echo "🎯 任务执行顺序:"
python3 -c "
import json
with open('$QUEUE_FILE', 'r', encoding='utf-8') as f:
    queue = json.load(f)
    for i, item in enumerate(queue['items'], 1):
        phase = item['metadata'].get('phase', 'Unknown')
        priority = item['metadata'].get('priority', 'Unknown')
        print(f\"  {i}. {item['title']} ({phase}阶段，优先级：{priority})\")
"

echo ""
echo "🔗 监控地址:"
echo "   http://127.0.0.1:8080 - 查看队列状态和执行进度"

echo ""
echo "🚀 基因管理队列已准备就绪，等待执行器处理..."
echo "============================================================"
