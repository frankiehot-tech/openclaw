#!/bin/bash

# 直接测试 DeepSeek API 连接
echo "=== 直接测试 DeepSeek API ==="
echo ""

# 设置环境变量
export DEEPSEEK_API_KEY="sk-a94b26e9a0a340ba81788a067872e79e"
export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
export ANTHROPIC_MODEL="deepseek-chat"
export ANTHROPIC_API_KEY="$DEEPSEEK_API_KEY"
export ANTHROPIC_AUTH_TOKEN="$DEEPSEEK_API_KEY"

echo "环境变量设置完成:"
echo "ANTHROPIC_BASE_URL: $ANTHROPIC_BASE_URL"
echo "ANTHROPIC_MODEL: $ANTHROPIC_MODEL"
echo "ANTHROPIC_API_KEY: $(echo $ANTHROPIC_API_KEY | head -c 10)..."
echo ""

# 测试 API 调用
echo "测试 API 调用:"
echo "发送测试消息..."
response=$(/opt/homebrew/bin/claude -p "Direct test message")
echo "响应:"
echo "$response"
echo ""

# 测试版本
echo "测试 Claude Code 版本:"
/opt/homebrew/bin/claude --version
echo ""

echo "=== 测试完成 ==="
