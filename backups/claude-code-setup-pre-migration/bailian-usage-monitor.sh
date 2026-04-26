#!/bin/bash

# 百炼PRO套餐使用监控脚本
# 监控90,000次/月套餐使用情况，智能路由到备用方案

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 配置
BAILIAN_MONTHLY_LIMIT=90000
BAILIAN_WARNING_THRESHOLD=0.9  # 90%警告阈值
BAILIAN_CRITICAL_THRESHOLD=0.95 # 95%临界阈值
USAGE_DATA_DIR="$HOME/.claude/bailian-usage"
USAGE_FILE="$USAGE_DATA_DIR/usage.csv"
DAILY_FILE="$USAGE_DATA_DIR/daily_$(date +%Y-%m-%d).log"

# 初始化使用文件
init_usage_file() {
    mkdir -p "$USAGE_DATA_DIR"

    if [ ! -f "$USAGE_FILE" ]; then
        echo "date,requests,model,cumulative_requests,remaining_requests" > "$USAGE_FILE"
    fi
}

# 记录API调用
record_api_call() {
    local model="$1"

    init_usage_file

    local current_date=$(date +%Y-%m-%d)
    local current_time=$(date +%H:%M:%S)

    # 读取当前累计请求数
    local cumulative_requests=0
    if [ -f "$USAGE_FILE" ] && [ $(wc -l < "$USAGE_FILE") -gt 1 ]; then
        cumulative_requests=$(tail -n +2 "$USAGE_FILE" | awk -F',' '{sum+=$2} END {print sum}')
    fi

    # 增加一次请求
    cumulative_requests=$((cumulative_requests + 1))
    local remaining_requests=$((BAILIAN_MONTHLY_LIMIT - cumulative_requests))

    # 记录到CSV文件
    echo "$current_date $current_time,1,$model,$cumulative_requests,$remaining_requests" >> "$USAGE_FILE"

    # 记录到每日日志
    echo "[$current_date $current_time] $model请求 - 累计: $cumulative_requests, 剩余: $remaining_requests" >> "$DAILY_FILE"

    echo "$cumulative_requests"
}

# 检查使用率，决定是否切换到备用方案
check_usage_and_route() {
    init_usage_file

    local cumulative_requests=0
    if [ -f "$USAGE_FILE" ] && [ $(wc -l < "$USAGE_FILE") -gt 1 ]; then
        cumulative_requests=$(tail -n +2 "$USAGE_FILE" | awk -F',' '{sum+=$2} END {print sum}')
    fi

    local usage_percent=$(echo "scale=2; $cumulative_requests / $BAILIAN_MONTHLY_LIMIT * 100" | bc)
    local remaining_requests=$((BAILIAN_MONTHLY_LIMIT - cumulative_requests))

    # 输出使用情况
    echo -e "${CYAN}📊 百炼PRO套餐使用情况${NC}"
    echo "========================================================"
    echo "• 月度限额: $BAILIAN_MONTHLY_LIMIT 次"
    echo "• 已使用: $cumulative_requests 次"
    echo "• 剩余: $remaining_requests 次"
    echo "• 使用率: ${usage_percent}%"
    echo ""

    # 检查阈值
    if (( $(echo "$usage_percent >= $BAILIAN_CRITICAL_THRESHOLD * 100" | bc -l) )); then
        echo -e "${RED}🚨 临界警告: 使用率超过95%，建议立即切换到备用方案${NC}"
        return 2  # 需要切换到备用方案
    elif (( $(echo "$usage_percent >= $BAILIAN_WARNING_THRESHOLD * 100" | bc -l) )); then
        echo -e "${YELLOW}⚠️  警告: 使用率超过90%，接近套餐限额${NC}"
        return 1  # 警告状态
    else
        echo -e "${GREEN}✅ 使用率正常，可继续使用百炼PRO${NC}"
        return 0  # 正常状态
    fi
}

# 获取推荐模型
get_recommended_model() {
    check_usage_and_route
    local usage_status=$?

    case $usage_status in
        0)
            # 正常状态，推荐百炼PRO模型
            echo "deepseek-r1"  # 默认推荐DeepSeek-R1
            ;;
        1)
            # 警告状态，建议开始考虑备用方案
            echo "deepseek-r1"  # 仍可使用百炼PRO，但需注意
            ;;
        2)
            # 临界状态，推荐切换到备用方案
            echo "deepseek-reasoner"  # 切换到DeepSeek-reasoner
            ;;
        *)
            echo "deepseek-r1"
            ;;
    esac
}

