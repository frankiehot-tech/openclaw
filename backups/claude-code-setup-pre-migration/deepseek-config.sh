#!/bin/bash

# DeepSeek API 配置脚本
# 将此文件内容添加到 ~/.zshrc 文件中

# DeepSeek API 密钥
export DEEPSEEK_API_KEY="sk-a94b26e9a0a340ba81788a067872e79e"

# Claude Code 主入口 - 使用 DeepSeek
function claude() {
  export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
  export ANTHROPIC_MODEL="deepseek-chat"
  export ANTHROPIC_API_KEY="$DEEPSEEK_API_KEY"
  export ANTHROPIC_AUTH_TOKEN="$DEEPSEEK_API_KEY"
  echo "🚀 [DeepSeek] Chat"
  /opt/homebrew/bin/claude "$@"
}

# Claude Code - DeepSeek Reasoner（推理模型）
function claude-reasoner() {
  export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
  export ANTHROPIC_MODEL="deepseek-reasoner"
  export ANTHROPIC_API_KEY="$DEEPSEEK_API_KEY"
  export ANTHROPIC_AUTH_TOKEN="$DEEPSEEK_API_KEY"
  echo "🧠 [DeepSeek] Reasoner"
  /opt/homebrew/bin/claude "$@"
}

# Claude Code - DeepSeek Coder（代码专用）
function claude-coder() {
  export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
  export ANTHROPIC_MODEL="deepseek-coder"
  export ANTHROPIC_API_KEY="$DEEPSEEK_API_KEY"
  export ANTHROPIC_AUTH_TOKEN="$DEEPSEEK_API_KEY"
  echo "💻 [DeepSeek] Coder"
  /opt/homebrew/bin/claude "$@"
}
