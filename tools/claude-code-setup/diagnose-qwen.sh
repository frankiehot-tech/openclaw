#!/bin/bash

# 诊断Qwen模型连接问题

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/load-local-secrets.sh"
require_any_secret DASHSCOPE_API_KEY ALIYUN_API_KEY || exit 1

API_KEY="${DASHSCOPE_API_KEY:-$ALIYUN_API_KEY}"
API_BASE="https://dashscope.aliyuncs.com/compatible-mode/v1"

echo "🔍 Qwen模型连接诊断"
echo "====================="
echo ""

# 1. 测试直接API调用（获取模型列表）
echo "1. 测试直接调用DashScope API获取模型列表"
curl -s -X GET "https://dashscope.aliyuncs.com/api/v1/models" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" | jq '.data[0:5]' 2>&1 || echo "curl命令失败"
echo ""

# 2. 测试LLM格式的消息请求到兼容端点
echo "2. 测试LLM格式请求到兼容端点"
cat > /tmp/test_message.json << 'EOF'
{
  "model": "qwen3.6-plus",
  "messages": [
    {"role": "user", "content": "test"}
  ],
  "max_tokens": 10
}
EOF

curl -s -X POST "$API_BASE/messages" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d @/tmp/test_message.json | head -c 500
echo ""
echo ""

# 3. 测试不同模型名称格式
echo "3. 测试不同模型名称格式"
MODELS=("qwen3.6-plus" "dashscope/qwen3.6-plus" "qwen-max" "dashscope/qwen-max")

for model in "${MODELS[@]}"; do
  echo "测试模型: $model"
  env \
    LLM_BASE_URL="$API_BASE" \
    LLM_MODEL="$model" \
    LLM_AUTH_TOKEN="$API_KEY" \
    AI_CODE_BARE=1 \
    /opt/homebrew/bin/claude echo "test" 2>&1 | grep -E "issue|error|Error|test" | head -2
  echo ""
done

# 4. 检查IP地址
echo "4. 当前公网IP地址"
curl -s https://api.ipify.org 2>/dev/null || echo "无法获取IP"
echo ""

echo "✅ 诊断完成"
