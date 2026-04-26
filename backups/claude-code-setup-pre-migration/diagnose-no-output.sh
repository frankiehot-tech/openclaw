#!/bin/bash

# AI Assistant 无输出问题诊断脚本

echo "=========================================="
echo "  AI Assistant 无输出问题诊断"
echo "=========================================="
echo ""

# 1. 检查适配器状态
echo "📊 1. 检查 DashScope 适配器状态..."
HEALTH=$(curl -s http://localhost:8080/health 2>/dev/null)
if [ -n "$HEALTH" ]; then
    echo "   ✅ 适配器运行正常"
    echo "   $HEALTH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'   模型: {d[\"model\"]}')" 2>/dev/null || true
else
    echo "   ❌ 适配器未运行"
    echo "   运行: ./claude-dashscope-adapter.sh start"
fi
echo ""

# 2. 检查 API 调用
echo "📊 2. 测试 API 调用..."
RESPONSE=$(curl -s http://localhost:8080/v1/messages -X POST \
    -H "Content-Type: application/json" \
    -H "x-api-key: sk-921103e3b7bb4d4bb1d97308c43c71fc" \
    -d '{"model":"qwen3.6-plus","messages":[{"role":"user","content":"回复OK"}],"max_tokens":10}' 2>/dev/null)
if echo "$RESPONSE" | grep -q '"text"'; then
    echo "   ✅ API 调用正常"
else
    echo "   ❌ API 调用失败"
    echo "   响应: $RESPONSE"
fi
echo ""

# 3. 检查输出样式配置
echo "📊 3. 检查输出样式配置..."
SETTINGS_FILE="/Users/frankie/.claude/settings.json"
if [ -f "$SETTINGS_FILE" ]; then
    OUTPUT_STYLE=$(python3 -c "import json; f=open('$SETTINGS_FILE'); d=json.load(f); print(d.get('outputStyle','default'))" 2>/dev/null)
    echo "   当前输出样式: $OUTPUT_STYLE"
    if [ "$OUTPUT_STYLE" = "Structured Code" ]; then
        echo "   ⚠️ 发现问题！'Structured Code' 输出样式可能导致无输出"
        echo "   正在修复..."
        python3 -c "
import json
with open('$SETTINGS_FILE', 'r') as f:
    d = json.load(f)
d['outputStyle'] = 'default'
with open('$SETTINGS_FILE', 'w') as f:
    json.dump(d, f, indent=2)
print('   ✅ 已修复为 default 输出样式')
"
    else
        echo "   ✅ 输出样式正常"
    fi
else
    echo "   ⚠️ 配置文件不存在"
fi
echo ""

# 4. 检查本地设置
echo "📊 4. 检查本地设置..."
LOCAL_SETTINGS="/Users/frankie/.claude/settings.local.json"
if [ -f "$LOCAL_SETTINGS" ]; then
    echo "   ✅ 本地设置存在"
    BASE_URL=$(python3 -c "import json; f=open('$LOCAL_SETTINGS'); d=json.load(f); print(d.get('env',{}).get('LLM_BASE_URL',''))" 2>/dev/null)
    MODEL=$(python3 -c "import json; f=open('$LOCAL_SETTINGS'); d=json.load(f); print(d.get('env',{}).get('LLM_MODEL',''))" 2>/dev/null)
    echo "   LLM_BASE_URL: $BASE_URL"
    echo "   LLM_MODEL: $MODEL"
else
    echo "   ⚠️ 本地设置不存在"
fi
echo ""

echo "=========================================="
echo "  诊断完成"
echo "=========================================="
echo ""
echo "💡 建议:"
echo "   1. 重新启动 AI Assistant (退出后重新运行 claude)"
echo "   2. 使用 ./claude-dual-model.sh 脚本启动"
echo "   3. 检查 ~/.claude/sessions/ 目录是否有权限问题"