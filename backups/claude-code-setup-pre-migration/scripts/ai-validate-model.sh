#!/bin/bash
# =============================================================================
# AI 模型验证脚本 - 深度测试单个模型的连接、响应和质量
# 用法: bash scripts/ai-validate-model.sh <model_name> [profile]
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_DIR="$PROJECT_DIR/config/ai-config"

# ---------------------------------------------------------------------------
# 颜色定义
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------
pass() { echo -e "  ${GREEN}✅ [PASS]${NC} $1"; }
fail() { echo -e "  ${RED}❌ [FAIL]${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠️  [WARN]${NC} $1"; }
info() { echo -e "  ${BLUE}ℹ️  [INFO]${NC} $1"; }
section() { echo -e "\n${CYAN}${BOLD}━━━ $1 ━━━${NC}"; }

# ---------------------------------------------------------------------------
# 加载密钥
# ---------------------------------------------------------------------------
load_secrets() {
    if [ -f "$HOME/.config/secret-env/load-keychain-secrets.sh" ]; then
        source "$HOME/.config/secret-env/load-keychain-secrets.sh"
    fi
}

# ---------------------------------------------------------------------------
# 解析模型所属 Provider
# ---------------------------------------------------------------------------
get_provider() {
    local model="$1"
    case "$model" in
        qwen-*|qwen3*) echo "bailian" ;;
        deepseek-*)    echo "deepseek" ;;
        claude-*)      echo "anthropic" ;;
        *)             echo "unknown" ;;
    esac
}

# ---------------------------------------------------------------------------
# 获取 API Key
# ---------------------------------------------------------------------------
get_api_key() {
    local provider="$1"
    case "$provider" in
        bailian)   echo "${DASHSCOPE_API_KEY:-}" ;;
        deepseek)  echo "${DEEPSEEK_API_KEY:-}" ;;
        anthropic) echo "${ANTHROPIC_API_KEY:-}" ;;
        *)         echo "" ;;
    esac
}

# ---------------------------------------------------------------------------
# 测试 1: API Key 配置检查
# ---------------------------------------------------------------------------
test_api_key() {
    local provider="$1"
    local api_key="$2"

    section "测试 1: API Key 检查"

    if [ -z "$api_key" ]; then
        fail "API Key 未设置 (provider: $provider)"
        info "请通过 Keychain 或环境变量设置对应的 API Key"
        case "$provider" in
            bailian)   info "Keychain service: env/DASHSCOPE_API_KEY" ;;
            deepseek)  info "Keychain service: env/DEEPSEEK_API_KEY" ;;
            anthropic) info "Keychain service: env/ANTHROPIC_API_KEY" ;;
        esac
        return 1
    fi

    local masked="${api_key:0:8}...${api_key: -4}"
    pass "API Key 已配置: $masked"
    return 0
}

