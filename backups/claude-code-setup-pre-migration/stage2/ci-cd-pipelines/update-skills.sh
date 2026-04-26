#!/bin/bash

# CI/CD流水线技能包更新脚本
# 从源代码更新CI/CD设计技能到最新版本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  CI/CD流水线技能包更新脚本${NC}"
echo -e "${BLUE}========================================${NC}"

# 检查当前目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="$HOME/.claude/skills"
SOURCE_FILE="$SCRIPT_DIR/ci-cd-designer.md"
TARGET_FILE="$SKILLS_DIR/ci-cd-designer.md"

# 检查源文件是否存在
if [ ! -f "$SOURCE_FILE" ]; then
    echo -e "${RED}错误: 找不到源技能文件: $SOURCE_FILE${NC}"
    exit 1
fi

# 检查目标目录是否存在
if [ ! -d "$SKILLS_DIR" ]; then
    echo -e "${YELLOW}AI Assistant技能目录不存在: $SKILLS_DIR${NC}"
    echo -e "${BLUE}创建技能目录...${NC}"
    mkdir -p "$SKILLS_DIR"
fi

# 检查当前是否已安装
if [ ! -f "$TARGET_FILE" ]; then
    echo -e "${YELLOW}未找到已安装的CI/CD技能包${NC}"
    echo -e "${BLUE}执行全新安装...${NC}"
    "$SCRIPT_DIR/install.sh"
    exit $?
fi

# 显示版本信息
echo -e "${BLUE}检查当前安装...${NC}"
echo -e "  源文件: $(basename "$SOURCE_FILE")"
echo -e "  目标文件: $TARGET_FILE"

# 比较文件修改时间
SOURCE_MTIME=$(stat -f "%m" "$SOURCE_FILE" 2>/dev/null || stat -c "%Y" "$SOURCE_FILE")
TARGET_MTIME=$(stat -f "%m" "$TARGET_FILE" 2>/dev/null || stat -c "%Y" "$TARGET_FILE")

if [ "$SOURCE_MTIME" -le "$TARGET_MTIME" ]; then
    echo -e "${GREEN}✓ 技能包已经是最新版本${NC}"

    # 可选: 强制更新
    if [ "$1" = "--force" ]; then
        echo -e "${YELLOW}强制更新...${NC}"
    else
        echo -e "  源文件修改时间: $(date -r "$SOURCE_MTIME" "+%Y-%m-%d %H:%M:%S")"
        echo -e "  目标文件修改时间: $(date -r "$TARGET_MTIME" "+%Y-%m-%d %H:%M:%S")"
        echo -e "\n${BLUE}使用 --force 参数强制更新${NC}"
        exit 0
    fi
else
    echo -e "${YELLOW}发现新版本，准备更新...${NC}"
    echo -e "  源文件修改时间: $(date -r "$SOURCE_MTIME" "+%Y-%m-%d %H:%M:%S")"
    echo -e "  目标文件修改时间: $(date -r "$TARGET_MTIME" "+%Y-%m-%d %H:%M:%S")"
fi

# 备份当前文件
BACKUP_FILE="$TARGET_FILE.backup.$(date +%Y%m%d_%H%M%S)"
echo -e "\n${BLUE}创建备份...${NC}"
cp "$TARGET_FILE" "$BACKUP_FILE"
echo -e "${GREEN}✓ 备份已创建: $(basename "$BACKUP_FILE")${NC}"

# 执行更新
echo -e "${BLUE}更新技能文件...${NC}"
cp "$SOURCE_FILE" "$TARGET_FILE"
chmod 644 "$TARGET_FILE"

# 验证更新
if cmp -s "$SOURCE_FILE" "$TARGET_FILE"; then
    echo -e "${GREEN}✓ 技能包更新成功!${NC}"

    # 显示更新信息
    SOURCE_SIZE=$(du -h "$SOURCE_FILE" | cut -f1)
    TARGET_SIZE=$(du -h "$TARGET_FILE" | cut -f1)
    echo -e "  文件大小: $SOURCE_SIZE → $TARGET_SIZE"

    # 检查文件差异
    echo -e "\n${BLUE}更新摘要:${NC}"
    DIFF_LINES=$(diff -u "$BACKUP_FILE" "$TARGET_FILE" | grep -E "^[+-]" | grep -v -- "^---" | grep -v -- "^+++" | wc -l || echo "0")
    echo -e "  变更行数: $DIFF_LINES"

    if [ "$DIFF_LINES" -gt 0 ] && [ "$DIFF_LINES" -lt 50 ]; then
        echo -e "\n${YELLOW}主要变更:${NC}"
        diff -u "$BACKUP_FILE" "$TARGET_FILE" | grep -E "^[+-]" | grep -v -- "^---" | grep -v -- "^+++" | head -20
    fi
else
    echo -e "${RED}✗ 更新失败: 文件不一致${NC}"

    # 恢复备份
    echo -e "${YELLOW}恢复备份...${NC}"
    cp "$BACKUP_FILE" "$TARGET_FILE"
    rm -f "$BACKUP_FILE"
    exit 1
fi

# 清理旧备份（保留最近5个）
echo -e "\n${BLUE}清理旧备份...${NC}"
BACKUP_COUNT=$(ls -1 "$TARGET_FILE.backup."* 2>/dev/null | wc -l || echo "0")
if [ "$BACKUP_COUNT" -gt 5 ]; then
    ls -1t "$TARGET_FILE.backup."* | tail -n +6 | while read -r OLD_BACKUP; do
        echo -e "  删除: $(basename "$OLD_BACKUP")"
        rm -f "$OLD_BACKUP"
    done
    echo -e "${GREEN}✓ 已清理旧备份${NC}"
else
    echo -e "  当前备份数: $BACKUP_COUNT/5"
fi

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  更新完成! 请重启AI Assistant会话。${NC}"
echo -e "${GREEN}========================================${NC}"

# 显示使用说明
echo -e "\n${BLUE}后续步骤:${NC}"
echo -e "  1. 重启AI Assistant会话使更新生效"
echo -e "  2. 使用 ${YELLOW}/ci-cd-designer${NC} 测试新版本"
echo -e "  3. 查看更新日志: ${YELLOW}head -n 50 $SOURCE_FILE${NC}"

# 如果备份文件很大，提示用户
BACKUP_SIZE=$(du -h "$BACKUP_FILE" 2>/dev/null | cut -f1 || echo "0")
if [ "$BACKUP_SIZE" != "0" ] && [ "$BACKUP_SIZE" != "0B" ]; then
    echo -e "\n${YELLOW}提示: 备份文件大小: $BACKUP_SIZE${NC}"
    echo -e "      如需恢复旧版本: ${YELLOW}cp $BACKUP_FILE $TARGET_FILE${NC}"
fi