#!/bin/bash

# 测试模型连接性脚本
# 测试实际的模型交互，而不是仅版本检查

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/load-local-secrets.sh"
require_any_secret DASHSCOPE_API_KEY ALIYUN_API_KEY || exit 1

export ALIYUN_API_KEY="${ALIYUN_API_KEY:-$DASHSCOPE_API_KEY}"
export AI_CODE_BARE=1
export AI_CODE_SKIP_KEYCHAIN=1

echo "🔍 模型连接性测试"
echo "====================="
echo ""

# 定义要测试的模型名称变体（包括带前缀和不带前缀的）
models=(
    "qwen-max"
    "dashscope/qwen-max"
    "qwen3.6-max"
    "dashscope/qwen3-max"
    "dashscope/qwen3-max-2026-01-23"
    "qwen3.6-plus"
    "dashscope/qwen-plus"
)

API_BASE="https://dashscope.aliyuncs.com/compatible-mode/v1"

for model in "${models[@]}"; do
    echo "🧪 测试模型连接: $model"
    echo "----------------------------------------"

    # 使用简单的echo命令测试模型响应
    # 使用timeout防止长时间挂起
    if command -v timeout &> /dev/null; then
        timeout_cmd="timeout 15s"
    else
        timeout_cmd=""
    fi

    # 创建一个简单的测试提示
    TEST_PROMPT="Hello, please respond with 'OK' if you can hear me."

    # 执行测试
    $timeout_cmd env \
        LLM_BASE_URL="$API_BASE" \
        LLM_MODEL="$model" \
        LLM_AUTH_TOKEN="$ALIYUN_API_KEY" \
        LLM_API_KEY="$ALIYUN_API_KEY" \
        AI_CODE_BARE=1 \
        AI_CODE_SKIP_KEYCHAIN=1 \
        /opt/homebrew/bin/claude echo "$TEST_PROMPT" 2>&1 | head -20

    echo ""
    sleep 2
done

echo "✅ 连接性测试完成"
echo ""
echo "📋 结果解读:"
echo "1. 如果看到 'OK' 或正常响应，表示模型连接成功"
echo "2. 如果看到 'issue with the selected model'，表示模型名称无效"
echo "3. 如果命令超时或没有输出，可能是API问题或模型名称错误"
