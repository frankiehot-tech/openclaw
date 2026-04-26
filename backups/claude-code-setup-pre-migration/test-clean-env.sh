#!/bin/bash

# 在干净环境中测试Qwen模型

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/load-local-secrets.sh"
require_any_secret DASHSCOPE_API_KEY ALIYUN_API_KEY || exit 1

ALIYUN_API_KEY="${ALIYUN_API_KEY:-$DASHSCOPE_API_KEY}"
DASHSCOPE_API_KEY="${DASHSCOPE_API_KEY:-$ALIYUN_API_KEY}"

echo "🧹 干净环境测试"
echo "====================="
echo ""

# 测试1: 使用 env -i 启动完全干净的环境
echo "🔧 测试1: 完全干净环境 (env -i)"
echo "----------------------------------------"
env -i \
    LLM_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1" \
    LLM_MODEL="qwen-max" \
    LLM_AUTH_TOKEN="$DASHSCOPE_API_KEY" \
    LLM_API_KEY="$DASHSCOPE_API_KEY" \
    AI_CODE_BARE=1 \
    AI_CODE_SKIP_KEYCHAIN=1 \
    /opt/homebrew/bin/claude echo "test" 2>&1 | head -10
echo ""

# 测试2: 使用 dashscope/qwen-max
echo "🔧 测试2: 使用 dashscope/qwen-max"
echo "----------------------------------------"
env -i \
    LLM_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1" \
    LLM_MODEL="dashscope/qwen-max" \
    LLM_AUTH_TOKEN="$DASHSCOPE_API_KEY" \
    LLM_API_KEY="$DASHSCOPE_API_KEY" \
    AI_CODE_BARE=1 \
    AI_CODE_SKIP_KEYCHAIN=1 \
    /opt/homebrew/bin/claude echo "test" 2>&1 | head -10
echo ""

# 测试3: 测试其他可能的模型名称
echo "🔧 测试3: 测试其他模型名称"
echo "----------------------------------------"
MODELS=("qwen-turbo" "qwen-plus" "qwen-coder" "qwen-flash")

for model in "${MODELS[@]}"; do
    echo "测试模型: $model"
    env -i \
        LLM_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1" \
        LLM_MODEL="$model" \
        LLM_AUTH_TOKEN="$DASHSCOPE_API_KEY" \
        LLM_API_KEY="$DASHSCOPE_API_KEY" \
        AI_CODE_BARE=1 \
        AI_CODE_SKIP_KEYCHAIN=1 \
        /opt/homebrew/bin/claude echo "test" 2>&1 | head -3
    echo ""
done

echo "✅ 干净环境测试完成"
