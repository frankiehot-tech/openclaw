#!/bin/bash

# CI/CD流水线技能包验证脚本
# 验证技能包完整性和安装状态

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  CI/CD流水线技能包验证脚本${NC}"
echo -e "${BLUE}========================================${NC}"

# 获取当前脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="$HOME/.claude/skills"
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# 验证函数
check() {
    local description="$1"
    local command="$2"
    local success_msg="${3:-✓ $description}"
    local failure_msg="${4:-✗ $description}"

    ((TOTAL_CHECKS++))
    if eval "$command" >/dev/null 2>&1; then
        echo -e "  ${GREEN}$success_msg${NC}"
        ((PASSED_CHECKS++))
        return 0
    else
        echo -e "  ${RED}$failure_msg${NC}"
        ((FAILED_CHECKS++))
        return 1
    fi
}

echo -e "${BLUE}1. 验证技能包源文件...${NC}"

# 检查主要技能文件
check "技能文件存在" "test -f '$SCRIPT_DIR/ci-cd-designer.md'"
check "技能文件可读" "test -r '$SCRIPT_DIR/ci-cd-designer.md'"
check "技能文件有有效内容" "test -s '$SCRIPT_DIR/ci-cd-designer.md'"

# 检查YAML frontmatter格式
if check "技能文件有YAML frontmatter" "head -n 5 '$SCRIPT_DIR/ci-cd-designer.md' | grep -q -- '---'"; then
    check "frontmatter包含name字段" "grep -q '^name:' '$SCRIPT_DIR/ci-cd-designer.md'"
    check "frontmatter包含description字段" "grep -q '^description:' '$SCRIPT_DIR/ci-cd-designer.md'"
fi

echo -e "\n${BLUE}2. 验证模板文件...${NC}"

# 检查各目录是否存在
check "GitHub Actions目录" "test -d '$SCRIPT_DIR/github-actions'"
check "GitLab CI目录" "test -d '$SCRIPT_DIR/gitlab-ci'"
check "Jenkins目录" "test -d '$SCRIPT_DIR/jenkins'"
check "测试自动化目录" "test -d '$SCRIPT_DIR/test-automation'"
check "部署配置目录" "test -d '$SCRIPT_DIR/deployment'"

# 检查各目录下的文件数量
if [ -d "$SCRIPT_DIR/github-actions" ]; then
    GHA_COUNT=$(ls -1 "$SCRIPT_DIR/github-actions/"*.yml 2>/dev/null | wc -l)
    check "GitHub Actions模板文件" "test $GHA_COUNT -gt 0" "✓ GitHub Actions模板 ($GHA_COUNT 个文件)" "✗ GitHub Actions模板 (0 个文件)"
fi

if [ -d "$SCRIPT_DIR/gitlab-ci" ]; then
    GITLAB_COUNT=$(ls -1 "$SCRIPT_DIR/gitlab-ci/"*.yml 2>/dev/null | wc -l)
    check "GitLab CI模板文件" "test $GITLAB_COUNT -gt 0" "✓ GitLab CI模板 ($GITLAB_COUNT 个文件)" "✗ GitLab CI模板 (0 个文件)"
fi

if [ -d "$SCRIPT_DIR/jenkins" ]; then
    JENKINS_COUNT=$(ls -1 "$SCRIPT_DIR/jenkins/"Jenkinsfile-* 2>/dev/null | wc -l)
    check "Jenkins模板文件" "test $JENKINS_COUNT -gt 0" "✓ Jenkins模板 ($JENKINS_COUNT 个文件)" "✗ Jenkins模板 (0 个文件)"
fi

if [ -d "$SCRIPT_DIR/test-automation" ]; then
    TEST_COUNT=$(ls -1 "$SCRIPT_DIR/test-automation/"* 2>/dev/null | wc -l)
    check "测试自动化配置" "test $TEST_COUNT -gt 0" "✓ 测试自动化配置 ($TEST_COUNT 个文件)" "✗ 测试自动化配置 (0 个文件)"
fi

if [ -d "$SCRIPT_DIR/deployment" ]; then
    DEPLOYMENT_COUNT=$(find "$SCRIPT_DIR/deployment" -name "*.yml" -o -name "*.yaml" -o -name "*.json" | wc -l)
    check "部署配置模板" "test $DEPLOYMENT_COUNT -gt 0" "✓ 部署配置模板 ($DEPLOYMENT_COUNT 个文件)" "✗ 部署配置模板 (0 个文件)"
fi

echo -e "\n${BLUE}3. 验证安装脚本...${NC}"