# 生成使用报告
generate_usage_report() {
    init_usage_file

    local cumulative_requests=0
    local monthly_usage=""

    if [ -f "$USAGE_FILE" ] && [ $(wc -l < "$USAGE_FILE") -gt 1 ]; then
        cumulative_requests=$(tail -n +2 "$USAGE_FILE" | awk -F',' '{sum+=$2} END {print sum}')
        monthly_usage=$(tail -n +2 "$USAGE_FILE" | head -20)  # 最近20条记录
    fi

    local usage_percent=$(echo "scale=2; $cumulative_requests / $BAILIAN_MONTHLY_LIMIT * 100" | bc)
    local remaining_requests=$((BAILIAN_MONTHLY_LIMIT - cumulative_requests))
    local days_in_month=$(date -d "$(date +%Y-%m-01) +1 month -1 day" +%d)
    local days_passed=$(date +%d)
    local daily_average=$(echo "scale=2; $cumulative_requests / $days_passed" | bc)
    local projected_monthly=$(echo "scale=0; $daily_average * $days_in_month" | bc)

    echo -e "${BLUE}📈 百炼PRO使用分析报告${NC}"
    echo "========================================================"
    echo "📅 报告时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    echo "📊 使用统计:"
    echo "• 月度限额: $BAILIAN_MONTHLY_LIMIT 次"
    echo "• 已使用: $cumulative_requests 次"
    echo "• 剩余: $remaining_requests 次"
    echo "• 使用率: ${usage_percent}%"
    echo ""
    echo "📈 趋势分析:"
    echo "• 本月已过天数: $days_passed 天"
    echo "• 日均使用: $daily_average 次/天"
    echo "• 月度预测: $projected_monthly 次 (基于当前速度)"
    echo ""

    # 预警分析
    if (( $(echo "$projected_monthly > $BAILIAN_MONTHLY_LIMIT" | bc -l) )); then
        echo -e "${RED}🚨 预测超额: 按当前速度将超出套餐限额${NC}"
        local overage=$(echo "$projected_monthly - $BAILIAN_MONTHLY_LIMIT" | bc)
        echo "   预计超额: $overage 次"
        echo "   建议: 控制使用速度或准备备用方案"
    elif (( $(echo "$projected_monthly > $BAILIAN_MONTHLY_LIMIT * 0.9" | bc -l) )); then
        echo -e "${YELLOW}⚠️  预测接近限额: 按当前速度将接近套餐限额${NC}"
        echo "   建议: 监控使用情况，考虑优化策略"
    else
        echo -e "${GREEN}✅ 使用速度正常，预计不会超出限额${NC}"
    fi

    echo ""
    echo "🔄 最近使用记录:"
    if [ -n "$monthly_usage" ]; then
        echo "$monthly_usage" | while IFS= read -r line; do
            echo "  $line"
        done
    else
        echo "  暂无使用记录"
    fi
}

# 重置使用计数（谨慎使用）
reset_usage() {
    local confirm
    echo -e "${RED}⚠️  警告: 这将重置所有使用记录${NC}"
    read -p "确认重置? (输入'YES'确认): " confirm

    if [ "$confirm" = "YES" ]; then
        rm -f "$USAGE_FILE" "$USAGE_DATA_DIR"/daily_*.log
        echo -e "${GREEN}✅ 使用记录已重置${NC}"
    else
        echo -e "${YELLOW}❌ 重置已取消${NC}"
    fi
}

# 主函数
main() {
    case "${1:-}" in
        "check")
            check_usage_and_route
            ;;
        "record")
            record_api_call "${2:-deepseek-r1}"
            ;;
        "recommend")
            get_recommended_model
            ;;
        "report")
            generate_usage_report
            ;;
        "reset")
            reset_usage
            ;;
        *)
            echo -e "${CYAN}🤖 百炼PRO套餐使用监控工具${NC}"
            echo "========================================================"
            echo ""
            echo "使用方法:"
            echo "  ./bailian-usage-monitor.sh [命令]"
            echo ""
            echo "命令:"
            echo "  check                   检查使用率并输出状态"
            echo "  record [模型]          记录一次API调用"
            echo "  recommend              获取推荐模型"
            echo "  report                 生成详细使用报告"
            echo "  reset                  重置使用计数（谨慎使用）"
            echo ""
            echo "示例:"
            echo "  ./bailian-usage-monitor.sh check"
            echo "  ./bailian-usage-monitor.sh record deepseek-r1"
            echo "  ./bailian-usage-monitor.sh report"
            echo ""
            check_usage_and_route
            ;;
    esac
}

# 运行主函数
main "$@"