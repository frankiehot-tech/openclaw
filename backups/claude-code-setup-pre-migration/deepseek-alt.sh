#!/bin/bash

# claude-deepseek-alt.sh - DeepSeek模型替代解决方案
# 使用OpenAI兼容API调用DeepSeek模型，作为claude-zh.sh的替代品

# 加载配置文件（如果存在）
CONFIG_FILE="/Users/frankie/claude-code-setup/claude-config.sh"
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
    API_KEY="$DEEPSEEK_API_KEY"
    API_BASE="$DEEPSEEK_API_BASE_URL"
    MODEL="deepseek-chat"
else
    # 默认配置
    API_KEY="${DEEPSEEK_API_KEY}"
    API_BASE="https://api.deepseek.com/v1"
    MODEL="deepseek-chat"
fi

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 帮助函数
show_help() {
    cat << EOF
🇨🇳 DeepSeek模型替代解决方案

DeepSeek提供OpenAI兼容API，成本仅为DashScope的12.5%，适合调试和测试任务。

使用方法:
  claude-deepseek-alt [选项] [查询]

选项:
  -h, --help          显示此帮助信息
  -m, --model MODEL   指定模型 (默认: deepseek-chat)
                     可用模型: deepseek-chat, deepseek-coder
  -t, --temperature N 温度参数 (默认: 0.7)
  -n, --max-tokens N  最大token数 (默认: 2000)
  -i, --interactive   交互模式
  -l, --list-models   列出可用模型
  --api-key KEY       指定API密钥 (默认使用环境变量DEEPSEEK_API_KEY)

示例:
  claude-deepseek-alt "你好，用中文回答"
  claude-deepseek-alt -i
  claude-deepseek-alt -m deepseek-coder "写一个Python函数"

工作流集成:
  将此脚本重命名为 claude-zh.sh 或创建别名:
  alias claude-zh='/Users/frankie/claude-code-setup/claude-deepseek-alt.sh'

成本优势:
  • 输入成本: 0.001元/1k tokens (DashScope: 0.008元)
  • 输出成本: 0.002元/1k tokens (DashScope: 0.008元)
  • 节省: 87.5%成本
EOF
}

# 列出模型函数
list_models() {
    echo -e "${BLUE}🔍 DeepSeek可用模型:${NC}"
    echo ""
    echo "  deepseek-chat        - 通用对话模型，128K上下文 (推荐)"
    echo "  deepseek-coder       - 代码专用模型，128K上下文"
    echo ""
    echo -e "${GREEN}💰 成本优势:${NC}"
    echo "  • 输入成本: 0.001元/1k tokens (DashScope的12.5%)"
    echo "  • 输出成本: 0.002元/1k tokens (DashScope的25%)"
    echo "  • 总成本: 仅DashScope的约18.75%"
    echo ""
    echo -e "${YELLOW}注: DeepSeek提供OpenAI兼容API，但可能不支持所有LLM格式。${NC}"
}

