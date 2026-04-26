#!/bin/bash

# Qwen模型名称诊断脚本
# 测试不同的模型名称变体

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/load-local-secrets.sh"
require_any_secret DASHSCOPE_API_KEY ALIYUN_API_KEY || exit 1

export ALIYUN_API_KEY="${ALIYUN_API_KEY:-$DASHSCOPE_API_KEY}"
export AI_MODE_BARE=1
export AI_SKIP_KEYCHAIN=1

echo "🔍 Qwen模型名称诊断"
echo "====================="
echo ""

# 定义要测试的模型名称变体
models=(
    "qwen3.6-max"
    "qwen-max"
    "qwen3-max"
    "qwen3-max-2026-01-23"
    "qwen3.6-max-latest"
    "qwen-max-latest"
)

API_BASE="https://dashscope.aliyuncs.com/compatible-mode/v1"

for model in "${models[@]}"; do
    echo "🧪 测试模型: $model"
    echo "----------------------------------------"

    # 使用env命令设置环境变量
    env \
        LLM_BASE_URL="$API_BASE" \
        LLM_MODEL="$model" \
        LLM_AUTH_TOKEN="$ALIYUN_API_KEY" \
        LLM_API_KEY="$ALIYUN_API_KEY" \
        AI_MODE_BARE=1 \
        AI_SKIP_KEYCHAIN=1 \
        /opt/homebrew/bin/claude --version 2>&1 | head -5

    echo ""
    sleep 1
done

echo "✅ 诊断完成"
echo ""
echo "📋 建议："
echo "1. 查看哪个模型名称没有报错"
echo "2. 使用有效的模型名称更新脚本"
echo "3. 检查阿里云控制台确认实际模型名称"
