#!/bin/bash

# Claude Code 智能路由系统 v2
# 支持: 本地模型 + 云端模型，自动根据任务复杂度选择
#
# 用法:
#   claude                    # 自动选择模型
#   claude local              # 强制本地模式
#   claude cloud              # 强制云端模式
#   claude 1                  # DeepSeek Chat
#   claude 2                  # DeepSeek Reasoner
#   claude 3                  # Qwen 中文优化
#   claude 5                  # Qwen 默认

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USAGE_MONITOR="${SCRIPT_DIR}/bailian-usage-monitor.sh"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# ==================== 任务复杂度分析 ====================
analyze_complexity() {
    local input="${1:-}"
    local current_file="${CURRENT_FILE:-}"

    # 重型任务关键词
    local heavy_keywords="架构|重构|分析|设计|复杂|大型|深度|review|audit|优化|性能|安全|并发|分布式|微服务"

    # 检查输入中的关键词
    if echo "$input" | grep -qiE "$heavy_keywords"; then
        echo "heavy"
        return
    fi

    # 检查当前文件大小
    if [ -n "$current_file" ] && [ -f "$current_file" ]; then
        local lines=$(wc -l < "$current_file" 2>/dev/null || echo 0)
        if [ "$lines" -gt 1000 ]; then
            echo "heavy"
            return
        fi
    fi

    # 检查上下文长度（通过环境变量）
    if [ "${CONTEXT_LENGTH:-0}" -gt 16000 ]; then
        echo "heavy"
        return
    fi

    echo "light"
}

# ==================== 本地模型配置 ====================
setup_ollama_local() {
    local model_name="${1:-qwen2.5-claude}"

    export ANTHROPIC_BASE_URL="http://localhost:11434"
    export ANTHROPIC_AUTH_TOKEN="ollama"
    export ANTHROPIC_API_KEY=""
    export ANTHROPIC_MODEL="$model_name"

    echo -e "${MAGENTA}🏠 本地模式${NC}"
    echo -e "${BLUE}------------------------------------------${NC}"
    echo -e "• 模型: ${CYAN}${model_name}${NC}"
    echo -e "• 类型: ${CYAN}轻量任务 / 零成本${NC}"
    echo -e "• 速度: ${CYAN}本地 Metal GPU 加速${NC}"
    echo -e "${BLUE}------------------------------------------${NC}"

    # 检查 Ollama 服务
    if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo -e "${RED}❌ Ollama 服务未运行${NC}"
        echo -e "${YELLOW}启动命令: brew services start ollama${NC}"
        exit 1
    fi

    # 检查模型是否存在
    if ! ollama list | grep -q "$model_name"; then
        echo -e "${RED}❌ 模型 ${model_name} 未找到${NC}"
        echo -e "${YELLOW}可用模型:${NC}"
        ollama list
        exit 1
    fi
}

