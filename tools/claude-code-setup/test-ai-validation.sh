#!/bin/bash

# AI Assistant 百炼PRO适配器验证脚本
# 模拟AI Assistant的完整验证流程

echo "🔍 AI Assistant 百炼PRO适配器验证测试"
echo "========================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/load-local-secrets.sh"
require_any_secret DASHSCOPE_API_KEY ALIYUN_API_KEY || exit 1

# 设置环境变量
export LLM_BASE_URL="http://localhost:8080"
export LLM_MODEL="qwen3.6-plus"
export LLM_AUTH_TOKEN="${DASHSCOPE_API_KEY:-$ALIYUN_API_KEY}"
export LLM_API_KEY="$LLM_AUTH_TOKEN"
export AI_CODE_BARE=1
export AI_CODE_SKIP_KEYCHAIN=1

echo "✅ 环境变量已设置"
echo "  LLM_BASE_URL: $LLM_BASE_URL"
echo "  LLM_MODEL: $LLM_MODEL"
echo "  AI_CODE_BARE: $AI_CODE_BARE"
echo ""

# 测试1: 验证API根端点
echo "📋 测试1: API根端点验证"
if curl -s -f "$LLM_BASE_URL/" > /dev/null 2>&1; then
    echo "  ✅ API根端点可达"
    root_response=$(curl -s "$LLM_BASE_URL/")
    echo "  响应: $root_response"
else
    echo "  ❌ API根端点不可达"
    exit 1
fi

echo ""

# 测试2: 验证模型列表端点
echo "📋 测试2: 模型列表验证"
if curl -s -f "$LLM_BASE_URL/v1/models" > /dev/null 2>&1; then
    echo "  ✅ 模型列表端点可达"
    models_response=$(curl -s "$LLM_BASE_URL/v1/models" | jq -r '.models[].id')
    echo "  可用模型: $models_response"

    # 检查是否包含我们的模型
    if echo "$models_response" | grep -q "qwen3.6-plus"; then
        echo "  ✅ 目标模型存在: qwen3.6-plus"
    else
        echo "  ❌ 目标模型不存在"
        exit 1
    fi
else
    echo "  ❌ 模型列表端点不可达"
    exit 1
fi

echo ""

# 测试3: 验证模型详情端点
echo "📋 测试3: 模型详情验证"
model_url="$LLM_BASE_URL/v1/models/$LLM_MODEL"
if curl -s -f "$model_url" > /dev/null 2>&1; then
    echo "  ✅ 模型详情端点可达"
    model_details=$(curl -s "$model_url" | jq -r '{id, name, max_tokens, capabilities}')
    echo "  模型详情: $model_details"
else
    echo "  ❌ 模型详情端点不可达"
    exit 1
fi

echo ""

# 测试4: 验证消息端点
echo "📋 测试4: 消息端点验证"
test_message='{"model": "qwen3.6-plus", "messages": [{"role": "user", "content": "Test message from AI Assistant validation"}], "max_tokens": 10}'
if curl -s -f -X POST "$LLM_BASE_URL/v1/messages" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $LLM_AUTH_TOKEN" \
    -d "$test_message" > /dev/null 2>&1; then
    echo "  ✅ 消息端点可达"

    # 获取完整的响应
    response=$(curl -s -X POST "$LLM_BASE_URL/v1/messages" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $LLM_AUTH_TOKEN" \
        -d "$test_message")

    if echo "$response" | jq -e '.id' > /dev/null 2>&1; then
        response_id=$(echo "$response" | jq -r '.id')
        model=$(echo "$response" | jq -r '.model')
        role=$(echo "$response" | jq -r '.role')
        echo "  ✅ 消息响应格式正确"
        echo "    响应ID: $response_id"
        echo "    模型: $model"
        echo "    角色: $role"
    else
        echo "  ❌ 消息响应格式错误"
        echo "    响应: $response"
        exit 1
    fi
else
    echo "  ❌ 消息端点不可达"
    exit 1
fi

echo ""
echo "🎉 所有验证测试通过!"
echo ""
echo "📋 验证总结:"
echo "   1. ✅ API根端点可达"
echo "   2. ✅ 模型列表包含目标模型"
echo "   3. ✅ 模型详情端点工作正常"
echo "   4. ✅ 消息端点格式正确"
echo ""
echo "🚀 适配器已准备好供AI Assistant使用!"
echo ""
echo "使用方法:"
echo "  1. 设置环境变量:"
echo "     eval \"\$($(dirname "$0")/claude-dashscope-adapter.sh start quiet 2>/dev/null)\""
echo "  2. 启动AI Assistant:"
echo "     claude"
echo ""
