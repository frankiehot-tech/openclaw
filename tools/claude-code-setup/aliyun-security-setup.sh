#!/bin/bash

# aliyun-security-setup.sh - 阿里云安全配置和问题排查脚本
# 帮助用户配置IP白名单和联系技术支持

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/load-local-secrets.sh"
require_any_secret DASHSCOPE_API_KEY ALIYUN_API_KEY || exit 1

API_KEY="${DASHSCOPE_API_KEY:-$ALIYUN_API_KEY}"
IP_ADDRESS="178.208.190.142"
ACCOUNT_NAME="nick6302944537"
ACCOUNT_ID="1023057678618605"
AK_ACCOUNT_ID="1712756199166083"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 打印标题
print_title() {
    echo -e "${CYAN}"
    echo "================================================"
    echo "  阿里云安全配置和DashScope问题排查"
    echo "================================================"
    echo -e "${NC}"
}

# 检查当前状态
check_current_status() {
    echo -e "${BLUE}🔍 检查当前状态${NC}"
    echo ""

    # 1. 检查公网IP
    echo -e "${YELLOW}1. 当前公网IP地址:${NC}"
    CURRENT_IP=$(curl -s https://api.ipify.org 2>/dev/null || echo "无法获取")
    echo "   $CURRENT_IP"
    if [ "$CURRENT_IP" = "$IP_ADDRESS" ]; then
        echo -e "  ${GREEN}✓ 与记录IP一致${NC}"
    else
        echo -e "  ${YELLOW}⚠  与记录IP不同，当前IP: $CURRENT_IP${NC}"
        read -p "  是否更新IP地址到 $CURRENT_IP? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            IP_ADDRESS="$CURRENT_IP"
            echo -e "  ${GREEN}✓ IP已更新为 $IP_ADDRESS${NC}"
        fi
    fi
    echo ""

    # 2. 检查API密钥有效性
    echo -e "${YELLOW}2. DashScope API密钥验证:${NC}"
    RESPONSE=$(curl -s -X GET "https://dashscope.aliyuncs.com/api/v1/models" \
      -H "Authorization: Bearer $API_KEY" \
      -H "Content-Type: application/json" \
      -w "%{http_code}" 2>/dev/null | tail -c 3)

    if [ "$RESPONSE" = "200" ]; then
        echo -e "  ${GREEN}✓ API密钥有效 (HTTP 200)${NC}"
    else
        echo -e "  ${RED}✗ API密钥无效 (HTTP $RESPONSE)${NC}"
    fi
    echo ""

    # 3. 检查aliyun CLI配置
    echo -e "${YELLOW}3. 阿里云CLI配置:${NC}"
    if command -v aliyun &> /dev/null; then
        echo -e "  ${GREEN}✓ aliyun CLI已安装${NC}"
        aliyun configure list 2>&1 | grep -A5 "Profile" || echo "  配置信息不可用"
    else
        echo -e "  ${YELLOW}⚠  aliyun CLI未安装${NC}"
    fi
}

# 显示控制台操作指南
show_console_guide() {
    echo -e "${BLUE}📋 控制台操作指南${NC}"
    echo ""

    echo -e "${YELLOW}步骤1: 登录阿里云控制台${NC}"
    echo "  网址: https://homenew.console.aliyun.com"
    echo "  账号: $ACCOUNT_NAME"
    echo "  账号ID: $ACCOUNT_ID"
    echo ""

    echo -e "${YELLOW}步骤2: 访问安全控制台添加IP白名单${NC}"
    echo "  直接链接: https://yundun.console.aliyun.com/?p=scnew#/sc/whitelist/ip"
    echo "  操作步骤:"
    echo "  1. 点击'添加白名单'"
    echo "  2. 输入IP地址: $IP_ADDRESS"
    echo "  3. 备注: 'DashScope API访问'"
    echo "  4. 选择'永久有效'"
    echo "  5. 点击'确定'"
    echo ""

    echo -e "${YELLOW}步骤3: 检查DashScope服务状态${NC}"
    echo "  链接: https://dashscope.console.aliyun.com/"
    echo "  检查项目:"
    echo "  1. 模型服务是否正常"
    echo "  2. API调用额度是否充足"
    echo "  3. 是否有地域限制"
    echo ""

    echo -e "${YELLOW}步骤4: 联系技术支持请求LLM兼容模式${NC}"
    echo "  链接: https://workorder.console.aliyun.com/#/ticket/createIndex"
    echo "  问题分类: 产品技术问题 > 人工智能与机器学习 > 百炼模型服务"
    echo "  问题描述模板:"
    echo "  '请求为DashScope API兼容模式增加LLM格式支持。'"
    echo "  '当前兼容模式只支持OpenAI格式(/chat/completions)，'"
    echo "  '但AI Assistant等工具需要LLM格式(/messages)。'"
    echo "  '请评估增加LLM兼容模式的可能性。'"
}

# 显示CLI操作选项
show_cli_options() {
    echo -e "${BLUE}🖥️  CLI操作选项${NC}"
    echo ""

    echo -e "${YELLOW}选项A: 检查现有IP白名单${NC}"
    echo "  运行以下命令检查DDoS高防IP白名单:"
    echo "  aliyun ddoscoo DescribeWebRules --RegionId cn-hangzhou"
    echo "  aliyun ddoscoo DescribeAutoCcWhitelist --InstanceId <实例ID>"
    echo ""

    echo -e "${YELLOW}选项B: 添加IP到DDoS高防白名单${NC}"
    echo "  如果已购买DDoS高防服务:"
    echo "  aliyun ddoscoo AddAutoCcWhitelist \\"
    echo "    --InstanceId <您的实例ID> \\"
    echo "    --Whitelist '[{\"srcIp\":\"$IP_ADDRESS\"}]'"
    echo ""

    echo -e "${YELLOW}选项C: 检查API网关IP控制${NC}"
    echo "  aliyun cloudapi DescribeIpControls --RegionId cn-hangzhou"
    echo ""
}

# 显示技术联系信息
show_contact_info() {
    echo -e "${BLUE}📞 技术支持联系信息${NC}"
    echo ""

    echo -e "${YELLOW}阿里云技术支持工单${NC}"
    echo "  链接: https://workorder.console.aliyun.com/#/ticket/createIndex"
    echo "  所需信息:"
    echo "  - 账号ID: $ACCOUNT_ID"
    echo "  - AK账号ID: $AK_ACCOUNT_ID"
    echo "  - 问题类型: 产品功能需求"
    echo "  - 产品: 百炼模型服务 (DashScope)"
    echo "  - 问题描述: 请求增加LLM API兼容模式"
    echo ""

    echo -e "${YELLOW}问题描述模板${NC}"
    cat << EOF
主题: 请求DashScope API兼容模式增加LLM格式支持

详细描述:

1. 当前情况:
   - DashScope提供的"兼容模式"端点(https://dashscope.aliyuncs.com/compatible-mode/v1)只支持OpenAI API格式(/chat/completions)
   - 不支持LLM API格式(/messages)

2. 问题影响:
   - AI Assistant等工具无法连接DashScope服务
   - 用户无法通过LLM兼容客户端使用Qwen模型
   - 限制了用户选择和使用体验

3. 需求:
   - 在兼容模式中增加LLM API格式支持
   - 实现/messages端点，兼容LLM消息格式
   - 保持现有OpenAI兼容性不变

4. 测试信息:
   - 测试IP: $IP_ADDRESS
   - 账号ID: $ACCOUNT_ID
   - 当前AK: ${API_KEY:0:10}...

谢谢！
EOF
    echo ""
}

# 显示替代解决方案
show_alternative_solutions() {
    echo -e "${BLUE}💡 替代解决方案${NC}"
    echo ""

    echo -e "${YELLOW}方案1: 使用OpenAI兼容客户端${NC}"
    echo "  已创建工具: claude-qwen-alt.sh"
    echo "  使用方法:"
    echo "  ./claude-qwen-alt.sh \"你的问题\""
    echo "  ./claude-qwen-alt.sh -i  # 交互模式"
    echo ""

    echo -e "${YELLOW}方案2: 使用Python CLI工具${NC}"
    echo "  已创建工具: qwen-cli.py"
    echo "  使用方法:"
    echo "  python3 qwen-cli.py \"你的问题\""
    echo "  python3 qwen-cli.py -i  # 交互模式"
    echo ""

    echo -e "${YELLOW}方案3: 直接curl调用${NC}"
    echo "  命令模板:"
    echo "  curl -X POST https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions \\"
    echo "    -H 'Authorization: Bearer \$DASHSCOPE_API_KEY' \\"
    echo "    -H 'Content-Type: application/json' \\"
    echo "    -d '{\"model\":\"qwen3.6-plus\",\"messages\":[{\"role\":\"user\",\"content\":\"你的问题\"}]}'"
    echo ""
}

# 主函数
main() {
    print_title

    echo -e "${GREEN}账号信息:${NC}"
    echo "  - 账号名称: $ACCOUNT_NAME"
    echo "  - 账号ID: $ACCOUNT_ID"
    echo "  - AK账号ID: $AK_ACCOUNT_ID"
    echo "  - 当前IP: $IP_ADDRESS"
    echo ""

    # 显示菜单
    echo -e "${CYAN}请选择操作:${NC}"
    echo "  1. 检查当前状态"
    echo "  2. 显示控制台操作指南"
    echo "  3. 显示CLI操作选项"
    echo "  4. 显示技术支持联系信息"
    echo "  5. 显示替代解决方案"
    echo "  6. 执行完整诊断"
    echo "  0. 退出"
    echo ""

    read -p "请输入选择 (0-6): " choice

    case $choice in
        1)
            check_current_status
            ;;
        2)
            show_console_guide
            ;;
        3)
            show_cli_options
            ;;
        4)
            show_contact_info
            ;;
        5)
            show_alternative_solutions
            ;;
        6)
            check_current_status
            echo ""
            show_console_guide
            echo ""
            show_cli_options
            echo ""
            show_alternative_solutions
            ;;
        0)
            echo "退出"
            exit 0
            ;;
        *)
            echo -e "${RED}无效选择${NC}"
            ;;
    esac

    echo ""
    echo -e "${GREEN}✅ 操作完成${NC}"
    echo "提示: 运行 ./claude-zh.sh 测试Qwen模型工作流"
}

# 执行主函数
main
