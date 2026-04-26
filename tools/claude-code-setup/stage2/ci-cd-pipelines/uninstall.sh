#!/bin/bash

# CI/CD流水线技能包卸载脚本
# 从AI Assistant技能目录中移除CI/CD设计技能

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  CI/CD流水线技能包卸载脚本${NC}"
echo -e "${BLUE}========================================${NC}"

# 检查AI Assistant技能目录是否存在
SKILLS_DIR="$HOME/.claude/skills"
TARGET_FILE="$SKILLS_DIR/ci-cd-designer.md"

if [ ! -d "$SKILLS_DIR" ]; then
    echo -e "${YELLOW}AI Assistant技能目录不存在: $SKILLS_DIR${NC}"
    echo -e "${GREEN}✓ 技能包未安装${NC}"
    exit 0
fi

if [ ! -f "$TARGET_FILE" ]; then
    echo -e "${YELLOW}CI/CD技能文件未找到: $TARGET_FILE${NC}"
    echo -e "${GREEN}✓ 技能包未安装${NC}"
    exit 0
fi

# 确认卸载
echo -e "${YELLOW}即将卸载CI/CD流水线技能包${NC}"
echo -e "  文件: $(basename "$TARGET_FILE")"
echo -e "  路径: $TARGET_FILE"
echo -e "  大小: $(du -h "$TARGET_FILE" | cut -f1)"

read -p "确定要卸载吗? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}卸载已取消${NC}"
    exit 0
fi

# 执行卸载
echo -e "${BLUE}卸载CI/CD设计技能...${NC}"
rm -f "$TARGET_FILE"

# 验证卸载
if [ ! -f "$TARGET_FILE" ]; then
    echo -e "${GREEN}✓ CI/CD技能包已成功卸载${NC}"
else
    echo -e "${RED}✗ 卸载失败: 文件仍然存在${NC}"
    exit 1
fi

# 可选: 检查技能目录是否为空
SKILL_COUNT=$(ls -1 "$SKILLS_DIR" 2>/dev/null | wc -l || echo "0")
if [ "$SKILL_COUNT" -eq 0 ]; then
    echo -e "${YELLOW}提示: 技能目录现在为空${NC}"
    echo -e "      你可以安全地删除目录: ${YELLOW}rm -rf $SKILLS_DIR${NC}"
fi

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  卸载完成!${NC}"
echo -e "${GREEN}========================================${NC}"

echo -e "\n${BLUE}注意事项:${NC}"
echo -e "  1. 如果当前在AI Assistant会话中，技能可能仍然在内存中"
echo -e "  2. 使用 ${YELLOW}/clear${NC} 命令清除会话缓存"
echo -e "  3. 重新启动AI Assistant以完全移除技能"