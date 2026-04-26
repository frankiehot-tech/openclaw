#!/bin/bash

# 临时测试 DeepSeek API 配置

# 设置 DeepSeek API 密钥
export DEEPSEEK_API_KEY="sk-a94b26e9a0a340ba81788a067872e79e"

# Claude Code 函数
function claude() {
  export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
  export ANTHROPIC_MODEL="deepseek-chat"
  export ANTHROPIC_API_KEY="$DEEPSEEK_API_KEY"
  export ANTHROPIC_AUTH_TOKEN="$DEEPSEEK_API_KEY"
  echo "🚀 [DeepSeek] Chat"
  /opt/homebrew/bin/claude "$@"
}

# 测试 Claude Code
echo "=== 测试 DeepSeek API 配置 ==="
echo ""
echo "测试 1: 版本信息"
claude --version
echo ""
echo "测试 2: 发送测试消息"
claude -p "Hello from DeepSeek test"
echo ""
echo "=== 测试完成 ==="
echo ""
echo "如果测试成功，将 deepseek-config.sh 中的内容添加到 ~/.zshrc 文件中"
echo "然后执行: source ~/.zshrc"
