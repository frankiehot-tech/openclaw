#!/bin/bash

# AI 模型连接验证脚本
# 测试所有已配置的 Claude Code 模型连接

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

pass_count=0
fail_count=0

echo "=========================================="
echo "  AI 模型连接验证"
echo "=========================================="
echo ""

# 加载密钥
source ~/.config/secret-env/load-keychain-secrets.sh

# 测试百炼API直连
echo -e "${BLUE}1. 百炼API直连 (OpenAI格式)${NC}"
result=$(curl -s -X POST "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions" \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3.6-plus","messages":[{"role":"user","content":"Hi"}],"max_tokens":5}' 2>&1)
if echo "$result" | grep -q "choices"; then
    echo -e "   ${GREEN}✅ 百炼API连接正常${NC}"
    ((pass_count++))
else
    echo -e "   ${RED}❌ 百炼API连接失败${NC}"
    echo -e "   响应: $(echo "$result" | head -c 100)"
    ((fail_count++))
fi
echo ""

# 测试本地适配器
echo -e "${BLUE}2. DashScope适配器 (Anthropic格式)${NC}"
if curl -s http://127.0.0.1:8080/v1/health > /dev/null 2>&1; then
    echo -e "   ${GREEN}✅ 适配器运行中${NC}"
    result=$(curl -s -X POST "http://127.0.0.1:8080/v1/messages" \
      -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
      -H "content-type: application/json" \
      -d '{"model":"qwen3.6-plus","max_tokens":5,"stream":false,"messages":[{"role":"user","content":"Hi"}]}' 2>&1)
    if echo "$result" | grep -q "content"; then
        echo -e "   ${GREEN}✅ 适配器API正常${NC}"
        ((pass_count++))
    else
        echo -e "   ${RED}❌ 适配器API失败${NC}"
        echo -e "   响应: $(echo "$result" | head -c 100)"
        ((fail_count++))
    fi
else
    echo -e "   ${YELLOW}⚠️ 适配器未运行 (运行 adapter-start 启动)${NC}"
    ((fail_count++))
fi
echo ""

# 测试DeepSeek API
echo -e "${BLUE}3. DeepSeek API${NC}"
if [ -n "$DEEPSEEK_API_KEY" ]; then
    result=$(curl -s -X POST "https://api.deepseek.com/v1/chat/completions" \
      -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"Hi"}],"max_tokens":5}' 2>&1)
    if echo "$result" | grep -q "choices"; then
        echo -e "   ${GREEN}✅ DeepSeek连接正常${NC}"
        ((pass_count++))
    else
        echo -e "   ${RED}❌ DeepSeek连接失败${NC}"
        echo -e "   响应: $(echo "$result" | head -c 100)"
        ((fail_count++))
    fi
else
    echo -e "   ${YELLOW}⚠️ DEEPSEEK_API_KEY 未设置${NC}"
    ((fail_count++))
fi
echo ""

# 测试Ollama本地模型
echo -e "${BLUE}4. Ollama 本地模型 (gemma4-claude)${NC}"
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    if ollama list | grep -q "gemma4-claude"; then
        echo -e "   ${GREEN}✅ gemma4-claude 可用${NC}"
        ((pass_count++))
    else
        echo -e "   ${YELLOW}⚠️ gemma4-claude 未安装 (运行: ollama pull gemma4-claude)${NC}"
        ((fail_count++))
    fi
else
    echo -e "   ${YELLOW}⚠️ Ollama 服务未运行${NC}"
    ((fail_count++))
fi
echo ""

# 总结
echo "=========================================="
echo -e "结果: ${GREEN}${pass_count} 通过${NC} / ${RED}${fail_count} 失败${NC}"
echo "=========================================="