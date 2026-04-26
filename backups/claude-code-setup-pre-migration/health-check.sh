#!/bin/bash
# Claude Code 健康检查脚本
# 检查所有服务状态、模型可用性、密钥配置

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

ERRORS=0
WARNINGS=0

echo -e "${BLUE}🔍 Claude Code 健康检查${NC}"
echo "========================"
echo ""

# 1. 检查 Ollama 服务
echo -e "${BLUE}[1/7] Ollama 服务${NC}"
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Ollama 服务运行正常${NC}"
    
    # 检查可用模型
    echo -e "${CYAN}   已安装模型:${NC}"
    ollama list | grep -v "NAME" | while read line; do
        echo -e "   • $line"
    done
else
    echo -e "${RED}❌ Ollama 服务未运行${NC}"
    echo -e "${YELLOW}   修复: brew services start ollama${NC}"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# 2. 检查 DashScope 适配器
echo -e "${BLUE}[2/7] DashScope 适配器${NC}"
if curl -s http://127.0.0.1:8080/v1/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ DashScope 适配器运行正常${NC}"
    ADAPTER_STATUS=$(curl -s http://127.0.0.1:8080/v1/health)
    echo -e "${CYAN}   状态: $ADAPTER_STATUS${NC}"
else
    echo -e "${RED}❌ DashScope 适配器未运行${NC}"
    echo -e "${YELLOW}   修复: adapter-start${NC}"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# 3. 检查 API 密钥
echo -e "${BLUE}[3/7] API 密钥配置${NC}"

if [ -n "${DASHSCOPE_API_KEY:-}" ]; then
    echo -e "${GREEN}✅ DASHSCOPE_API_KEY 已配置${NC}"
    echo -e "${CYAN}   前缀: ${DASHSCOPE_API_KEY:0:10}...${NC}"
else
    echo -e "${RED}❌ DASHSCOPE_API_KEY 未配置${NC}"
    ERRORS=$((ERRORS + 1))
fi

if [ -n "${DEEPSEEK_API_KEY:-}" ]; then
    echo -e "${GREEN}✅ DEEPSEEK_API_KEY 已配置${NC}"
    echo -e "${CYAN}   前缀: ${DEEPSEEK_API_KEY:0:10}...${NC}"
else
    echo -e "${YELLOW}⚠️  DEEPSEEK_API_KEY 未配置${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
    echo -e "${GREEN}✅ ANTHROPIC_API_KEY 已配置${NC}"
else
    echo -e "${YELLOW}⚠️  ANTHROPIC_API_KEY 未配置${NC}"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

# 4. 检查关键脚本
echo -e "${BLUE}[4/7] 关键脚本${NC}"

SCRIPTS=(
    "claude-dual-model.sh"
    "claude-dual-model-v2.sh"
    "dashscope-adapter.py"
    "start-dashscope-adapter.sh"
    "clean-claude-fingerprints.sh"
)

for script in "${SCRIPTS[@]}"; do
    if [ -f "/Users/frankie/claude-code-setup/$script" ]; then
        echo -e "${GREEN}✅ $script${NC}"
    else
        echo -e "${RED}❌ $script 缺失${NC}"
        ERRORS=$((ERRORS + 1))
    fi
done
echo ""

# 5. 检查 .zshrc 别名
echo -e "${BLUE}[5/7] .zshrc 别名配置${NC}"

if [ -f "$HOME/.zshrc" ]; then
    ALIASES=("claude" "claude-big" "claude-small" "claude-max" "claude-pro")
    
    for alias in "${ALIASES[@]}"; do
        if grep -q "alias $alias=" "$HOME/.zshrc" 2>/dev/null; then
            echo -e "${GREEN}✅ $alias 已配置${NC}"
        else
            echo -e "${YELLOW}⚠️  $alias 未配置${NC}"
            WARNINGS=$((WARNINGS + 1))
        fi
    done
else
    echo -e "${RED}❌ ~/.zshrc 不存在${NC}"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# 6. 检查模型性能
echo -e "${BLUE}[6/7] 模型快速测试${NC}"

if ollama list | grep -q "qwen2.5-claude"; then
    echo -e "${GREEN}✅ qwen2.5-claude 模型已安装${NC}"
elif ollama list | grep -q "gemma4-claude"; then
    echo -e "${YELLOW}⚠️  使用旧版 gemma4-claude 模型${NC}"
    echo -e "${YELLOW}   建议: 升级到 qwen2.5-claude${NC}"
    WARNINGS=$((WARNINGS + 1))
else
    echo -e "${RED}❌ 未找到 Claude Code 专用模型${NC}"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# 7. 检查网络连接
echo -e "${BLUE}[7/7] 网络连接${NC}"

if ping -c 1 -W 2 dashscope.aliyuncs.com > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 百炼 API 可访问${NC}"
else
    echo -e "${YELLOW}⚠️  百炼 API 连接异常${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

if ping -c 1 -W 2 api.deepseek.com > /dev/null 2>&1; then
    echo -e "${GREEN}✅ DeepSeek API 可访问${NC}"
else
    echo -e "${YELLOW}⚠️  DeepSeek API 连接异常${NC}"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

# 总结
echo "========================"
echo -e "${BLUE}📊 健康检查总结${NC}"
echo "========================"

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ 所有检查通过，系统健康！${NC}"
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠️  发现 $WARNINGS 个警告，建议优化${NC}"
else
    echo -e "${RED}❌ 发现 $ERRORS 个错误，$WARNINGS 个警告${NC}"
    echo -e "${RED}   请先修复错误再使用 Claude Code${NC}"
fi

echo ""
echo -e "${BLUE}💡 快速修复:${NC}"
echo "  启动 Ollama:     brew services start ollama"
echo "  启动适配器:      adapter-start"
echo "  安装新模型:      ollama pull qwen2.5:14b"
echo "  运行安装脚本:    ./install-claude-suite.sh"
echo ""
