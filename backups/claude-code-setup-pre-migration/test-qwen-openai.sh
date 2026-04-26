#!/bin/bash

# 测试Qwen模型通过OpenAI兼容API

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/load-local-secrets.sh"
require_any_secret DASHSCOPE_API_KEY ALIYUN_API_KEY || exit 1

API_KEY="${DASHSCOPE_API_KEY:-$ALIYUN_API_KEY}"
API_BASE="https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL="qwen3.6-plus"

echo "🧪 测试Qwen模型通过OpenAI兼容API"
echo "======================================"
echo "API端点: $API_BASE/chat/completions"
echo "模型: $MODEL"
echo ""

# 测试简单的对话
echo "📤 发送测试请求..."
RESPONSE=$(curl -s -X POST "$API_BASE/chat/completions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "'"$MODEL"'",
    "messages": [
      {"role": "user", "content": "你好，请用中文回答。测试一下连接是否正常。"}
    ],
    "max_tokens": 100,
    "temperature": 0.7
  }')

echo "📥 收到响应:"
echo "$RESPONSE" | jq '.choices[0].message.content' 2>/dev/null || echo "$RESPONSE"
echo ""

# 检查是否成功
if echo "$RESPONSE" | grep -q '"object":"chat.completion"'; then
  echo "✅ 测试成功！Qwen模型可以通过OpenAI兼容API正常工作。"
  echo ""
  echo "🔍 问题分析："
  echo "   DashScope提供了OpenAI兼容端点 (/chat/completions)"
  echo "   但AI Assistant需要LLM兼容端点 (/messages)"
  echo "   目前DashScope可能不提供LLM兼容模式"
else
  echo "❌ 测试失败"
  echo "响应详情:"
  echo "$RESPONSE"
fi
