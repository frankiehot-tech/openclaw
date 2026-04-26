#!/bin/bash

# 测试百炼PRO连接 - 诊断脚本

# 加载密钥
source ~/.config/secret-env/load-keychain-secrets.sh

echo "========== 环境变量检查 =========="
echo "DASHSCOPE_API_KEY: ${DASHSCOPE_API_KEY:0:10}..."
echo "DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY:0:10}..."
echo ""

echo "========== 测试百炼 API 直连 =========="
RESULT=$(curl -s -X POST "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions" \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3.6-plus","messages":[{"role":"user","content":"Hi"}],"max_tokens":5}')

echo "API 响应: $RESULT" | head -c 200
echo ""
echo ""

echo "========== 测试通过 Anthropic 兼容端点 =========="
ANTHROPIC_RESULT=$(curl -s -X POST "https://dashscope.aliyuncs.com/compatible-mode/v1/messages" \
  -H "x-api-key: $DASHSCOPE_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{
    "model": "qwen3.6-plus",
    "max_tokens": 10,
    "messages": [{"role": "user", "content": "Hi"}]
  }')

echo "Anthropic 兼容端点响应: $ANTHROPIC_RESULT" | head -c 300
echo ""