# ---------------------------------------------------------------------------
# 测试 2: 直连百炼 OpenAI 兼容 API
# ---------------------------------------------------------------------------
test_bailian_openai() {
    local model="$1"
    local api_key="$2"
    local base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    local timeout="${3:-30}"

    section "测试 2: 直连百炼 OpenAI 兼容 API"

    info "模型: $model"
    info "端点: $base_url/chat/completions"

    local start_time=$(date +%s)
    local response
    response=$(curl -s --connect-timeout 10 --max-time "$timeout" \
        "$base_url/chat/completions" \
        -H "Authorization: Bearer $api_key" \
        -H "Content-Type: application/json" \
        -d "{
            \"model\": \"$model\",
            \"messages\": [{\"role\": \"user\", \"content\": \"请用中文简短回答：1+1等于几？只回答数字。\"}],
            \"max_tokens\": 50,
            \"temperature\": 0.5
        }" 2>/dev/null)
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    if [ -z "$response" ]; then
        fail "无响应 (超时: ${timeout}s)"
        return 1
    fi

    # 检查错误
    local error_msg
    error_msg=$(echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('error',{}).get('message',''))" 2>/dev/null || echo "")
    if [ -n "$error_msg" ]; then
        fail "API 返回错误: $error_msg"
        return 1
    fi

    # 检查响应
    local content finish_reason prompt_tokens completion_tokens
    content=$(echo "$response" | python3 -c "
import sys, json
d = json.load(sys.stdin)
c = d.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
print(c)
" 2>/dev/null || echo "")

    finish_reason=$(echo "$response" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('choices', [{}])[0].get('finish_reason', ''))
" 2>/dev/null || echo "")

    prompt_tokens=$(echo "$response" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('usage', {}).get('prompt_tokens', 0))
" 2>/dev/null || echo "0")

    completion_tokens=$(echo "$response" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('usage', {}).get('completion_tokens', 0))
" 2>/dev/null || echo "0")

    if [ -n "$content" ]; then
        pass "响应正常: \"$content\""
        pass "完成原因: $finish_reason"
        pass "Token 使用: 输入=$prompt_tokens, 输出=$completion_tokens"
        pass "响应时间: ${duration}s"
        return 0
    else
        fail "响应内容为空"
        info "原始响应: $(echo "$response" | head -c 300)"
        return 1
    fi
}

# ---------------------------------------------------------------------------
# 测试 3: 通过 DashScope 适配器
# ---------------------------------------------------------------------------
test_via_adapter() {
    local model="$1"
    local api_key="$2"
    local adapter_url="http://127.0.0.1:8080"
    local timeout="${3:-30}"

    section "测试 3: 通过 DashScope 适配器"

    # 检查适配器是否运行
    local health
    health=$(curl -s --connect-timeout 5 "$adapter_url/health" 2>/dev/null || echo "")
    if [ -z "$health" ]; then
        fail "适配器未运行于 $adapter_url"
        info "启动: cd $PROJECT_DIR && python3 dashscope-adapter.py &"
        return 1
    fi
    pass "适配器运行正常"

    info "模型: $model"
    info "端点: $adapter_url/v1/messages (流式=false)"

    local start_time=$(date +%s)
    local response
    response=$(curl -s --connect-timeout 10 --max-time "$timeout" \
        "$adapter_url/v1/messages" \
        -X POST \
        -H "Content-Type: application/json" \
        -H "x-api-key: $api_key" \
        -d "{
            \"model\": \"$model\",
            \"messages\": [{\"role\": \"user\", \"content\": \"请用中文简短回答：1+1等于几？只回答数字。\"}],
            \"max_tokens\": 50,
            \"stream\": false
        }" 2>/dev/null)
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    if [ -z "$response" ]; then
        fail "无响应 (超时: ${timeout}s)"
        return 1
    fi

    # 检查错误
    local error_type
    error_type=$(echo "$response" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('error', {}).get('type', ''))
" 2>/dev/null || echo "")

    if [ "$error_type" = "error" ] || [ -n "$(echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('type',''))" 2>/dev/null | grep -i error)" ]; then
        local error_msg
        error_msg=$(echo "$response" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('error', {}).get('message', 'unknown'))
" 2>/dev/null || echo "unknown")
        fail "适配器返回错误: $error_msg"
        info "原始响应: $(echo "$response" | head -c 300)"
        return 1
    fi

    # 检查内容
    local content returned_model input_tokens output_tokens
    content=$(echo "$response" | python3 -c "
import sys, json
d = json.load(sys.stdin)
blocks = d.get('content', [])
texts = [b.get('text','') for b in blocks if b.get('type') == 'text']
print('\n'.join(texts))
" 2>/dev/null || echo "")

    returned_model=$(echo "$response" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('model', '?'))
" 2>/dev/null || echo "?")

    input_tokens=$(echo "$response" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('usage', {}).get('input_tokens', 0))
" 2>/dev/null || echo "0")

    output_tokens=$(echo "$response" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('usage', {}).get('output_tokens', 0))
" 2>/dev/null || echo "0")

    if [ -n "$content" ]; then
        pass "响应正常: \"$content\""
        pass "返回模型: $returned_model"
        pass "Token 使用: 输入=$input_tokens, 输出=$output_tokens"
        pass "响应时间: ${duration}s"
        return 0
    else
        fail "响应内容为空"
        info "原始响应: $(echo "$response" | head -c 300)"
        return 1
    fi
}

# ---------------------------------------------------------------------------
# 测试 4: 流式响应 (通过适配器)
# ---------------------------------------------------------------------------
test_streaming() {
    local model="$1"
    local api_key="$2"
    local adapter_url="http://127.0.0.1:8080"
    local timeout="${3:-30}"

    section "测试 4: 流式响应测试"

    # 检查适配器
    local health
    health=$(curl -s --connect-timeout 5 "$adapter_url/health" 2>/dev/null || echo "")
    if [ -z "$health" ]; then
        fail "适配器未运行，跳过流式测试"
        return 1
    fi

    info "模型: $model"
    info "端点: $adapter_url/v1/messages (流式=true)"

    local stream_file
    stream_file=$(mktemp /tmp/ai-stream-test-XXXXXX.txt)

    curl -s --connect-timeout 10 --max-time "$timeout" \
        "$adapter_url/v1/messages" \
        -X POST \
        -H "Content-Type: application/json" \
        -H "x-api-key: $api_key" \
        -d "{
            \"model\": \"$model\",
            \"messages\": [{\"role\": \"user\", \"content\": \"请用中文列举3种水果。\"}],
            \"max_tokens\": 100,
            \"stream\": true
        }" > "$stream_file" 2>/dev/null &
    local curl_pid=$!
    sleep 10
    kill $curl_pid 2>/dev/null || true

    local event_count content_deltas
    event_count=$(grep -c "data:" "$stream_file" 2>/dev/null || echo "0")
    content_deltas=$(grep -c "content_block_delta" "$stream_file" 2>/dev/null || echo "0")
    has_message_start=$(grep -c "message_start" "$stream_file" 2>/dev/null || echo "0")
    has_message_stop=$(grep -c "message_stop" "$stream_file" 2>/dev/null || echo "0")

    rm -f "$stream_file"

    local result=0

    if [ "$has_message_start" -gt 0 ]; then
        pass "收到 message_start 事件"
    else
        fail "缺少 message_start 事件"
        result=1
    fi

    if [ "$content_deltas" -gt 0 ]; then
        pass "收到 $content_deltas 个 content_block_delta 事件"
    else
        fail "缺少 content_block_delta 事件"
        result=1
    fi

    if [ "$has_message_stop" -gt 0 ]; then
        pass "收到 message_stop 事件"
    else
        warn "缺少 message_stop 事件 (可能被中断)"
    fi

    if [ "$event_count" -gt 2 ]; then
        pass "总共收到 $event_count 个 SSE 事件"
    else
        fail "SSE 事件数量不足: $event_count"
        result=1
    fi

    return $result
}

# ---------------------------------------------------------------------------
# 测试 5: 质量验证 - 简单推理
# ---------------------------------------------------------------------------
test_reasoning() {
    local model="$1"
    local api_key="$2"
    local adapter_url="http://127.0.0.1:8080"
    local timeout="${3:-30}"

    section "测试 5: 推理能力验证"

    # 检查适配器
    local health
    health=$(curl -s --connect-timeout 5 "$adapter_url/health" 2>/dev/null || echo "")
    if [ -z "$health" ]; then
        fail "适配器未运行，跳过推理测试"
        return 1
    fi

    info "测试问题: 一个房间里有3盏灯，外面有3个开关，你只能进房间一次，如何确定哪个开关控制哪盏灯？"

    local response
    response=$(curl -s --connect-timeout 10 --max-time "$timeout" \
        "$adapter_url/v1/messages" \
        -X POST \
        -H "Content-Type: application/json" \
        -H "x-api-key: $api_key" \
        -d "{
            \"model\": \"$model\",
            \"messages\": [{\"role\": \"user\", \"content\": \"一个房间里有3盏灯，外面有3个开关，你只能进房间一次，如何确定哪个开关控制哪盏灯？请用中文简短回答。\"}],
            \"max_tokens\": 300,
            \"stream\": false
        }" 2>/dev/null)

    if [ -z "$response" ]; then
        fail "无响应"
        return 1
    fi

    local content
    content=$(echo "$response" | python3 -c "
import sys, json
d = json.load(sys.stdin)
blocks = d.get('content', [])
texts = [b.get('text','') for b in blocks if b.get('type') == 'text']
print('\n'.join(texts))
" 2>/dev/null || echo "")

    if [ -n "$content" ]; then
        pass "推理测试通过"
        echo -e "\n  ${CYAN}回答内容:${NC}"
        echo "  ┌─────────────────────────────────────────"
        # 缩进回答
        echo "$content" | sed 's/^/  │ /'
        echo "  └─────────────────────────────────────────"
        echo ""
        return 0
    else
        fail "推理测试失败"
        info "原始响应: $(echo "$response" | head -c 300)"
        return 1
    fi
}

# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
main() {
    local model="${1:-}"
    if [ -z "$model" ]; then
        echo -e "${RED}用法: $0 <model_name> [profile]${NC}"
        echo ""
        echo "可用模型:"
        echo "  百炼: qwen-max, qwen-plus, qwen-turbo, qwen-coder-plus, qwen-long, qwen3-235B-A22B, qwen3.6-plus"
        echo "  DeepSeek: deepseek-chat, deepseek-coder"
        exit 1
    fi

    local profile="${2:-}"

    echo -e "${BOLD}${BLUE}╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${BLUE}║${NC}  ${BOLD}AI 模型深度验证${NC}                                    ${BOLD}${BLUE}║${NC}"
    echo -e "${BOLD}${BLUE}╚══════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  模型: ${BOLD}$model${NC}"
    [ -n "$profile" ] && echo -e "  配置: ${BOLD}$profile${NC}"
    echo ""

    # 加载密钥
    load_secrets

    # 获取 provider
    local provider
    provider=$(get_provider "$model")
    info "Provider: $provider"

    # 获取 API Key
    local api_key
    api_key=$(get_api_key "$provider")

    # 测试计数器
    local total=0 passed=0 failed=0

    # 测试 1: API Key
    total=$((total + 1))
    if test_api_key "$provider" "$api_key"; then
        passed=$((passed + 1))
    else
        failed=$((failed + 1))
        echo -e "\n${RED}⚠️  API Key 无效，跳过后续测试${NC}"
        exit 1
    fi

    # 测试 2-5 根据 provider 执行
    case "$provider" in
        bailian)
            # 测试直连
            total=$((total + 1))
            if test_bailian_openai "$model" "$api_key"; then
                passed=$((passed + 1))
            else
                failed=$((failed + 1))
            fi

            # 测试通过适配器
            total=$((total + 1))
            if test_via_adapter "$model" "$api_key"; then
                passed=$((passed + 1))
            else
                failed=$((failed + 1))
            fi

            # 测试流式
            total=$((total + 1))
            if test_streaming "$model" "$api_key"; then
                passed=$((passed + 1))
            else
                failed=$((failed + 1))
            fi

            # 测试推理
            total=$((total + 1))
            if test_reasoning "$model" "$api_key"; then
                passed=$((passed + 1))
            else
                failed=$((failed + 1))
            fi
            ;;
        deepseek)
            # DeepSeek 直连测试 (OpenAI 兼容)
            total=$((total + 1))
            section "测试 2: DeepSeek OpenAI 兼容 API"
            local base_url="https://api.deepseek.com/v1"
            local response
            response=$(curl -s --connect-timeout 10 --max-time 30 \
                "$base_url/chat/completions" \
                -H "Authorization: Bearer $api_key" \
                -H "Content-Type: application/json" \
                -d "{
                    \"model\": \"$model\",
                    \"messages\": [{\"role\": \"user\", \"content\": \"请用中文简短回答：1+1等于几？只回答数字。\"}],
                    \"max_tokens\": 50
                }" 2>/dev/null)

            if echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'choices' in d" 2>/dev/null; then
                local content
                content=$(echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['choices'][0]['message']['content'].strip())" 2>/dev/null)
                pass "DeepSeek API 响应正常: \"$content\""
                passed=$((passed + 1))
            else
                fail "DeepSeek API 响应异常"
                info "响应: $(echo "$response" | head -c 300)"
                failed=$((failed + 1))
            fi

            # 测试 Anthropic 兼容端点 (Claude Code 需要)
            total=$((total + 1))
            section "测试 3: DeepSeek Anthropic 兼容端点"
            local anthropic_url="https://api.deepseek.com/anthropic/v1/messages"
            response=$(curl -s --connect-timeout 10 --max-time 30 \
                "$anthropic_url" \
                -X POST \
                -H "x-api-key: $api_key" \
                -H "anthropic-version: 2023-06-01" \
                -H "content-type: application/json" \
                -d "{
                    \"model\": \"$model\",
                    \"messages\": [{\"role\": \"user\", \"content\": \"OK\"}],
                    \"max_tokens\": 50
                }" 2>/dev/null)

            if echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('content') or d.get('type') == 'message'" 2>/dev/null; then
                pass "Anthropic 兼容端点正常"
                passed=$((passed + 1))
            else
                fail "Anthropic 兼容端点异常"
                info "响应: $(echo "$response" | head -c 300)"
                failed=$((failed + 1))
            fi
            ;;
        *)
            fail "未知 Provider: $provider"
            exit 1
            ;;
    esac

    # 总结
    echo ""
    echo -e "${BOLD}${BLUE}╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${BLUE}║${NC}  ${BOLD}测试总结${NC}                                            ${BOLD}${BLUE}║${NC}"
    echo -e "${BOLD}${BLUE}╚══════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  总计: ${BOLD}$total${NC} 项测试"
    echo -e "  通过: ${GREEN}$passed${NC}"
    echo -e "  失败: ${RED}$failed${NC}"
    echo ""

    if [ $failed -eq 0 ]; then
        echo -e "  ${GREEN}${BOLD}✅ 模型 $model 验证通过！${NC}"
    else
        echo -e "  ${RED}${BOLD}❌ 模型 $model 验证失败，请检查配置${NC}"
    fi

    exit $failed
}

main "$@"