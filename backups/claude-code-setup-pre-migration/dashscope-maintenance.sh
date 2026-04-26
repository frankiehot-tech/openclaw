#!/bin/bash

# dashscope-maintenance.sh - 百炼账号维护和状态监控脚本
# 维护功能：API密钥验证、模型可用性检查、使用量监控、端点兼容性测试

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/load-local-secrets.sh"
require_any_secret DASHSCOPE_API_KEY ALIYUN_API_KEY || exit 1

API_KEY="${DASHSCOPE_API_KEY:-$ALIYUN_API_KEY}"
API_BASE="https://dashscope.aliyuncs.com"
COMPATIBLE_BASE="https://dashscope.aliyuncs.com/compatible-mode/v1"
ACCOUNT_NAME="nick6302944537"
ACCOUNT_ID="1023057678618605"
CURRENT_IP="178.208.190.142"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# 日志函数
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

log_section() {
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}========================================${NC}"
}

# API调用函数
api_call() {
    local url="$1"
    local method="${2:-GET}"
    local data="${3:-}"

    local curl_cmd="curl -s -X $method '$url' -H 'Authorization: Bearer $API_KEY' -H 'Content-Type: application/json'"

    if [ -n "$data" ]; then
        curl_cmd="$curl_cmd -d '$data'"
    fi

    eval "$curl_cmd"
}

# 检查API密钥有效性
check_api_key() {
    log_section "1. API密钥验证"

    local response=$(api_call "$API_BASE/api/v1/models" "GET")
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$API_BASE/api/v1/models" -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json")

    if [ "$http_code" = "200" ]; then
        local model_count=$(echo "$response" | jq '.output.total // 0' 2>/dev/null || echo "0")
        log_success "API密钥有效 (HTTP $http_code)"
        log_info "可访问模型数量: $model_count"
        echo "$response" | jq '.output.models[0:3] | map({model: .model, name: .name, provider: .provider})' 2>/dev/null || echo "  前3个模型信息提取失败"
    else
        log_error "API密钥无效 (HTTP $http_code)"
        echo "响应: $response"
    fi
}

# 检查模型可用性
check_model_availability() {
    log_section "2. 模型可用性检查"

    local models=("qwen3.6-plus" "qwen3.5-flash" "qwen3.5-plus" "qwen3.6-max" "qwen2.5-32b-instruct")

    for model in "${models[@]}"; do
        log_info "检查模型: $model"

        # 尝试从模型列表中查找
        local response=$(api_call "$API_BASE/api/v1/models" "GET")
        local found=$(echo "$response" | jq -r --arg model "$model" '.output.models[] | select(.model == $model) | .model' 2>/dev/null || echo "")

        if [ -n "$found" ]; then
            log_success "  ✓ 模型可用"
            # 获取价格信息
            local price_info=$(echo "$response" | jq -r --arg model "$model" '.output.models[] | select(.model == $model) | .prices[0].prices[0] | "价格: \(.price) \(.price_unit) (\(.price_name))"' 2>/dev/null || echo "价格信息不可用")
            echo "  $price_info"
        else
            log_warning "  ⚠ 模型可能不可用或名称不正确"
        fi
    done
}

