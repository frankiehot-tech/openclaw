#!/bin/bash

# AI Assistant 配置文件
# 统一管理 DeepSeek / DashScope 配置，并确保 Qwen 统一走本地 LLM 适配器。

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP_DIR="${TMPDIR:-/tmp}"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 本地适配器配置
DASHSCOPE_ADAPTER_HOST="${DASHSCOPE_ADAPTER_HOST:-127.0.0.1}"
DASHSCOPE_ADAPTER_PORT="${DASHSCOPE_ADAPTER_PORT:-8080}"
DASHSCOPE_ADAPTER_URL="${DASHSCOPE_ADAPTER_URL:-http://${DASHSCOPE_ADAPTER_HOST}:${DASHSCOPE_ADAPTER_PORT}}"
DASHSCOPE_ADAPTER_PID_FILE="${DASHSCOPE_ADAPTER_PID_FILE:-${TMP_DIR}/dashscope-adapter.pid}"
DASHSCOPE_ADAPTER_LOG="${DASHSCOPE_ADAPTER_LOG:-${TMP_DIR}/dashscope-adapter.log}"
DASHSCOPE_ADAPTER_MODEL="${DASHSCOPE_ADAPTER_MODEL:-qwen3.6-plus}"
AI_CLI_BIN="${AI_CLI_BIN:-/opt/homebrew/bin/ai-assistant}"

# API 密钥
DASHSCOPE_API_KEY="${DASHSCOPE_API_KEY:-}"
DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY:-}"
ALIYUN_API_KEY="${ALIYUN_API_KEY:-$DASHSCOPE_API_KEY}"

# DeepSeek 配置
DEEPSEEK_BASE_URL="https://api.deepseek.com/v1"
DEEPSEEK_MODELS_URL="https://api.deepseek.com/v1/models"
DEEPSEEK_CHAT_MODEL="deepseek-chat"
DEEPSEEK_REASONER_MODEL="deepseek-reasoner"

# DashScope 配置
BAILIAN_PRO_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
BAILIAN_PRO_MODEL_DEEPSEEK_R1="deepseek-r1"
DASHSCOPE_BASE_URL="https://dashscope.aliyuncs.com"
DASHSCOPE_COMPATIBLE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
DASHSCOPE_MODEL_QWEN_MAX="qwen3.6-max"
DASHSCOPE_MODEL_QWEN_PLUS="qwen3.6-plus"
DASHSCOPE_MODEL_QWEN_FLASH="qwen3.5-flash"
DASHSCOPE_MODEL_QWEN_PLUS_OLD="qwen3.5-plus"

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

ensure_dashscope_adapter() {
    local adapter_script="${SCRIPT_DIR}/dashscope-adapter.py"
    local existing_pid=""

    # 如果适配器已经在运行，直接返回
    if curl -fsS "${DASHSCOPE_ADAPTER_URL}/health" >/dev/null 2>&1; then
        log_info "本地适配器已运行"
        return 0
    fi

    if [ ! -f "$adapter_script" ]; then
        log_error "未找到适配器脚本: $adapter_script"
        return 1
    fi

    # 停止旧的适配器进程（如果有）
    if [ -f "$DASHSCOPE_ADAPTER_PID_FILE" ]; then
        existing_pid="$(cat "$DASHSCOPE_ADAPTER_PID_FILE" 2>/dev/null || true)"
        if [ -n "$existing_pid" ] && ps -p "$existing_pid" >/dev/null 2>&1; then
            log_info "停止旧的适配器进程 (PID: $existing_pid)"
            kill "$existing_pid" >/dev/null 2>&1 || true
            sleep 1
        fi
    fi

    if [ -z "${DASHSCOPE_API_KEY:-${ALIYUN_API_KEY:-}}" ]; then
        log_warning "未检测到 DASHSCOPE_API_KEY，适配器将依赖调用方传入 Authorization"
    fi

    log_info "启动本地适配器..."
    nohup python3 "$adapter_script" > "$DASHSCOPE_ADAPTER_LOG" 2>&1 &
    local new_pid=$!
    echo "$new_pid" > "$DASHSCOPE_ADAPTER_PID_FILE"

    # 轮询等待适配器就绪（最多 15 秒）
    local max_wait=15
    local waited=0
    local interval=1
    while [ "$waited" -lt "$max_wait" ]; do
        sleep "$interval"
        waited=$((waited + interval))
        if curl -fsS "${DASHSCOPE_ADAPTER_URL}/health" >/dev/null 2>&1; then
            log_success "本地适配器已就绪 (PID: $new_pid, 等待 ${waited}s)"
            return 0
        fi
    done

    log_error "DashScope 适配器启动超时（等待 ${max_wait}s），请检查日志: $DASHSCOPE_ADAPTER_LOG"
    # 清理失败进程
    kill "$new_pid" >/dev/null 2>&1 || true
    return 1
}