# ==================== 云端模型配置 ====================
setup_cloud_model() {
    local choice="$1"

    case "$choice" in
        deepseek-chat|1)
            export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
            export ANTHROPIC_MODEL="deepseek-chat"
            export ANTHROPIC_API_KEY="${DEEPSEEK_API_KEY:-}"
            export ANTHROPIC_AUTH_TOKEN="${DEEPSEEK_API_KEY:-}"
            echo -e "${GREEN}🚀 云端: DeepSeek Chat${NC}"
            ;;
        deepseek-reasoner|2)
            export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
            export ANTHROPIC_MODEL="deepseek-reasoner"
            export ANTHROPIC_API_KEY="${DEEPSEEK_API_KEY:-}"
            export ANTHROPIC_AUTH_TOKEN="${DEEPSEEK_API_KEY:-}"
            echo -e "${GREEN}🧠 云端: DeepSeek Reasoner${NC}"
            ;;
        qwen|qwen-max|5)
            export ANTHROPIC_BASE_URL="${DASHSCOPE_BASE_URL:-https://dashscope.aliyuncs.com/compatible-mode/v1}"
            export ANTHROPIC_MODEL="qwen-max"
            export ANTHROPIC_API_KEY="${DASHSCOPE_API_KEY:-}"
            export ANTHROPIC_AUTH_TOKEN="${DASHSCOPE_API_KEY:-}"
            echo -e "${GREEN}🎯 云端: Qwen-Max (百炼)${NC}"
            ;;
        qwen-plus|3)
            export ANTHROPIC_BASE_URL="${DASHSCOPE_BASE_URL:-https://dashscope.aliyuncs.com/compatible-mode/v1}"
            export ANTHROPIC_MODEL="qwen-plus"
            export ANTHROPIC_API_KEY="${DASHSCOPE_API_KEY:-}"
            export ANTHROPIC_AUTH_TOKEN="${DASHSCOPE_API_KEY:-}"
            echo -e "${GREEN}🎯 云端: Qwen-Plus (百炼)${NC}"
            ;;
        *)
            export ANTHROPIC_BASE_URL="${DASHSCOPE_BASE_URL:-https://dashscope.aliyuncs.com/compatible-mode/v1}"
            export ANTHROPIC_MODEL="qwen-max"
            export ANTHROPIC_API_KEY="${DASHSCOPE_API_KEY:-}"
            export ANTHROPIC_AUTH_TOKEN="${DASHSCOPE_API_KEY:-}"
            echo -e "${GREEN}🎯 云端: Qwen-Max (默认)${NC}"
            ;;
    esac

    echo -e "${YELLOW}📝 模式: 重型任务 / 按量计费${NC}"
}

# ==================== 智能路由 ====================
setup_smart_route() {
    local user_input="${1:-}"
    local complexity=$(analyze_complexity "$user_input")

    echo "=========================================="
    echo "  Claude Code - 智能模型路由系统 v2"
    echo "=========================================="
    echo ""

    case "$complexity" in
        heavy)
            echo -e "${YELLOW}🧠 任务复杂度: 重型${NC}"
            echo -e "${YELLOW}   检测到复杂任务关键词或大型文件${NC}"
            echo ""
            setup_cloud_model "qwen-max"
            ;;
        light)
            echo -e "${GREEN}⚡ 任务复杂度: 轻量${NC}"
            echo -e "${GREEN}   使用本地模型，零延迟零成本${NC}"
            echo ""
            setup_ollama_local "qwen2.5-claude"
            ;;
    esac
}

# ==================== 主逻辑 ====================
choice="${1:-auto}"
shift 2>/dev/null || true

case "$choice" in
    local|ollama|o)
        setup_ollama_local "qwen2.5-claude"
        ;;
    local-big|big)
        setup_ollama_local "qwen2.5-claude"
        echo -e "• 上下文: ${CYAN}32K${NC}"
        ;;
    cloud|c)
        setup_cloud_model "qwen-max"
        ;;
    1)
        setup_cloud_model "deepseek-chat"
        ;;
    2)
        setup_cloud_model "deepseek-reasoner"
        ;;
    3)
        setup_cloud_model "qwen-plus"
        ;;
    5)
        setup_cloud_model "qwen-max"
        ;;
    auto|*)
        setup_smart_route "$*"
        ;;
esac

echo ""
echo -e "${BLUE}📊 环境信息${NC}"
echo -e "${BLUE}------------------------------------------${NC}"
echo -e "• API端点: ${CYAN}${ANTHROPIC_BASE_URL}${NC}"
echo -e "• 模型: ${CYAN}${ANTHROPIC_MODEL}${NC}"
echo -e "• 自动压缩: ${CYAN}60%${NC}"
echo ""

# 启动 Claude Code
echo -e "${CYAN}🚀 启动 Claude Code...${NC}"
echo ""

exec env \
  ANTHROPIC_BASE_URL="$ANTHROPIC_BASE_URL" \
  ANTHROPIC_MODEL="$ANTHROPIC_MODEL" \
  ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  CLAUDE_CODE_AUTO_COMPACT_WINDOW=120000 \
  CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=60 \
  claude "$@"