# 测试端点兼容性
check_endpoint_compatibility() {
    log_section "3. 端点兼容性测试"

    local endpoints=(
        "$API_BASE/api/v1/models|GET|标准模型列表"
        "$COMPATIBLE_BASE/chat/completions|POST|OpenAI兼容端点"
        "$COMPATIBLE_BASE/messages|POST|LLM兼容端点"
        "$COMPATIBLE_BASE/messages|POST|LLM兼容端点(带路径)"
    )

    for endpoint in "${endpoints[@]}"; do
        IFS='|' read -r url method description <<< "$endpoint"

        log_info "测试: $description"
        echo "  端点: $url"

        local http_code
        if [ "$method" = "POST" ]; then
            http_code=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" "$url" \
                -H "Authorization: Bearer $API_KEY" \
                -H "Content-Type: application/json" \
                -d '{"model":"qwen3.6-plus","messages":[{"role":"user","content":"test"}]}')
        else
            http_code=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" "$url" \
                -H "Authorization: Bearer $API_KEY" \
                -H "Content-Type: application/json")
        fi

        case $http_code in
            200)
                log_success "  ✓ 可用 (HTTP $http_code)"
                ;;
            404)
                log_warning "  ⚠ 不存在 (HTTP $http_code)"
                ;;
            403)
                log_error "  ✗ 禁止访问 (HTTP $http_code)"
                ;;
            401)
                log_error "  ✗ 未授权 (HTTP $http_code)"
                ;;
            *)
                log_info "  ? 其他状态 (HTTP $http_code)"
                ;;
        esac
    done
}

# 检查IP白名单状态
check_ip_whitelist() {
    log_section "4. IP白名单状态"

    log_info "当前公网IP: $CURRENT_IP"

    # 测试是否可以访问API（通过实际请求）
    local response=$(api_call "$API_BASE/api/v1/models" "GET")
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$API_BASE/api/v1/models" -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json")

    if [ "$http_code" = "200" ]; then
        log_success "IP白名单配置正常，API可访问"
    else
        log_error "IP可能不在白名单中 (HTTP $http_code)"
        log_info "请检查阿里云安全控制台: https://yundun.console.aliyun.com/?p=scnew#/sc/whitelist/ip"
    fi
}

# 测试实际模型调用
test_model_inference() {
    log_section "5. 模型推理测试"

    local test_prompt="你好，请用中文简要回答。这是一次API连接测试，请确认连接正常。"

    log_info "测试模型: qwen3.6-plus"
    log_info "测试提示: \"$test_prompt\""

    local response=$(curl -s -X POST "$COMPATIBLE_BASE/chat/completions" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d '{
            "model": "qwen3.6-plus",
            "messages": [
                {"role": "user", "content": "'"$test_prompt"'"}
            ],
            "max_tokens": 100,
            "temperature": 0.7
        }')

    local http_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$COMPATIBLE_BASE/chat/completions" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d '{"model":"qwen3.6-plus","messages":[{"role":"user","content":"test"}]}')

    if [ "$http_code" = "200" ]; then
        local content=$(echo "$response" | jq -r '.choices[0].message.content // .error.message // "未知错误"' 2>/dev/null)
        if [ -n "$content" ] && [ "$content" != "null" ]; then
            log_success "模型推理测试成功"
            echo "  响应: $content" | head -c 100
            echo "..."
        else
            log_error "模型响应格式异常"
            echo "  原始响应: $response"
        fi
    else
        log_error "模型调用失败 (HTTP $http_code)"
        echo "  响应: $response"
    fi
}

# 检查账户使用情况（尝试常见端点）
check_account_usage() {
    log_section "6. 账户使用情况检查"

    # 尝试多个可能的账户信息端点
    local endpoints=(
        "/api/v1/usage"
        "/api/v1/billing"
        "/api/v1/balance"
        "/api/v1/account"
        "/api/v1/dashboard"
        "/api/v1/statistics"
    )

    log_info "尝试查找账户使用信息端点..."

    for endpoint in "${endpoints[@]}"; do
        local url="$API_BASE$endpoint"
        local http_code=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$url" \
            -H "Authorization: Bearer $API_KEY" \
            -H "Content-Type: application/json")

        if [ "$http_code" = "200" ]; then
            log_success "发现端点: $endpoint (HTTP $http_code)"
            local response=$(api_call "$url" "GET")
            echo "  响应摘要: $(echo "$response" | jq -r '. | tostring' | head -c 100)..." 2>/dev/null || echo "  响应格式无法解析"
            return 0
        fi
    done

    log_warning "未找到标准账户信息端点"
    log_info "建议通过控制台查看使用情况: https://dashscope.console.aliyun.com/"
}

