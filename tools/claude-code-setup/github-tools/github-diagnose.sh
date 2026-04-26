#!/bin/bash

# GitHub连接诊断工具
# 检查GitHub配置和连接状态

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 GitHub连接诊断${NC}"
echo -e "${BLUE}=================${NC}\n"

# 1. 检查Git配置
echo -e "${YELLOW}1. Git配置检查:${NC}"
GIT_NAME=$(git config --global user.name)
GIT_EMAIL=$(git config --global user.email)

if [ -n "$GIT_NAME" ]; then
    echo -e "  ${GREEN}✓ Git用户名: $GIT_NAME${NC}"
else
    echo -e "  ${RED}✗ Git用户名未设置${NC}"
fi

if [ -n "$GIT_EMAIL" ]; then
    echo -e "  ${GREEN}✓ Git邮箱: $GIT_EMAIL${NC}"
else
    echo -e "  ${RED}✗ Git邮箱未设置${NC}"
fi

# 2. 检查GitHub CLI状态
echo -e "\n${YELLOW}2. GitHub CLI状态:${NC}"
if command -v gh &> /dev/null; then
    echo -e "  ${GREEN}✓ GitHub CLI已安装${NC}"

    # 检查登录状态
    if gh auth status &> /dev/null; then
        echo -e "  ${GREEN}✓ GitHub CLI已登录${NC}"

        # 获取当前用户
        CURRENT_USER=$(gh api user -q .login 2>/dev/null)
        if [ -n "$CURRENT_USER" ]; then
            echo -e "  ${GREEN}✓ 当前用户: $CURRENT_USER${NC}"
        fi
    else
        echo -e "  ${RED}✗ GitHub CLI未登录${NC}"
        echo -e "  ${BLUE}  运行 'gh auth login' 登录${NC}"
    fi
else
    echo -e "  ${RED}✗ GitHub CLI未安装${NC}"
    echo -e "  ${BLUE}  运行 'brew install gh' 安装${NC}"
fi

# 3. 检查环境变量
echo -e "\n${YELLOW}3. 环境变量检查:${NC}"
if [ -n "$GITHUB_TOKEN" ]; then
    echo -e "  ${GREEN}✓ GITHUB_TOKEN已设置${NC}"
    echo -e "  ${BLUE}  令牌开头: ${GITHUB_TOKEN:0:10}...${NC}"
else
    echo -e "  ${YELLOW}⚠  GITHUB_TOKEN未设置${NC}"
    echo -e "  ${BLUE}  建议设置个人访问令牌${NC}"
fi

if [ -n "$GITHUB_USERNAME" ]; then
    echo -e "  ${GREEN}✓ GITHUB_USERNAME已设置: $GITHUB_USERNAME${NC}"
else
    echo -e "  ${YELLOW}⚠  GITHUB_USERNAME未设置${NC}"
fi

if [ -n "$GITHUB_EMAIL" ]; then
    echo -e "  ${GREEN}✓ GITHUB_EMAIL已设置: $GITHUB_EMAIL${NC}"
else
    echo -e "  ${YELLOW}⚠  GITHUB_EMAIL未设置${NC}"
fi

# 4. 测试API连接
echo -e "\n${YELLOW}4. API连接测试:${NC}"
if [ -n "$GITHUB_TOKEN" ]; then
    RESPONSE=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        https://api.github.com/user 2>/dev/null)

    if echo "$RESPONSE" | grep -q '"login"'; then
        USERNAME=$(echo "$RESPONSE" | jq -r '.login' 2>/dev/null || echo "未知")
        echo -e "  ${GREEN}✓ API连接成功${NC}"
        echo -e "  ${BLUE}  认证用户: $USERNAME${NC}"
    elif echo "$RESPONSE" | grep -q '"message"'; then
        ERROR_MSG=$(echo "$RESPONSE" | jq -r '.message' 2>/dev/null || echo "未知错误")
        echo -e "  ${RED}✗ API连接失败: $ERROR_MSG${NC}"
    else
        echo -e "  ${RED}✗ API连接失败，无响应${NC}"
    fi
