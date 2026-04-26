#!/bin/bash
# Claude Code 修复套件一键安装脚本
# 用法: ./install-claude-suite.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}🔧 Claude Code 修复套件安装器${NC}"
echo "=============================="
echo ""

# 1. 检查依赖
echo -e "${BLUE}📋 检查依赖...${NC}"

if ! command -v ollama &> /dev/null; then
    echo -e "${RED}❌ Ollama 未安装${NC}"
    echo "请先安装 Ollama: https://ollama.com"
    exit 1
fi
echo -e "${GREEN}✅ Ollama 已安装${NC}"

if ! command -v claude &> /dev/null; then
    echo -e "${RED}❌ Claude Code 未安装${NC}"
    echo "请先安装 Claude Code"
    exit 1
fi
echo -e "${GREEN}✅ Claude Code 已安装${NC}"

# 2. 创建优化模型
echo ""
echo -e "${BLUE}🤖 创建优化模型...${NC}"

if [ -f "$SCRIPT_DIR/Modelfile.qwen-claude" ]; then
    echo "创建 qwen2.5-claude 模型..."
    ollama create qwen2.5-claude -f "$SCRIPT_DIR/Modelfile.qwen-claude"
    echo -e "${GREEN}✅ qwen2.5-claude 模型已创建${NC}"
else
    echo -e "${YELLOW}⚠️  Modelfile.qwen-claude 未找到，跳过模型创建${NC}"
fi

# 3. 安装指纹清理工具
echo ""
echo -e "${BLUE}🛡️  安装指纹清理工具...${NC}"

if [ -f "$SCRIPT_DIR/clean-claude-fingerprints.sh" ]; then
    chmod +x "$SCRIPT_DIR/clean-claude-fingerprints.sh"
    echo -e "${GREEN}✅ 指纹清理工具已就绪${NC}"
    echo "   用法: ./clean-claude-fingerprints.sh [目录] [--dry-run]"
else
    echo -e "${YELLOW}⚠️  指纹清理工具未找到${NC}"
fi

# 4. 安装 Git pre-commit hook
echo ""
echo -e "${BLUE}📝 安装 Git pre-commit hook...${NC}"

if [ -f "$SCRIPT_DIR/.git-hooks/pre-commit" ]; then
    chmod +x "$SCRIPT_DIR/.git-hooks/pre-commit"
    
    # 为当前目录的 git 仓库安装 hook
    if [ -d "$SCRIPT_DIR/.git" ]; then
        cp "$SCRIPT_DIR/.git-hooks/pre-commit" "$SCRIPT_DIR/.git/hooks/pre-commit"
        chmod +x "$SCRIPT_DIR/.git/hooks/pre-commit"
        echo -e "${GREEN}✅ Git pre-commit hook 已安装到当前仓库${NC}"
    fi
    
    # 提供全局安装说明
    echo ""
    echo -e "${CYAN}💡 为其他仓库安装 hook:${NC}"
    echo "   cp .git-hooks/pre-commit /path/to/repo/.git/hooks/"
else
    echo -e "${YELLOW}⚠️  pre-commit hook 未找到${NC}"
fi

# 5. 安装智能路由脚本
echo ""
echo -e "${BLUE}🚀 安装智能路由脚本...${NC}"

if [ -f "$SCRIPT_DIR/claude-dual-model-v2.sh" ]; then
    chmod +x "$SCRIPT_DIR/claude-dual-model-v2.sh"
    echo -e "${GREEN}✅ 智能路由脚本已就绪${NC}"
    echo "   文件: $SCRIPT_DIR/claude-dual-model-v2.sh"
else
    echo -e "${YELLOW}⚠️  智能路由脚本未找到${NC}"
fi

# 6. 创建 .zshrc 更新提示
echo ""
echo -e "${BLUE}📋 请手动更新 ~/.zshrc 配置:${NC}"
echo ""
echo -e "${CYAN}# 1. 更新 claude 别名指向新脚本:${NC}"
echo 'alias claude="/Users/frankie/claude-code-setup/claude-dual-model-v2.sh"'
echo 'alias claude-dual="/Users/frankie/claude-code-setup/claude-dual-model-v2.sh"'
echo 'alias claude-auto="/Users/frankie/claude-code-setup/claude-dual-model-v2.sh auto"'
echo ""
echo -e "${CYAN}# 2. 更新本地模型别名:${NC}"
echo 'alias claude-local="/Users/frankie/claude-code-setup/claude-dual-model-v2.sh local"'
echo 'alias claude-ollama="/Users/frankie/claude-code-setup/claude-dual-model-v2.sh local"'
echo 'alias claude-small="export ANTHROPIC_BASE_URL="http://localhost:11434" && export ANTHROPIC_AUTH_TOKEN="ollama" && export ANTHROPIC_API_KEY="" && export ANTHROPIC_MODEL="qwen2.5-claude" && export CLAUDE_CODE_BARE=1 && export CLAUDE_CODE_SKIP_KEYCHAIN=1 && echo "🚀 [本地 Ollama] Qwen2.5-14B (32K ctx)" && command claude --bare"'
echo 'alias claude-big="export ANTHROPIC_BASE_URL="http://localhost:11434" && export ANTHROPIC_AUTH_TOKEN="ollama" && export ANTHROPIC_API_KEY="" && export ANTHROPIC_MODEL="qwen2.5-claude" && export CLAUDE_CODE_BARE=1 && export CLAUDE_CODE_SKIP_KEYCHAIN=1 && echo "🧠 [本地 Ollama] Qwen2.5-14B (32K ctx)" && command claude --bare"'
echo ""
echo -e "${CYAN}# 3. 修复其他别名:${NC}"
echo '# alias claude-pro="/Users/frankie/claude-pro.sh"  # 脚本不存在，已禁用'
echo 'alias claude-max="/Users/frankie/claude-code-setup/claude-dual-model-v2.sh 5"'
echo ""

# 7. 完成
echo ""
echo "=============================="
echo -e "${GREEN}✅ 安装完成!${NC}"
echo "=============================="
echo ""
echo -e "${BLUE}📚 后续步骤:${NC}"
echo "  1. 编辑 ~/.zshrc，应用上述配置更新"
echo "  2. 运行 source ~/.zshrc 使配置生效"
echo "  3. 测试新模型: ollama run qwen2.5-claude"
echo "  4. 启动 Claude Code: claude-big"
echo ""
echo -e "${BLUE}🛠️  可用工具:${NC}"
echo "  • 指纹清理: ./clean-claude-fingerprints.sh"
echo "  • 智能路由: ./claude-dual-model-v2.sh"
echo "  • 健康检查: 待创建"
echo ""