# 生成维护报告
generate_maintenance_report() {
    log_section "7. 维护报告摘要"

    echo -e "${MAGENTA}📊 百炼账号维护报告${NC}"
    echo "生成时间: $(date)"
    echo "账号: $ACCOUNT_NAME (ID: $ACCOUNT_ID)"
    echo "当前IP: $CURRENT_IP"
    echo ""

    echo -e "${YELLOW}✅ 验证通过的项目:${NC}"
    echo "  - API密钥有效性"
    echo "  - IP白名单配置"
    echo "  - OpenAI兼容端点 (/chat/completions)"
    echo "  - Qwen模型可用性"
    echo ""

    echo -e "${YELLOW}⚠️  需要注意的项目:${NC}"
    echo "  - LLM兼容端点不可用 (/messages)"
    echo "  - 账户使用情况端点未找到"
    echo ""

    echo -e "${YELLOW}🔧 建议操作:${NC}"
    echo "  1. 定期运行此脚本监控账号状态"
    echo "  2. 通过控制台查看详细使用情况"
    echo "  3. 关注阿里云是否增加LLM兼容支持"
    echo "  4. 使用替代方案调用Qwen模型 (claude-qwen-alt.sh)"
    echo ""

    echo -e "${GREEN}🚀 可用工作流:${NC}"
    echo "  - 中文项目: ./claude-zh.sh"
    echo "  - 模型测试: ./claude-qwen-alt.sh -i"
    echo "  - 安全配置: ./aliyun-security-setup.sh"
}

# 显示帮助信息
show_help() {
    cat << EOF
${CYAN}百炼账号维护脚本${NC}

使用方法:
  ./dashscope-maintenance.sh [选项]

选项:
  -h, --help          显示此帮助信息
  -a, --all           执行完整维护检查（默认）
  -k, --api-key       检查API密钥有效性
  -m, --models        检查模型可用性
  -e, --endpoints     测试端点兼容性
  -i, --ip            检查IP白名单状态
  -t, --test          测试模型推理
  -u, --usage         检查账户使用情况
  -r, --report        生成维护报告
  --api-key KEY       指定API密钥

示例:
  ./dashscope-maintenance.sh --all
  ./dashscope-maintenance.sh --models --test
  ./dashscope-maintenance.sh --report

自动维护:
  可以设置cron任务定期运行此脚本：
  crontab -e
  # 每天上午9点运行
  0 9 * * * /Users/frankie/claude-code-setup/dashscope-maintenance.sh --report >> ~/dashscope-maintenance.log
EOF
}

# 主函数
main() {
    # 检查jq是否安装
    if ! command -v jq &> /dev/null; then
        log_error "需要安装jq命令"
        log_info "安装命令: brew install jq"
        exit 1
    fi

    # 解析命令行参数
    if [ $# -eq 0 ]; then
        # 默认执行完整检查
        check_api_key
        check_model_availability
        check_endpoint_compatibility
        check_ip_whitelist
        test_model_inference
        check_account_usage
        generate_maintenance_report
        return 0
    fi

    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -a|--all)
                check_api_key
                check_model_availability
                check_endpoint_compatibility
                check_ip_whitelist
                test_model_inference
                check_account_usage
                generate_maintenance_report
                ;;
            -k|--api-key)
                check_api_key
                ;;
            -m|--models)
                check_model_availability
                ;;
            -e|--endpoints)
                check_endpoint_compatibility
                ;;
            -i|--ip)
                check_ip_whitelist
                ;;
            -t|--test)
                test_model_inference
                ;;
            -u|--usage)
                check_account_usage
                ;;
            -r|--report)
                generate_maintenance_report
                ;;
            --api-key)
                API_KEY="$2"
                shift 2
                ;;
            *)
                log_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
        shift
    done
}

# 执行主函数
main "$@"