check_config() {
    echo -e "${CYAN}🔧 AI Assistant 配置检查${NC}"
    echo ""

    echo -e "${YELLOW}1. API 密钥状态:${NC}"

    local dashscope_status
    if [ -n "$DASHSCOPE_API_KEY" ] && curl -s -X GET "${DASHSCOPE_BASE_URL}/api/v1/models" \
        -H "Authorization: Bearer ${DASHSCOPE_API_KEY}" \
        -H "Content-Type: application/json" \
        -o /dev/null -w "%{http_code}" 2>/dev/null | grep -q "200"; then
        dashscope_status="${GREEN}✓${NC}"
    elif [ -n "$DASHSCOPE_API_KEY" ]; then
        dashscope_status="${RED}✗${NC}"
    else
        dashscope_status="${YELLOW}⚠${NC} (未设置)"
    fi
    echo "  DashScope (阿里云): $dashscope_status"

    local deepseek_status
    if [ -z "$DEEPSEEK_API_KEY" ]; then
        deepseek_status="${YELLOW}⚠${NC} (未设置)"
    elif curl -s -X GET "${DEEPSEEK_MODELS_URL}" \
        -H "Authorization: Bearer ${DEEPSEEK_API_KEY}" \
        -H "Content-Type: application/json" \
        -o /dev/null -w "%{http_code}" 2>/dev/null | grep -q "200"; then
        deepseek_status="${GREEN}✓${NC}"
    else
        deepseek_status="${RED}✗${NC}"
    fi
    echo "  DeepSeek: $deepseek_status"

    echo ""
    echo -e "${YELLOW}2. 模型配置:${NC}"
    echo "  DeepSeek Chat: $DEEPSEEK_CHAT_MODEL"
    echo "  DeepSeek Reasoner: $DEEPSEEK_REASONER_MODEL"
    echo "  Qwen3.6-Plus: $DASHSCOPE_MODEL_QWEN_PLUS"
    echo "  Qwen3.5-Flash: $DASHSCOPE_MODEL_QWEN_FLASH"
    echo "  Qwen3.6-Max: $DASHSCOPE_MODEL_QWEN_MAX (可能不可用)"
    echo "  AI Assistant 代理: $DASHSCOPE_ADAPTER_URL"

    echo ""
    echo -e "${YELLOW}3. 代理状态:${NC}"
    if curl -fsS "${DASHSCOPE_ADAPTER_URL}/health" >/dev/null 2>&1; then
        echo "  ${GREEN}✓${NC} 本地适配器已运行"
    else
        echo "  ${YELLOW}⚠${NC} 本地适配器未运行"
    fi

    echo ""
    echo -e "${YELLOW}4. 使用建议:${NC}"
    if [ -z "$DEEPSEEK_API_KEY" ]; then
        echo "  ${YELLOW}⚠${NC} DeepSeek API 密钥未设置，相关备用模型不可用"
    else
        echo "  ${GREEN}✓${NC} DeepSeek 配置完整"
    fi
    echo "  ${GREEN}✓${NC} Qwen 默认通过本地适配器连接 DashScope"

    echo ""
    echo -e "${YELLOW}5. 环境变量示例:${NC}"
    cat << EOF
  export DASHSCOPE_API_KEY="你的阿里云密钥"
  export DEEPSEEK_API_KEY="你的DeepSeek密钥"

  alias claude='/Users/frankie/claude-code-setup/claude-dual-model.sh'
  alias claude-dual='/Users/frankie/claude-code-setup/claude-dual-model.sh'
  alias claude-max='/Users/frankie/claude-code-setup/claude-qwen-alt.sh -m qwen3.6-plus'
  alias claude-dev='/Users/frankie/claude-code-setup/claude-dual-model.sh 2'
  alias claude-fix='/Users/frankie/claude-code-setup/claude-dual-model.sh 1'
  alias claude-zh='/Users/frankie/claude-code-setup/claude-qwen-alt.sh'
EOF
}

export_config() {
    local model_type="$1"

    case "$model_type" in
        "deepseek-chat")
            export LLM_BASE_URL="$DEEPSEEK_BASE_URL"
            export LLM_MODEL="$DEEPSEEK_CHAT_MODEL"
            export LLM_AUTH_TOKEN="${DEEPSEEK_API_KEY:-$ALIYUN_API_KEY}"
            ;;
        "deepseek-reasoner")
            export LLM_BASE_URL="$DEEPSEEK_BASE_URL"
            export LLM_MODEL="$DEEPSEEK_REASONER_MODEL"
            export LLM_AUTH_TOKEN="${DEEPSEEK_API_KEY:-$ALIYUN_API_KEY}"
            ;;
        "deepseek-r1")
            export LLM_BASE_URL="$BAILIAN_PRO_BASE_URL"
            export LLM_MODEL="$BAILIAN_PRO_MODEL_DEEPSEEK_R1"
            export LLM_AUTH_TOKEN="${DASHSCOPE_API_KEY:-$ALIYUN_API_KEY}"
            ;;
        "qwen3.6-plus"|"qwen3.5-flash"|"qwen3.5-plus")
            ensure_dashscope_adapter || return 1
            export LLM_BASE_URL="$DASHSCOPE_ADAPTER_URL"
            export LLM_MODEL="$DASHSCOPE_ADAPTER_MODEL"
            export LLM_AUTH_TOKEN="${DASHSCOPE_API_KEY:-$ALIYUN_API_KEY}"
            ;;
        *)
            log_error "未知模型类型: $model_type"
            return 1
            ;;
    esac

    export AI_CODE_BARE=1
    export AI_CODE_SKIP_KEYCHAIN=1
    export LLM_API_KEY="$LLM_AUTH_TOKEN"

    log_success "已配置模型: $model_type"
    log_info "端点: $LLM_BASE_URL"
    log_info "模型: $LLM_MODEL"
}

main() {
    case "${1:-}" in
        check)
            check_config
            ;;
        export)
            if [ -z "${2:-}" ]; then
                log_error "请指定模型名"
                return 1
            fi
            export_config "$2"
            ;;
        *)
            echo -e "${CYAN}AI Assistant 配置管理器${NC}"
            echo ""
            echo "使用方法:"
            echo "  ./claude-config.sh check"
            echo "  ./claude-config.sh export MODEL"
            echo ""
            echo "可用模型:"
            echo "  deepseek-chat"
            echo "  deepseek-reasoner"
            echo "  deepseek-r1"
            echo "  qwen3.6-plus"
            echo "  qwen3.5-flash"
            echo "  qwen3.5-plus"
            ;;
    esac
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
