#!/bin/bash

# AI Assistant 智能模型路由系统
# 默认优先 Qwen + 本地 LLM 适配器，DeepSeek 作为备用模型。

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/claude-config.sh"
USAGE_MONITOR="${SCRIPT_DIR}/bailian-usage-monitor.sh"
AI_CLI_BIN="${AI_CLI_BIN:-/opt/homebrew/bin/ai-assistant}"

if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
else
    echo "❌ 未找到配置文件: $CONFIG_FILE" >&2
    exit 1
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

get_recommended_model() {
    if [[ "${1:-}" =~ ^[1-5]$ ]]; then
        echo "$1"
        return
    fi

    if [ -f "$USAGE_MONITOR" ]; then
        local recommended_model
        recommended_model="$("$USAGE_MONITOR" recommend 2>/dev/null || true)"
        case "$recommended_model" in
            qwen3.6-plus)
                echo "5"
                ;;
            deepseek-reasoner)
                echo "2"
                ;;
            *)
                echo "5"
                ;;
        esac
    else
        echo "5"
    fi
}

record_api_usage() {
    local model_choice="$1"
    local model_name=""

    case "$model_choice" in
        1) model_name="deepseek-chat" ;;
        2) model_name="deepseek-reasoner" ;;
        3|4|5) model_name="qwen3.6-plus" ;;
        *) model_name="unknown" ;;
    esac

    if [[ "$model_choice" =~ ^[345]$ ]] && [ -f "$USAGE_MONITOR" ]; then
        "$USAGE_MONITOR" record "$model_name" >/dev/null 2>&1 || true
    fi
}

show_usage_status() {
    if [ -f "$USAGE_MONITOR" ]; then
        echo ""
        echo -e "${CYAN}📊 百炼 PRO 套餐使用监控${NC}"
        echo "------------------------------------------"
        "$USAGE_MONITOR" check || true
    fi
}

AUTO_SELECT=false
if [[ "${1:-}" =~ ^[1-5]$ ]]; then
    choice="$1"
    AUTO_SELECT=true
    shift
elif [ "${1:-}" = "auto" ]; then
    choice="$(get_recommended_model)"
    AUTO_SELECT=true
    shift
fi

echo "=========================================="
echo "  AI Assistant - 智能模型路由系统"
echo "  套餐: 百炼PRO (90,000次/月)"
echo "=========================================="
echo ""

if [ "$AUTO_SELECT" = false ]; then
    show_usage_status
    echo ""
    echo "🤖 模型选择:"
    echo ""
    echo "  🎯 百炼PRO套餐 (推荐)"
    echo "  5. Qwen3.6-Plus (默认)       - 统一走本地适配器"
    echo "  3. Qwen3.6-Plus (中文优化)   - 同样走本地适配器"
    echo ""
    echo "  🔄 备用方案"
    echo "  2. DeepSeek Reasoner         - 复杂推理 / 架构设计"
    echo "  1. DeepSeek Chat             - 快速编码 / 日常开发"
    echo ""
    echo "  🔧 工具模式"
    echo "  auto - 自动选择"
    echo ""

    read -r -p "选择 [1-3,5,auto] (默认: auto): " choice_input
    if [ -z "$choice_input" ]; then
        choice_input="auto"
    fi

    if [ "$choice_input" = "auto" ]; then
        choice="$(get_recommended_model)"
        AUTO_SELECT=true
    elif [[ "$choice_input" =~ ^[1-35]$ ]]; then
        choice="$choice_input"
    else
        echo -e "${YELLOW}⚠️  无效选择，使用自动模式${NC}"
        choice="$(get_recommended_model)"
        AUTO_SELECT=true
    fi
fi

choice="$(echo "$choice" | tr -d '[:space:]')"

echo ""
echo -e "${BLUE}🤖 模型配置${NC}"
echo "------------------------------------------"

record_api_usage "$choice"

case "$choice" in
    1)
        export_config "deepseek-chat" || exit 1
        echo -e "🚀 ${GREEN}已选择: DeepSeek Chat${NC}"
        echo -e "${YELLOW}📝 模式: 备用方案${NC}"
        ;;
    2)
        export_config "deepseek-reasoner" || exit 1
        echo -e "🧠 ${GREEN}已选择: DeepSeek Reasoner${NC}"
        echo -e "${YELLOW}📝 模式: 备用方案${NC}"
        ;;
    3|4|5|*)
        export_config "qwen3.6-plus" || exit 1
        echo -e "🎯 ${GREEN}已选择: Qwen3.6-Plus${NC}"
        echo -e "${YELLOW}📝 模式: 百炼PRO，经本地适配器连接 DashScope${NC}"
        ;;
esac

if [ "$AUTO_SELECT" = true ]; then
    show_usage_status
fi

echo ""
echo -e "${BLUE}📊 配置信息${NC}"
echo "------------------------------------------"
echo "• API端点: $LLM_BASE_URL"
echo "• 模型: $LLM_MODEL"
echo "• 套餐: 百炼PRO (90,000次/月)"
echo "• 智能路由: ${AUTO_SELECT}"
echo ""

if [[ "$choice" =~ ^[345]$ ]]; then
    echo -e "${GREEN}💰 成本优化: 默认走本地 DashScope 适配链路${NC}"
    echo ""
else
    echo -e "${YELLOW}⚠️  当前使用备用方案 (按 token 计费)${NC}"
    echo ""
fi

echo -e "${CYAN}🚀 启动 AI Assistant...${NC}"
echo ""

exec env \
  LLM_BASE_URL="$LLM_BASE_URL" \
  LLM_MODEL="$LLM_MODEL" \
  LLM_AUTH_TOKEN="$LLM_AUTH_TOKEN" \
  LLM_API_KEY="$LLM_API_KEY" \
  AI_CODE_BARE=1 \
  AI_CODE_SKIP_KEYCHAIN=1 \
  "$AI_CLI_BIN" "$@"
