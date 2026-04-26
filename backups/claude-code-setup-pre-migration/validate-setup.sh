#!/bin/bash

# AI Assistant 设置验证脚本
# 验证所有技能包和配置是否正确设置

echo "🔍 AI Assistant 设置验证"
echo "========================"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 测试计数器
PASS=0
FAIL=0
WARN=0

# 函数：通过测试
pass() {
    echo -e "${GREEN}✓ $1${NC}"
    ((PASS++))
}

# 函数：失败测试
fail() {
    echo -e "${RED}✗ $1${NC}"
    ((FAIL++))
}

# 函数：警告
warn() {
    echo -e "${YELLOW}⚠ $1${NC}"
    ((WARN++))
}

echo ""
echo "1. 环境变量验证..."
if [ -n "$GITHUB_TOKEN" ]; then
    pass "GITHUB_TOKEN已设置 (${GITHUB_TOKEN:0:10}...)"
else
    fail "GITHUB_TOKEN未设置"
fi

if [ -n "$GITHUB_USERNAME" ]; then
    pass "GITHUB_USERNAME已设置 ($GITHUB_USERNAME)"
else
    fail "GITHUB_USERNAME未设置"
fi

if [ -n "$DASHSCOPE_API_KEY" ]; then
    pass "DASHSCOPE_API_KEY已设置 (${DASHSCOPE_API_KEY:0:10}...)"
else
    fail "DASHSCOPE_API_KEY未设置"
fi

if [ -n "$DEEPSEEK_API_KEY" ]; then
    pass "DEEPSEEK_API_KEY已设置 (${DEEPSEEK_API_KEY:0:10}...)"
else
    fail "DEEPSEEK_API_KEY未设置"
fi

echo ""
echo "2. 脚本文件验证..."
SCRIPTS=(
    "claude-dual-model.sh"
    "claude-qwen-alt.sh"
    "claude-dev.sh"
    "claude-fix.sh"
    "claude-zh.sh"
    "claude-config.sh"
    "init-claude-env.sh"
    "github-tools/github-diagnose.sh"
    "dashscope-maintenance.sh"
)

for script in "${SCRIPTS[@]}"; do
    if [ -f "/Users/frankie/claude-code-setup/$script" ]; then
        pass "$script 文件存在"
    else
        fail "$script 文件不存在"
    fi
done

echo ""
echo "3. GitHub配置验证..."
GIT_NAME=$(git config --global user.name 2>/dev/null)
GIT_EMAIL=$(git config --global user.email 2>/dev/null)

if [ -n "$GIT_NAME" ]; then
    pass "Git用户名: $GIT_NAME"
else
    fail "Git用户名未设置"
fi

if [ -n "$GIT_EMAIL" ]; then
    pass "Git邮箱: $GIT_EMAIL"
else
    fail "Git邮箱未设置"
fi

# 检查Git用户名与GitHub用户名是否一致
if [ "$GIT_NAME" = "frankiehot-tech" ]; then
    pass "Git用户名与GitHub用户名一致"
else
    warn "Git用户名($GIT_NAME)与GitHub用户名(frankiehot-tech)不一致"
    echo "  建议: git config --global user.name 'frankiehot-tech'"
fi

echo ""
echo "4. GitHub CLI验证..."
if command -v gh >/dev/null 2>&1; then
    pass "GitHub CLI已安装"

    # 检查登录状态
    if gh auth status 2>&1 | grep -q 'Logged in'; then
        pass "GitHub CLI已登录"
        USER=$(gh api user -q '.login' 2>/dev/null || echo "未知")
        pass "当前GitHub用户: $USER"
    else
        fail "GitHub CLI未登录"
    fi
else
    fail "GitHub CLI未安装"
fi

echo ""
echo "5. 技能包验证..."
# 检查技能文件是否存在
if [ -f ~/.claude/skills/github-integration.md ]; then
    pass "GitHub技能包文档存在"
else
    fail "GitHub技能包文档不存在"
fi

if [ -f ~/.claude/skills/bailian-platform.md ]; then
    pass "百炼平台技能包文档存在"
else
    fail "百炼平台技能包文档不存在"
fi

echo ""
echo "6. 别名配置验证（信息性）..."
echo "   别名定义在 ~/.zshrc 中，需要 'source ~/.zshrc' 或重启终端后生效"
echo "   已定义的别名: claude, claude-dual, claude-max, claude-dev, claude-fix, claude-zh, claude-qwen"

echo ""
echo "================================"
echo "验证结果:"
echo "  ${GREEN}通过: $PASS${NC}"
echo "  ${RED}失败: $FAIL${NC}"
echo "  ${YELLOW}警告: $WARN${NC}"

if [ $FAIL -eq 0 ]; then
    echo -e "\n${GREEN}✅ 所有关键测试通过！AI Assistant 设置验证成功。${NC}"

    echo -e "\n📋 下一步:"
    echo "  1. 要使用别名，请运行: source ~/.zshrc"
    echo "  2. 要设置环境变量，请运行: eval \"\$(./init-claude-env.sh --export)\""
    echo "  3. 测试GitHub连接: ./github-tools/github-diagnose.sh"
    echo "  4. 测试百炼平台: ./dashscope-maintenance.sh --report"

    # 建议修复Git用户名
    if [ $WARN -gt 0 ]; then
        echo -e "\n${YELLOW}⚠ 建议修复:${NC}"
        if [ "$GIT_NAME" != "frankiehot-tech" ]; then
            echo "  git config --global user.name 'frankiehot-tech'"
        fi
    fi
else
    echo -e "\n${RED}❌ 有 $FAIL 个测试失败，需要修复。${NC}"
    echo -e "\n🔧 修复建议:"
    echo "  1. 设置环境变量: eval \"\$(./init-claude-env.sh --export)\""
    echo "  2. 检查脚本文件: ls -la /Users/frankie/claude-code-setup/"
    echo "  3. 检查GitHub CLI: gh auth status"
    exit 1
fi