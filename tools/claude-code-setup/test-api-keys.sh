#!/bin/bash

# API密钥测试脚本
# 测试两个阿里云API密钥和DeepSeek连接

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 API密钥诊断测试${NC}"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/load-local-secrets.sh"
require_any_secret DASHSCOPE_API_KEY ALIYUN_API_KEY || exit 1

PRIMARY_KEY="${DASHSCOPE_API_KEY:-$ALIYUN_API_KEY}"
SECONDARY_KEY="${ALIYUN_API_KEY:-$DASHSCOPE_API_KEY}"

test_dashscope_key() {
    local label="$1"
    local key="$2"

    echo -e "${YELLOW}${label} (${key:0:10}...)${NC}"
    local response
    response=$(curl -s -X GET "https://dashscope.aliyuncs.com/api/v1/models" \
      -H "Authorization: Bearer $key" \
      -H "Content-Type: application/json" \
      -w "%{http_code}" 2>/dev/null | tail -c 3)

    if [ "$response" = "200" ]; then
        echo -e "  ${GREEN}✓ 有效 (HTTP $response)${NC}"
    else
        echo -e "  ${RED}✗ 无效 (HTTP $response)${NC}"
    fi
}

echo -e "${YELLOW}1. 测试阿里云DashScope API${NC}"
test_dashscope_key "  主密钥" "$PRIMARY_KEY"

echo ""
echo -e "${YELLOW}2. 测试备用阿里云DashScope API${NC}"
if [ "$SECONDARY_KEY" != "$PRIMARY_KEY" ]; then
    test_dashscope_key "  备用密钥" "$SECONDARY_KEY"
else
    echo "  当前只配置了一套 DashScope 密钥"
fi

echo ""
echo -e "${YELLOW}3. 测试DeepSeek API连接性${NC}"
echo "  注意：DeepSeek需要独立的API密钥，不能使用阿里云密钥"

# 测试DeepSeek端点是否可达
DEEPSEEK_ENDPOINT="https://api.deepseek.com/v1"
echo "  测试端点: $DEEPSEEK_ENDPOINT"

# 简单连接测试（不带认证）
CONNECT_TEST=$(curl -s -I "$DEEPSEEK_ENDPOINT" -o /dev/null -w "%{http_code}" 2>/dev/null)
if [ "$CONNECT_TEST" = "200" ] || [ "$CONNECT_TEST" = "401" ] || [ "$CONNECT_TEST" = "404" ]; then
    echo -e "  ${GREEN}✓ 端点可达 (HTTP $CONNECT_TEST)${NC}"
else
    echo -e "  ${RED}✗ 端点不可达 (HTTP $CONNECT_TEST)${NC}"
fi

echo ""
echo -e "${YELLOW}4. 测试使用阿里云密钥访问DeepSeek${NC}"
echo "  这将重现401错误..."
RESPONSE_DEEPSEEK=$(curl -s -X GET "$DEEPSEEK_ENDPOINT/v1/models" \
  -H "Authorization: Bearer $PRIMARY_KEY" \
  -H "Content-Type: application/json" \
  -w "%{http_code}" 2>/dev/null | tail -c 3)

if [ "$RESPONSE_DEEPSEEK" = "401" ]; then
    echo -e "  ${RED}✗ 预期错误：阿里云密钥不能用于DeepSeek (HTTP 401)${NC}"
    echo "  错误信息与用户遇到的一致"
else
    echo -e "  ${YELLOW}⚠  意外响应 (HTTP $RESPONSE_DEEPSEEK)${NC}"
fi

echo ""
echo -e "${BLUE}📊 诊断结论${NC}"
echo ""
echo "问题分析："
echo "1. DeepSeek 需要独立的 API 密钥"
echo "2. 阿里云密钥只能用于 DashScope 服务"
echo "3. 用户需要获取 DeepSeek API 密钥"
echo ""
echo "解决方案："
echo "1. 注册 DeepSeek 平台获取 API 密钥"
echo "2. 更新配置文件使用正确的密钥"
echo "3. 或者继续使用阿里云Qwen模型（通过claude-qwen-alt.sh）"
