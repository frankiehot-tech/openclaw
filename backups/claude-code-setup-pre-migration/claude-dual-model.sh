#!/bin/bash

# Claude Code 统一入口 - 支持云端模型 + Ollama 本地模型
# 用法:
#   claude                     # 自动选择模型
#   claude local               # Ollama 本地模式 (gemma4-claude, 128K 上下文)
#   claude local-big           # Ollama 本地 gemma4-claude (128K 上下文)
#   claude 1                   # DeepSeek Chat
#   claude 2                   # DeepSeek Reasoner
#   claude 3                   # Qwen 中文优化
#   claude 5                   # Qwen 默认

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

# ==================== Ollama 本地模式配置 ====================
setup_ollama_local() {
    local model_name="${1:-gemma4-claude}"

    export ANTHROPIC_BASE_URL="http://localhost:11434"
    export ANTHROPIC_AUTH_TOKEN="ollama"
    export ANTHROPIC_API_KEY=""
    export ANTHROPIC_MODEL="$model_name"

    echo -e "${MAGENTA}🏠 Ollama 本地模式${NC}"
    echo -e "${BLUE}------------------------------------------${NC}"
    echo -e "• 模型: ${CYAN}${model_name}${NC}"
    echo -e "• 上下文: ${CYAN}128K (E4B)${NC}"
    echo -e "• 内存占用: ${CYAN}~11GB${NC}"
    echo -e "• 速度: ${CYAN}本地 Metal GPU 加速${NC}"
    echo -e "${BLUE}------------------------------------------${NC}"

    # 检查 Ollama 服务是否运行
    if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo -e "${RED}❌ Ollama 服务未运行${NC}"
        echo -e "${YELLOW}启动命令: brew services start ollama${NC}"
        exit 1
    fi

    # 检查模型是否存在
    if ! ollama list | grep -q "$model_name"; then
        echo -e "${RED}❌ 模型 ${model_name} 未找到${NC}"
        echo -e "${YELLOW}可用模型:${NC}"
        ollama list | grep -E "gemma4" || echo "无 Gemma4 模型"
        exit 1
    fi
}

# ==================== 云端模型配置 ====================
setup_cloud_model() {
    local choice="$1"

    # 加载百炼PRO配置（如有）
    if [ -f "$SCRIPT_DIR/dashscope-adapter.py" ]; then
        export DASHSCOPE_ADAPTER="$SCRIPT_DIR/dashscope-adapter.py"
    fi

    case "$choice" in
        1)
            export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
            export ANTHROPIC_MODEL="deepseek-chat"
            export ANTHROPIC_API_KEY="${DEEPSEEK_API_KEY:-}"
            export ANTHROPIC_AUTH_TOKEN="${DEEPSEEK_API_KEY:-}"
            echo -e "${GREEN}🚀 已选择: DeepSeek Chat${NC}"
            echo -e "${YELLOW}📝 模式: 快速编码 / 日常开发${NC}"
            ;;
        2)
            export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
            export ANTHROPIC_MODEL="deepseek-reasoner"
            export ANTHROPIC_API_KEY="${DEEPSEEK_API_KEY:-}"
            export ANTHROPIC_AUTH_TOKEN="${DEEPSEEK_API_KEY:-}"
            echo -e "${GREEN}🧠 已选择: DeepSeek Reasoner${NC}"
            echo -e "${YELLOW}📝 模式: 复杂推理 / 架构设计${NC}"
            ;;
        3)
            export ANTHROPIC_BASE_URL="${DASHSCOPE_BASE_URL:-https://dashscope.aliyuncs.com/compatible-mode/v1}"
            export ANTHROPIC_MODEL="qwen3.6-plus"
            export ANTHROPIC_API_KEY="${DASHSCOPE_API_KEY:-}"
            export ANTHROPIC_AUTH_TOKEN="${DASHSCOPE_API_KEY:-}"
            echo -e "${GREEN}🎯 已选择: Qwen3.6-Plus (中文优化)${NC}"
            echo -e "${YELLOW}📝 模式: 百炼PRO，经本地适配器${NC}"
            ;;
        5|*)
            export ANTHROPIC_BASE_URL="${DASHSCOPE_BASE_URL:-https://dashscope.aliyuncs.com/compatible-mode/v1}"
            export ANTHROPIC_MODEL="qwen3.6-plus"
            export ANTHROPIC_API_KEY="${DASHSCOPE_API_KEY:-}"
            export ANTHROPIC_AUTH_TOKEN="${DASHSCOPE_API_KEY:-}"
            echo -e "${GREEN}🎯 已选择: Qwen3.6-Plus (默认)${NC}"
            echo -e "${YELLOW}📝 模式: 百炼PRO，经本地适配器${NC}"
            ;;
    esac
}

# ==================== 主逻辑 ====================
echo "=========================================="
echo "  Claude Code - 智能模型路由系统"
echo "  支持: Ollama 本地 + 云端多模型"
echo "=========================================="
echo ""

# 参数解析
choice="${1:-auto}"
shift 2>/dev/null

case "$choice" in
    local|ollama|o)
        setup_ollama_local "gemma4-claude"
        ;;
    local-big|ollama-big|o-big|big)
        setup_ollama_local "gemma4-claude"
        echo -e "• 上下文: ${CYAN}128K (E4B)${NC}"
        echo -e "• 内存占用: ${CYAN}~10GB${NC}"
        ;;
    1)
        setup_cloud_model "1"
        ;;
    2)
        setup_cloud_model "2"
        ;;
    3|4)
        setup_cloud_model "3"
        ;;
    5|*)
        setup_cloud_model "5"
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

# 启动 Claude Code（不使用 --bare，避免认证问题）
exec env \
  ANTHROPIC_BASE_URL="$ANTHROPIC_BASE_URL" \
  ANTHROPIC_MODEL="$ANTHROPIC_MODEL" \
  ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  CLAUDE_CODE_AUTO_COMPACT_WINDOW=120000 \
  CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=60 \
  claude "$@"
