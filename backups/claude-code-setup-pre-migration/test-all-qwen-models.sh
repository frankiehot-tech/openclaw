#!/bin/bash

# 测试所有可能的Qwen模型名称

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/load-local-secrets.sh"
require_any_secret DASHSCOPE_API_KEY ALIYUN_API_KEY || exit 1

export DASHSCOPE_API_KEY="${DASHSCOPE_API_KEY:-$ALIYUN_API_KEY}"
export AI_CODE_BARE=1
export AI_CODE_SKIP_KEYCHAIN=1

API_BASE="https://dashscope.aliyuncs.com/compatible-mode/v1"

# 所有可能的模型名称
MODELS=(
    # 不带前缀
    "qwen-turbo"
    "qwen-plus"
    "qwen-max"
    "qwen-coder"
    "qwen-flash"
    "qwen3.6-turbo"
    "qwen3.6-plus"
    "qwen3.6-max"
    "qwen3.6-coder"
    "qwen3.6-flash"
    "qwen3-turbo"
    "qwen3-plus"
    "qwen3-max"
    "qwen3-coder"
    "qwen3-flash"

    # 带前缀
    "dashscope/qwen-turbo"
    "dashscope/qwen-plus"
    "dashscope/qwen-max"
    "dashscope/qwen-coder"
    "dashscope/qwen-flash"
    "dashscope/qwen3.6-turbo"
    "dashscope/qwen3.6-plus"
    "dashscope/qwen3.6-max"
    "dashscope/qwen3.6-coder"
    "dashscope/qwen3.6-flash"
    "dashscope/qwen3-turbo"
    "dashscope/qwen3-plus"
    "dashscope/qwen3-max"
    "dashscope/qwen3-coder"
    "dashscope/qwen3-flash"

    # 带日期版本
    "dashscope/qwen-plus-2025-01-25"
    "dashscope/qwen-plus-2025-04-28"
    "dashscope/qwen-plus-2025-07-14"
    "dashscope/qwen-plus-2025-07-28"
    "dashscope/qwen-plus-2025-09-11"
    "dashscope/qwen-plus-latest"
    "dashscope/qwen-turbo-2024-11-01"
    "dashscope/qwen-turbo-2025-04-28"
    "dashscope/qwen-turbo-latest"
    "dashscope/qwen3-max-2026-01-23"
    "dashscope/qwen3-coder-plus"
    "dashscope/qwen3-coder-plus-2025-07-22"
    "dashscope/qwen3-coder-flash"
    "dashscope/qwen3-coder-flash-2025-07-28"
)

echo "🔍 测试所有Qwen模型"
echo "====================="
echo "使用API密钥: ${DASHSCOPE_API_KEY:0:10}..."
echo ""

SUCCESS_COUNT=0
FAIL_COUNT=0

for model in "${MODELS[@]}"; do
    echo -n "🧪 $model: "

    # 运行测试，限制输出
    OUTPUT=$(env \
        LLM_BASE_URL="$API_BASE" \
        LLM_MODEL="$model" \
        LLM_AUTH_TOKEN="$DASHSCOPE_API_KEY" \
        LLM_API_KEY="$DASHSCOPE_API_KEY" \
        AI_CODE_BARE=1 \
        AI_CODE_SKIP_KEYCHAIN=1 \
        /opt/homebrew/bin/claude echo "test" 2>&1 | head -5)

    # 检查是否成功（没有错误信息）
    if echo "$OUTPUT" | grep -q "issue with the selected model"; then
        echo "❌ 失败"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    else
        # 检查是否有其他错误或正常输出
        if echo "$OUTPUT" | grep -q -E "error|Error|ERROR|failed|Failed"; then
            echo "⚠️  可能有其他错误"
            echo "   输出: $(echo "$OUTPUT" | head -1)"
        else
            echo "✅ 可能成功"
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
            # 显示第一行输出
            echo "   输出: $(echo "$OUTPUT" | head -1)"
        fi
    fi

    sleep 1  # 避免速率限制
done

echo ""
echo "📊 测试结果:"
echo "  成功: $SUCCESS_COUNT"
echo "  失败: $FAIL_COUNT"
echo "  总计: ${#MODELS[@]}"

if [ $SUCCESS_COUNT -eq 0 ]; then
    echo ""
    echo "⚠️  所有模型测试都失败了。可能的原因:"
    echo "  1. API密钥无效或无权限"
    echo "  2. 端点URL不正确"
    echo "  3. 套餐不包含任何Qwen模型"
    echo "  4. 需要额外的认证参数"
fi
