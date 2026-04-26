#!/bin/bash
# =============================================================================
# AI 智能路由器 - 自动检测主模型可用性并降级到备用模型
# 用法: bash scripts/ai-router.sh <model_name> [prompt]
# 功能: 自动检测 -> 重试 -> 降级 -> 返回结果
# =============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_DIR="$PROJECT_DIR/config/ai-config"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# ---------------------------------------------------------------------------
# 加载密钥
# ---------------------------------------------------------------------------
if [ -f "$HOME/.config/secret-env/load-keychain-secrets.sh" ]; then
    source "$HOME/.config/secret-env/load-keychain-secrets.sh"
fi

# ---------------------------------------------------------------------------
# 降级链配置
# ---------------------------------------------------------------------------
BAILIAN_FALLBACK_CHAIN=("qwen-max" "qwen3.6-plus" "qwen-plus" "qwen-turbo")
DEEPSEEK_FALLBACK_CHAIN=("deepseek-chat" "deepseek-coder")

# ---------------------------------------------------------------------------
# 测试单个模型是否可用
# ---------------------------------------------------------------------------
test_model_available() {
    local model="$1"
    local timeout="${2:-15}"

    # 获取 provider
    local provider base_url api_key
    case "$model" in
        qwen-*|qwen3*)
            provider="bailian"
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            api_key="${DASHSCOPE_API_KEY:-}"
            ;;
        deepseek-*)
            provider="deepseek"
            base_url="https://api.deepseek.com/v1"
            api_key="${DEEPSEEK_API_KEY:-}"
            ;;
        *)
            return 1
            ;;
    esac

    [ -z "$api_key" ] && return 1

    local response
    response=$(curl -s --connect-timeout 5 --max-time "$timeout" \
        "$base_url/chat/completions" \
        -H "Authorization: Bearer $api_key" \
        -H "Content-Type: application/json" \
        -d "{
            \"model\": \"$model\",
            \"messages\": [{\"role\": \"user\", \"content\": \"OK\"}],
            \"max_tokens\": 5
        }" 2>/dev/null)

    if echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'choices' in d and len(d['choices']) > 0" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# ---------------------------------------------------------------------------
# 找到第一个可用的模型
# ---------------------------------------------------------------------------
find_available_model() {
    local chain_name="$1"
    local chain=()

    case "$chain_name" in
        bailian) chain=("${BAILIAN_FALLBACK_CHAIN[@]}") ;;
        deepseek) chain=("${DEEPSEEK_FALLBACK_CHAIN[@]}") ;;
        *)
            # 自动检测
            case "$chain_name" in
                qwen-*|qwen3*) chain=("${BAILIAN_FALLBACK_CHAIN[@]}") ;;
                deepseek-*) chain=("${DEEPSEEK_FALLBACK_CHAIN[@]}") ;;
            esac
            ;;
    esac

    for model in "${chain[@]}"; do
        if test_model_available "$model" 10; then
            echo "$model"
            return 0
        fi
    done

    echo ""
    return 1
}

# ---------------------------------------------------------------------------
# 发送请求（带降级）
# ---------------------------------------------------------------------------
send_with_fallback() {
    local preferred_model="$1"
    local prompt="$2"
    local max_retries="${3:-2}"

    echo -e "${BOLD}${BLUE}━━━ AI 智能路由 ━━━${NC}"
    echo ""
    echo -e "  首选模型: ${BOLD}$preferred_model${NC}"
    echo -e "  请求内容: ${prompt:0:50}..."
    echo ""

    # 确定降级链
    local chain=()
    case "$preferred_model" in
        qwen-*|qwen3*) chain=("${BAILIAN_FALLBACK_CHAIN[@]}") ;;
        deepseek-*) chain=("${DEEPSEEK_FALLBACK_CHAIN[@]}") ;;
    esac

    # 找到 preferred_model 在链中的位置
    local start_idx=0
    for i in "${!chain[@]}"; do
        if [ "${chain[$i]}" = "$preferred_model" ]; then
            start_idx=$i
            break
        fi
    done

    # 从 preferred_model 开始尝试
    for ((i=start_idx; i<${#chain[@]}; i++)); do
        local model="${chain[$i]}"
        local is_primary=$([ $i -eq $start_idx ] && echo "true" || echo "false")

        if [ "$is_primary" = "true" ]; then
            echo -e "  尝试: ${BOLD}$model${NC} (首选)"
        else
            echo -e "  降级: ${YELLOW}$model${NC} (降级 #$((i - start_idx)))"
        fi

        # 测试模型可用性
        if ! test_model_available "$model" 10; then
            echo -e "    ${RED}不可用${NC}"
            continue
        fi

        echo -e "    ${GREEN}可用，发送请求...${NC}"

        # 获取 API Key
        local api_key
        case "$model" in
            qwen-*|qwen3*) api_key="${DASHSCOPE_API_KEY:-}" ;;
            deepseek-*) api_key="${DEEPSEEK_API_KEY:-}" ;;
        esac

        local base_url
        case "$model" in
            qwen-*|qwen3*) base_url="https://dashscope.aliyuncs.com/compatible-mode/v1" ;;
            deepseek-*) base_url="https://api.deepseek.com/v1" ;;
        esac

        # 发送请求
        local response
        response=$(curl -s --connect-timeout 10 --max-time 60 \
            "$base_url/chat/completions" \
            -H "Authorization: Bearer $api_key" \
            -H "Content-Type: application/json" \
            -d "{
                \"model\": \"$model\",
                \"messages\": [{\"role\": \"user\", \"content\": \"$prompt\"}],
                \"max_tokens\": 2000,
                \"temperature\": 0.7
            }" 2>/dev/null)

        local content
        content=$(echo "$response" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d['choices'][0]['message']['content'].strip())
except:
    print('')
" 2>/dev/null || echo "")

        if [ -n "$content" ]; then
            echo ""
            echo -e "${GREEN}✅ 模型 $model 响应成功${NC}"
            echo ""
            echo "$content"
            return 0
        fi

        echo -e "    ${RED}响应失败，尝试下一个${NC}"
    done

    echo ""
    echo -e "${RED}❌ 所有模型都不可用${NC}"
    return 1
}

# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
main() {
    local model="${1:-qwen-max}"
    local prompt="${2:-请用中文简短介绍你自己}"

    send_with_fallback "$model" "$prompt"
}

main "$@"