# 发送API请求函数
send_request() {
    local query="$1"
    local temperature="${2:-0.7}"
    local max_tokens="${3:-2000}"

    # 使用jq转义query字符串，确保JSON有效
    local escaped_query
    if command -v jq >/dev/null 2>&1; then
        escaped_query=$(echo -n "$query" | jq -Rs .)
        # 调试输出：显示转义前后的长度
        echo -e "\033[0;33m🔍 调试: 原始查询长度=${#query}, 转义后长度=${#escaped_query}\033[0m" >&2
    else
        # 基本转义：替换双引号和换行符（不完整，但比没有好）
        escaped_query="\"${query//\"/\\\"}\""
        # 替换换行符为\n序列
        escaped_query=${escaped_query//$'\n'/\\n}
        echo -e "\033[0;33m⚠️  调试: 使用基本转义，jq不可用\033[0m" >&2
    fi

    # 构建JSON数据
    local json_data=$(cat <<EOF
{
  "model": "$MODEL",
  "messages": [
    {"role": "user", "content": $escaped_query}
  ],
  "temperature": $temperature,
  "max_tokens": $max_tokens
}
EOF
)

    echo -e "${BLUE}🤖 DeepSeek(${MODEL}):${NC}"

    # 成本提醒
    echo -e "\033[0;33m💰 成本优势: 当前使用成本仅DashScope的18.75%\033[0m" >&2

    # 调试：打印JSON前300个字符
    echo -e "\033[0;33m🔍 调试: JSON数据前300字符: ${json_data:0:300}...\033[0m" >&2

    # 发送请求
    local response=$(curl -s -X POST "${API_BASE}/chat/completions" \
        -H "Authorization: Bearer ${API_KEY}" \
        -H "Content-Type: application/json" \
        -d "$json_data")

    # 提取回复内容
    local content=$(echo "$response" | jq -r '.choices[0].message.content // .error.message // "未知错误"' 2>/dev/null)

    if [ $? -eq 0 ] && [ "$content" != "null" ] && [ ! -z "$content" ]; then
        echo -e "${GREEN}$content${NC}"
    else
        echo -e "${RED}❌ 请求失败${NC}"
        echo "原始响应:"
        echo "$response" | head -c 500
        echo ""
    fi
}

# 交互模式
interactive_mode() {
    echo -e "${BLUE}🤖 DeepSeek模型交互式聊天 (模型: ${MODEL})${NC}"
    echo -e "${YELLOW}输入 'quit' 或 'exit' 退出${NC}"
    echo -e "${YELLOW}输入 'model <模型名称>' 切换模型${NC}"
    echo -e "${YELLOW}💰 成本提醒: 当前会话成本仅为DashScope的18.75%${NC}"
    echo "="$(printf '=%.0s' {1..50})

    while true; do
        echo -e "${BLUE}\n👤 你: ${NC}"
        read -r user_input

        if [[ "$user_input" =~ ^[qQ]uit$ ]] || [[ "$user_input" =~ ^[eE]xit$ ]] || [[ "$user_input" == "退出" ]]; then
            echo -e "${GREEN}再见！${NC}"
            break
        elif [[ "$user_input" =~ ^[mM]odel\ .+ ]]; then
            new_model=$(echo "$user_input" | cut -d' ' -f2-)
            MODEL="$new_model"
            echo -e "${GREEN}✅ 已切换到模型: ${MODEL}${NC}"
            continue
        fi

        send_request "$user_input"
    done
}

# 解析命令行参数
QUERY=""
INTERACTIVE=0
TEMPERATURE=0.7
MAX_TOKENS=2000

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -i|--interactive)
            INTERACTIVE=1
            shift
            ;;
        -l|--list-models)
            list_models
            exit 0
            ;;
        -m|--model)
            MODEL="$2"
            shift 2
            ;;
        -t|--temperature)
            TEMPERATURE="$2"
            shift 2
            ;;
        -n|--max-tokens)
            MAX_TOKENS="$2"
            shift 2
            ;;
        --api-key)
            API_KEY="$2"
            shift 2
            ;;
        -*)
            echo -e "${RED}❌ 未知选项: $1${NC}"
            show_help
            exit 1
            ;;
        *)
            QUERY="$1"
            shift
            ;;
    esac
done

# 检查API密钥
if [ -z "$API_KEY" ]; then
    echo -e "${RED}❌ 未提供DeepSeek API密钥${NC}"
    echo "请设置以下任一方式提供API密钥："
    echo "1. 设置环境变量 DEEPSEEK_API_KEY"
    echo "2. 使用 --api-key 参数"
    echo "3. 在 claude-config.sh 中配置"
    echo ""
    echo -e "${YELLOW}💰 成本优势提醒: DeepSeek成本仅为DashScope的18.75%${NC}"
    echo "   • 输入: 0.001元/1k tokens (vs DashScope 0.008元)"
    echo "   • 输出: 0.002元/1k tokens (vs DashScope 0.008元)"
    exit 1
fi

# 显示使用的密钥信息（部分隐藏）
echo -e "${BLUE}🔑 使用DeepSeek API密钥: ${API_KEY:0:10}...${NC}"
echo -e "\033[0;33m💰 成本优势: 当前使用成本仅DashScope的18.75%\033[0m" >&2

# 执行模式
if [ $INTERACTIVE -eq 1 ]; then
    interactive_mode
elif [ -n "$QUERY" ]; then
    send_request "$QUERY" "$TEMPERATURE" "$MAX_TOKENS"
else
    # 如果没有参数，显示帮助
    show_help
fi