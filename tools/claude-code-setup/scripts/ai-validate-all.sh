#!/bin/bash
# =============================================================================
# AI 全量模型验证脚本 - 逐个测试所有配置的模型
# 用法: bash scripts/ai-validate-all.sh [bailian|deepseek|all]
# =============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VALIDATE_SCRIPT="$SCRIPT_DIR/ai-validate-model.sh"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ---------------------------------------------------------------------------
# 模型列表
# ---------------------------------------------------------------------------
BAILIAN_MODELS=("qwen-max" "qwen-plus" "qwen-turbo" "qwen-coder-plus" "qwen-long" "qwen3-235B-A22B" "qwen3.6-plus")
DEEPSEEK_MODELS=("deepseek-chat" "deepseek-coder")

# ---------------------------------------------------------------------------
# 加载密钥
# ---------------------------------------------------------------------------
if [ -f "$HOME/.config/secret-env/load-keychain-secrets.sh" ]; then
    source "$HOME/.config/secret-env/load-keychain-secrets.sh"
fi

# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
TARGET="${1:-all}"

echo -e "${BOLD}${BLUE}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║${NC}  ${BOLD}AI 全量模型验证${NC}                                    ${BOLD}${BLUE}║${NC}"
echo -e "${BOLD}${BLUE}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  测试目标: ${BOLD}$TARGET${NC}"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 报告文件
REPORT_FILE="$SCRIPT_DIR/../config/ai-config/validation-report-$(date +%Y%m%d_%H%M%S).md"
echo "# AI 模型验证报告" > "$REPORT_FILE"
echo "生成时间: $(date '+%Y-%m-%d %H:%M:%S')" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "| 模型 | 状态 | 通过/总测试 | 详情 |" >> "$REPORT_FILE"
echo "|------|------|------------|------|" >> "$REPORT_FILE"

TOTAL_ALL=0
PASSED_ALL=0
FAILED_ALL=0
SKIPPED_ALL=0

run_model_test() {
    local model="$1"
    local result_file="/tmp/ai-validate-${model//\//-}-$(date +%s).txt"

    echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}🧪 测试模型: $model${NC}"
    echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    bash "$VALIDATE_SCRIPT" "$model" > "$result_file" 2>&1
    local exit_code=$?

    # 显示输出
    cat "$result_file"

    # 提取统计信息
    local passed total status
    passed=$(grep -oP '通过: \K[0-9]+' "$result_file" || echo "0")
    total=$(grep -oP '总计: \K[0-9]+' "$result_file" || echo "0")
    if [ $exit_code -eq 0 ]; then
        status="✅ 通过"
    else
        status="❌ 失败"
    fi

    # 写入报告
    echo "| $model | $status | $passed/$total | [详情](#$(echo $model | tr 'A-Z' 'a-z')) |" >> "$REPORT_FILE"

    TOTAL_ALL=$((TOTAL_ALL + total))
    PASSED_ALL=$((PASSED_ALL + passed))
    FAILED_ALL=$((FAILED_ALL + total - passed))

    rm -f "$result_file"
    echo ""
}

# 检查适配器是否运行（百炼模型需要）
ADAPTER_RUNNING=false
if curl -s --connect-timeout 3 http://127.0.0.1:8080/health > /dev/null 2>&1; then
    ADAPTER_RUNNING=true
    echo -e "${GREEN}ℹ️  DashScope 适配器已运行${NC}"
else
    echo -e "${YELLOW}⚠️  DashScope 适配器未运行，百炼模型测试将部分失败${NC}"
    echo -e "${YELLOW}   启动: python3 /Users/frankie/claude-code-setup/dashscope-adapter.py &${NC}"
    echo ""
fi

case "$TARGET" in
    bailian|百炼)
        echo -e "${BOLD}${BLUE}━━━ 百炼模型测试 ━━━${NC}"
        echo "" >> "$REPORT_FILE"
        echo "## 百炼模型" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
        for model in "${BAILIAN_MODELS[@]}"; do
            run_model_test "$model"
        done
        ;;
    deepseek|DeepSeek)
        echo -e "${BOLD}${BLUE}━━━ DeepSeek 模型测试 ━━━${NC}"
        echo "" >> "$REPORT_FILE"
        echo "## DeepSeek 模型" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
        for model in "${DEEPSEEK_MODELS[@]}"; do
            run_model_test "$model"
        done
        ;;
    all|全部)
        echo -e "${BOLD}${BLUE}━━━ 百炼模型测试 ━━━${NC}"
        echo "" >> "$REPORT_FILE"
        echo "## 百炼模型" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
        for model in "${BAILIAN_MODELS[@]}"; do
            run_model_test "$model"
        done

        echo -e "${BOLD}${BLUE}━━━ DeepSeek 模型测试 ━━━${NC}"
        echo "" >> "$REPORT_FILE"
        echo "## DeepSeek 模型" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
        for model in "${DEEPSEEK_MODELS[@]}"; do
            run_model_test "$model"
        done
        ;;
    *)
        echo -e "${RED}用法: $0 [bailian|deepseek|all]${NC}"
        exit 1
        ;;
esac

# 总结
echo -e "${BOLD}${BLUE}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║${NC}  ${BOLD}全量验证总结${NC}                                        ${BOLD}${BLUE}║${NC}"
echo -e "${BOLD}${BLUE}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  总测试数: ${BOLD}$TOTAL_ALL${NC}"
echo -e "  总通过: ${GREEN}$PASSED_ALL${NC}"
echo -e "  总失败: ${RED}$FAILED_ALL${NC}"
echo ""

if [ $FAILED_ALL -eq 0 ]; then
    echo -e "  ${GREEN}${BOLD}✅ 所有模型验证通过！${NC}"
else
    echo -e "  ${RED}${BOLD}❌ 有 $FAILED_ALL 项测试失败${NC}"
fi

echo ""
echo -e "  📋 详细报告: ${BOLD}$REPORT_FILE${NC}"

# 写入报告总结
echo "" >> "$REPORT_FILE"
echo "---" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "## 总结" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "- 总测试数: $TOTAL_ALL" >> "$REPORT_FILE"
echo "- 总通过: $PASSED_ALL" >> "$REPORT_FILE"
echo "- 总失败: $FAILED_ALL" >> "$REPORT_FILE"

exit $FAILED_ALL