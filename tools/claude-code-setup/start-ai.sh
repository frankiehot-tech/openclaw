#!/bin/bash

# AI Assistant 启动脚本
# 统一走本地 DashScope LLM 适配器。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/claude-config.sh"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ 未找到配置文件: $CONFIG_FILE" >&2
    exit 1
fi

source "$CONFIG_FILE"

echo "🔍 检查 DashScope 代理状态..."
ensure_dashscope_adapter
export_config "qwen3.6-plus" >/dev/null

echo ""
echo "📋 配置信息:"
echo "   模型: ${LLM_MODEL}"
echo "   代理: ${LLM_BASE_URL}"
echo "   后端: DashScope (阿里云百炼)"
echo ""
echo "🚀 启动 AI Assistant..."
echo ""

exec env \
  LLM_BASE_URL="$LLM_BASE_URL" \
  LLM_MODEL="$LLM_MODEL" \
  LLM_AUTH_TOKEN="$LLM_AUTH_TOKEN" \
  LLM_API_KEY="$LLM_API_KEY" \
  AI_CODE_BARE=1 \
  AI_CODE_SKIP_KEYCHAIN=1 \
  "$AI_CLI_BIN" "$@"
