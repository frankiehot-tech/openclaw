#!/bin/bash

# 阿里云 Qwen Coding Plan Pro 配置
# 专用 Qwen3.6-Plus 启动脚本（替代 Qwen3.6-Max）

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 加载配置文件
CONFIG_FILE="${SCRIPT_DIR}/claude-config.sh"
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
else
    echo "❌ 未找到配置文件: $CONFIG_FILE" >&2
    exit 1
fi

echo "=========================================="
echo "  AI Assistant - Qwen3.6-Plus 专用"
echo "  套餐: Qwen Coding Plan Pro (90,000次/月)"
echo "=========================================="
echo ""
echo "⚡ 已选择: Qwen3.6-Plus (阿里云) - 最强可用性能"
echo "注意：Qwen3.6-Max 当前不可用，使用 Qwen3.6-Plus 作为替代"
echo ""

if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
    export_config "qwen3.6-plus"
fi

# 验证环境变量设置
echo "📊 配置信息:"
echo "  API端点: ${LLM_BASE_URL:0:50}..."
echo "  模型: $LLM_MODEL"
echo "  套餐: Qwen Coding Plan Pro"
echo ""

# 使用env命令确保环境变量覆盖
exec env \
  LLM_BASE_URL="$LLM_BASE_URL" \
  LLM_MODEL="$LLM_MODEL" \
  LLM_AUTH_TOKEN="$LLM_AUTH_TOKEN" \
  LLM_API_KEY="$LLM_API_KEY" \
  AI_CODE_BARE=1 \
  AI_CODE_SKIP_KEYCHAIN=1 \
  /opt/homebrew/bin/claude "$@"
