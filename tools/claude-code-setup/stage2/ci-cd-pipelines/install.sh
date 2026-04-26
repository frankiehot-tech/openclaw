#!/bin/bash

# CI/CD流水线技能包安装脚本
# 将CI/CD设计技能安装到AI Assistant技能目录

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  CI/CD流水线技能包安装脚本${NC}"
echo -e "${BLUE}========================================${NC}"

# 检查AI Assistant技能目录是否存在
SKILLS_DIR="$HOME/.claude/skills"
if [ ! -d "$SKILLS_DIR" ]; then
    echo -e "${YELLOW}创建AI Assistant技能目录: $SKILLS_DIR${NC}"
    mkdir -p "$SKILLS_DIR"
fi

# 获取当前脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 复制技能文件
echo -e "${BLUE}安装CI/CD设计技能...${NC}"
CI_CD_SKILL_FILE="$SCRIPT_DIR/ci-cd-designer.md"
TARGET_FILE="$SKILLS_DIR/ci-cd-designer.md"

if [ ! -f "$CI_CD_SKILL_FILE" ]; then
    echo -e "${RED}错误: 找不到技能文件: $CI_CD_SKILL_FILE${NC}"
    exit 1
fi

cp "$CI_CD_SKILL_FILE" "$TARGET_FILE"
echo -e "${GREEN}✓ 技能文件已复制到: $TARGET_FILE${NC}"

# 设置文件权限
chmod 644 "$TARGET_FILE"

# 验证安装
echo -e "\n${BLUE}验证安装...${NC}"
if [ -f "$TARGET_FILE" ]; then
    echo -e "${GREEN}✓ CI/CD技能包安装成功!${NC}"

    # 显示技能文件信息
    echo -e "\n${BLUE}技能文件信息:${NC}"
    echo -e "  文件: $(basename "$TARGET_FILE")"
    echo -e "  大小: $(du -h "$TARGET_FILE" | cut -f1)"
    echo -e "  路径: $TARGET_FILE"

    # 检查技能文件格式
    if head -n 5 "$TARGET_FILE" | grep -q -- "---"; then
        echo -e "  格式: ${GREEN}✓ 有效的YAML frontmatter${NC}"
    else
        echo -e "  格式: ${YELLOW}⚠ 未找到YAML frontmatter${NC}"
    fi
else
    echo -e "${RED}✗ 安装失败: 技能文件未找到${NC}"
    exit 1
fi

# 显示使用说明
echo -e "\n${BLUE}使用说明:${NC}"
echo -e "  1. 重启AI Assistant会话使新技能生效"
echo -e "  2. 在AI Assistant中使用以下命令激活技能:"
echo -e "     ${YELLOW}使用CI/CD设计技能${NC}"
echo -e "     或直接使用技能命令:"
echo -e "     ${YELLOW}/ci-cd-designer${NC}"
echo -e "  3. 描述你的CI/CD需求，例如:"
echo -e "     \"为我的Python项目创建GitHub Actions工作流\""
echo -e "     \"配置多环境Kubernetes部署\""
echo -e "     \"创建完整的测试自动化流水线\""

# 显示模板文件信息
echo -e "\n${BLUE}可用模板:${NC}"
echo -e "  ${GREEN}✓ GitHub Actions${NC}      - $(ls -1 "$SCRIPT_DIR/github-actions/" | wc -l) 个模板"
echo -e "  ${GREEN}✓ GitLab CI/CD${NC}       - $(ls -1 "$SCRIPT_DIR/gitlab-ci/" | wc -l) 个模板"
echo -e "  ${GREEN}✓ Jenkins${NC}            - $(ls -1 "$SCRIPT_DIR/jenkins/" | wc -l) 个模板"
echo -e "  ${GREEN}✓ 测试自动化${NC}         - $(ls -1 "$SCRIPT_DIR/test-automation/" | wc -l) 个配置文件"
echo -e "  ${GREEN}✓ 部署配置${NC}           - $(find "$SCRIPT_DIR/deployment" -name "*.yml" -o -name "*.yaml" -o -name "*.json" | wc -l) 个模板"

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  安装完成! 请重启AI Assistant会话。${NC}"
echo -e "${GREEN}========================================${NC}"

# 可选: 检查是否需要重启当前会话
if [ -n "$AI_SESSION_ID" ]; then
    echo -e "\n${YELLOW}提示: 检测到当前在AI Assistant会话中运行${NC}"
    echo -e "      请使用 ${YELLOW}/clear${NC} 命令清除会话，然后重新开始以使新技能生效"
fi