check "安装脚本存在" "test -f '$SCRIPT_DIR/install.sh'"
check "安装脚本可执行" "test -x '$SCRIPT_DIR/install.sh'"
check "卸载脚本存在" "test -f '$SCRIPT_DIR/uninstall.sh'"
check "卸载脚本可执行" "test -x '$SCRIPT_DIR/uninstall.sh'"
check "更新脚本存在" "test -f '$SCRIPT_DIR/update-skills.sh'"
check "更新脚本可执行" "test -x '$SCRIPT_DIR/update-skills.sh'"
check "安装文档存在" "test -f '$SCRIPT_DIR/INSTALL.md'"

echo -e "\n${BLUE}4. 验证安装状态...${NC}"

if [ -d "$SKILLS_DIR" ]; then
    check "AI Assistant技能目录存在" "true" "✓ AI Assistant技能目录: $SKILLS_DIR"

    if [ -f "$SKILLS_DIR/ci-cd-designer.md" ]; then
        check "技能已安装" "true" "✓ CI/CD技能已安装"

        # 比较安装版本和源版本
        if [ -f "$SCRIPT_DIR/ci-cd-designer.md" ] && [ -f "$SKILLS_DIR/ci-cd-designer.md" ]; then
            if cmp -s "$SCRIPT_DIR/ci-cd-designer.md" "$SKILLS_DIR/ci-cd-designer.md"; then
                check "安装版本最新" "true" "✓ 安装版本是最新的"
            else
                check "安装版本最新" "false" "⚠ 安装版本不是最新的 (使用 update-skills.sh 更新)"
            fi
        fi
    else
        check "技能已安装" "false" "⚠ CI/CD技能未安装 (使用 install.sh 安装)"
    fi
else
    check "AI Assistant技能目录存在" "false" "⚠ AI Assistant技能目录不存在 (使用 install.sh 安装)"
fi

echo -e "\n${BLUE}5. 验证示例文件...${NC}"

check "示例目录存在" "test -d '$SCRIPT_DIR/examples'"
if [ -d "$SCRIPT_DIR/examples" ]; then
    EXAMPLE_COUNT=$(find "$SCRIPT_DIR/examples" -type f | wc -l)
    check "示例文件存在" "test $EXAMPLE_COUNT -gt 0" "✓ 示例文件 ($EXAMPLE_COUNT 个文件)" "✗ 示例文件 (0 个文件)"
fi

# 总结报告
echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}  验证结果摘要${NC}"
echo -e "${BLUE}========================================${NC}"

echo -e "  总检查项: $TOTAL_CHECKS"
echo -e "  通过: ${GREEN}$PASSED_CHECKS${NC}"
echo -e "  失败: ${RED}$FAILED_CHECKS${NC}"

if [ "$FAILED_CHECKS" -eq 0 ]; then
    echo -e "\n${GREEN}✓ 所有检查通过! CI/CD技能包完整且可用。${NC}"

    # 显示技能包信息
    echo -e "\n${BLUE}技能包信息:${NC}"
    echo -e "  名称: $(grep -m1 '^name:' "$SCRIPT_DIR/ci-cd-designer.md" | cut -d: -f2- | sed 's/^ *//' || echo '未指定')"
    echo -e "  描述: $(grep -m1 '^description:' "$SCRIPT_DIR/ci-cd-designer.md" | cut -d: -f2- | sed 's/^ *//' || echo '未指定')"
    echo -e "  版本: $(date -r "$SCRIPT_DIR/ci-cd-designer.md" "+%Y-%m-%d %H:%M:%S")"
    echo -e "  总文件数: $(find "$SCRIPT_DIR" -type f -not -path "*/\.*" | wc -l)"

    exit 0
else
    echo -e "\n${YELLOW}⚠ 发现 $FAILED_CHECKS 个问题${NC}"
    echo -e "\n${BLUE}建议操作:${NC}"

    if [ ! -f "$SCRIPT_DIR/ci-cd-designer.md" ]; then
        echo -e "  ${RED}• 主技能文件缺失，请检查项目完整性${NC}"
    fi

    if [ ! -d "$SKILLS_DIR" ] || [ ! -f "$SKILLS_DIR/ci-cd-designer.md" ]; then
        echo -e "  ${YELLOW}• 运行安装脚本: ${BLUE}./install.sh${NC}"
    fi

    if [ -f "$SCRIPT_DIR/ci-cd-designer.md" ] && [ -f "$SKILLS_DIR/ci-cd-designer.md" ] && ! cmp -s "$SCRIPT_DIR/ci-cd-designer.md" "$SKILLS_DIR/ci-cd-designer.md"; then
        echo -e "  ${YELLOW}• 运行更新脚本: ${BLUE}./update-skills.sh${NC}"
    fi

    echo -e "\n${YELLOW}详细验证日志已输出如上${NC}"
    exit 1
fi