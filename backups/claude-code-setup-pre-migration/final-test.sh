#!/bin/bash

# 最终测试：在尽可能干净的环境中测试

echo "🔬 最终诊断测试"
echo "====================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/load-local-secrets.sh"
require_any_secret DASHSCOPE_API_KEY ALIYUN_API_KEY || exit 1

# 设置关键环境变量，其他全部清除
export PATH="/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin"
export ALIYUN_API_KEY="${ALIYUN_API_KEY:-$DASHSCOPE_API_KEY}"
export DASHSCOPE_API_KEY="${DASHSCOPE_API_KEY:-$ALIYUN_API_KEY}"

# 测试1: 使用ALIYUN_API_KEY
echo "1. 使用 ALIYUN_API_KEY 测试 qwen-plus"
env -i \
    PATH="$PATH" \
    LLM_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1" \
    LLM_MODEL="qwen-plus" \
    LLM_AUTH_TOKEN="$ALIYUN_API_KEY" \
    LLM_API_KEY="$ALIYUN_API_KEY" \
    /opt/homebrew/bin/claude echo "test" 2>&1 | grep -E "issue|error|Error|OK|test" | head -5
echo ""

# 测试2: 使用DASHSCOPE_API_KEY
echo "2. 使用 DASHSCOPE_API_KEY 测试 qwen-plus"
env -i \
    PATH="$PATH" \
    LLM_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1" \
    LLM_MODEL="qwen-plus" \
    LLM_AUTH_TOKEN="$DASHSCOPE_API_KEY" \
    LLM_API_KEY="$DASHSCOPE_API_KEY" \
    /opt/homebrew/bin/claude echo "test" 2>&1 | grep -E "issue|error|Error|OK|test" | head -5
echo ""

# 测试3: 测试DeepSeek作为对比
echo "3. 测试 DeepSeek Chat (对比)"
env -i \
    PATH="$PATH" \
    LLM_BASE_URL="https://api.deepseek.com/v1" \
    LLM_MODEL="deepseek-chat" \
    LLM_AUTH_TOKEN="${DEEPSEEK_API_KEY:-$ALIYUN_API_KEY}" \
    LLM_API_KEY="${DEEPSEEK_API_KEY:-$ALIYUN_API_KEY}" \
    /opt/homebrew/bin/claude echo "test" 2>&1 | grep -E "issue|error|Error|OK|test" | head -5
echo ""

echo "✅ 测试完成"
echo ""
echo "📋 可能的问题:"
echo "1. API密钥无效或无Qwen模型权限"
echo "2. 套餐虽续期但API密钥需要重新生成"
echo "3. 阿里云百炼服务未正确激活"
echo "4. 需要联系阿里云技术支持"