else
    echo -e "  ${YELLOW}⚠  跳过API测试（需要GITHUB_TOKEN）${NC}"
fi

# 5. 检查SSH连接
echo -e "\n${YELLOW}5. SSH连接测试:${NC}"
if [ -f ~/.ssh/id_ed25519.pub ] || [ -f ~/.ssh/id_rsa.pub ]; then
    echo -e "  ${GREEN}✓ SSH密钥存在${NC}"

    # 测试SSH连接
    SSH_OUTPUT=$(ssh -T git@github.com 2>&1 | head -1)
    if echo "$SSH_OUTPUT" | grep -q "successfully authenticated"; then
        echo -e "  ${GREEN}✓ SSH连接成功${NC}"
    elif echo "$SSH_OUTPUT" | grep -q "Permission denied"; then
        echo -e "  ${RED}✗ SSH权限被拒绝${NC}"
        echo -e "  ${BLUE}  请确保SSH密钥已添加到GitHub账户${NC}"
    else
        echo -e "  ${YELLOW}⚠  SSH连接测试: $SSH_OUTPUT${NC}"
    fi
else
    echo -e "  ${YELLOW}⚠  未找到SSH密钥${NC}"
    echo -e "  ${BLUE}  运行 'ssh-keygen -t ed25519 -C \"your-email@example.com\"' 创建${NC}"
fi

# 6. 检查当前目录Git状态
echo -e "\n${YELLOW}6. 当前目录Git状态:${NC}"
if [ -d .git ]; then
    echo -e "  ${GREEN}✓ 当前目录是Git仓库${NC}"

    # 检查远程仓库
    REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "无")
    echo -e "  ${BLUE}  远程仓库: $REMOTE_URL${NC}"

    # 检查分支
    CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "未知")
    echo -e "  ${BLUE}  当前分支: $CURRENT_BRANCH${NC}"

    # 检查未提交的更改
    if [ -n "$(git status --porcelain)" ]; then
        echo -e "  ${YELLOW}⚠  有未提交的更改${NC}"
    else
        echo -e "  ${GREEN}✓ 工作区干净${NC}"
    fi
else
    echo -e "  ${YELLOW}⚠  当前目录不是Git仓库${NC}"
fi

echo -e "\n${BLUE}📋 建议操作:${NC}"

# 根据检查结果给出建议
if [ -z "$GIT_NAME" ] || [ -z "$GIT_EMAIL" ]; then
    echo -e "  ${YELLOW}• 运行以下命令设置Git配置:${NC}"
    echo -e "    git config --global user.name \"Your Name\""
    echo -e "    git config --global user.email \"your-email@example.com\""
fi

if ! command -v gh &> /dev/null || ! gh auth status &> /dev/null; then
    echo -e "  ${YELLOW}• 安装并登录GitHub CLI:${NC}"
    echo -e "    brew install gh"
    echo -e "    gh auth login"
fi

if [ -z "$GITHUB_TOKEN" ]; then
    echo -e "  ${YELLOW}• 创建GitHub个人访问令牌:${NC}"
    echo -e "    1. 访问 https://github.com/settings/tokens"
    echo -e "    2. 生成新令牌（选择repo权限）"
    echo -e "    3. 添加到环境变量:"
    echo -e "       export GITHUB_TOKEN=\"your_token_here\""
fi

if [ ! -f ~/.ssh/id_ed25519.pub ] && [ ! -f ~/.ssh/id_rsa.pub ]; then
    echo -e "  ${YELLOW}• 创建SSH密钥:${NC}"
    echo -e "    ssh-keygen -t ed25519 -C \"$GITHUB_EMAIL\""
    echo -e "    然后将公钥添加到GitHub:"
    echo -e "    cat ~/.ssh/id_ed25519.pub"
fi

echo -e "\n${GREEN}✅ 诊断完成${NC}"
echo -e "${BLUE}📊 运行 'gh auth status' 查看详细状态${NC}"