#!/bin/bash
# MAREF日志管理脚本
# 支持日志轮转、清理和状态查看

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LOG_DIR="logs"
ACTION="status"
DAYS_TO_KEEP=90
FORCE=false

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 参数解析
while [[ $# -gt 0 ]]; do
    case $1 in
        --action)
            ACTION="$2"
            shift 2
            ;;
        --days)
            DAYS_TO_KEEP="$2"
            shift 2
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --help)
            echo "使用方法: $0 [选项]"
            echo "选项:"
            echo "  --action <status|rotate|cleanup|stats>  执行的操作 (默认: status)"
            echo "  --days <天数>                          清理时保留的天数 (默认: 90)"
            echo "  --force                                强制执行操作"
            echo "  --help                                 显示此帮助信息"
            echo ""
            echo "操作说明:"
            echo "  status   显示日志状态 (默认)"
            echo "  rotate   手动轮转日志"
            echo "  cleanup  清理旧日志"
            echo "  stats    显示日志统计信息"
            exit 0
            ;;
        *)
            echo "未知选项: $1"
            exit 1
            ;;
    esac
done

# 检查日志目录
if [ ! -d "$LOG_DIR" ]; then
    echo -e "${RED}❌ 日志目录不存在: $LOG_DIR${NC}"
    exit 1
fi

# 显示日志状态
show_status() {
    echo -e "${BLUE}=== MAREF日志状态 ===${NC}"
    echo "日志目录: $(pwd)/$LOG_DIR"

    # 主日志文件状态
    MAIN_LOG="$LOG_DIR/maref_production.log"
    if [ -f "$MAIN_LOG" ]; then
        SIZE=$(du -h "$MAIN_LOG" | cut -f1)
        LINES=$(wc -l < "$MAIN_LOG" 2>/dev/null || echo "N/A")
        MOD_TIME=$(stat -f "%Sm" "$MAIN_LOG" 2>/dev/null || stat -c "%y" "$MAIN_LOG")
        echo -e "${GREEN}✅ 主日志文件:${NC}"
        echo "  路径: $MAIN_LOG"
        echo "  大小: $SIZE"
        echo "  行数: $LINES"
        echo "  修改时间: $MOD_TIME"
    else
        echo -e "${YELLOW}⚠️  主日志文件不存在${NC}"
    fi

    # 轮转文件
    echo -e "\n${BLUE}轮转日志文件:${NC}"
    ROTATED_LOGS=$(find "$LOG_DIR" -name "*.log.*" -o -name "*.log.[0-9]" -o -name "*.log.[0-9].gz" 2>/dev/null | sort)
    if [ -z "$ROTATED_LOGS" ]; then
        echo "  无轮转日志"
    else
        COUNT=0
        for log in $ROTATED_LOGS; do
            COUNT=$((COUNT + 1))
            SIZE=$(du -h "$log" | cut -f1)
            MOD_TIME=$(stat -f "%Sm" "$log" 2>/dev/null || stat -c "%y" "$log")
            echo "  $COUNT. $(basename "$log") ($SIZE, $MOD_TIME)"
        done
        echo "  总计: $COUNT 个轮转文件"
    fi

    # 按日期命名的日志文件
    echo -e "\n${BLUE}按日期命名的日志文件:${NC}"
    DATE_LOGS=$(find "$LOG_DIR" -name "*_*.log" -o -name "*_*.log.gz" 2>/dev/null | grep -E "(startup_|monitor_|daily_report_|backup_)" | sort -r | head -10)
    if [ -z "$DATE_LOGS" ]; then
        echo "  无日期日志文件"
    else
        for log in $DATE_LOGS; do
            SIZE=$(du -h "$log" 2>/dev/null | cut -f1 || echo "N/A")
            MOD_TIME=$(stat -f "%Sm" "$log" 2>/dev/null || stat -c "%y" "$log")
            echo "  $(basename "$log") ($SIZE, $MOD_TIME)"
        done
    fi

    # 目录总大小
    TOTAL_SIZE=$(du -sh "$LOG_DIR" | cut -f1)
    echo -e "\n${BLUE}日志目录总大小:${NC} $TOTAL_SIZE"
}

# 手动轮转日志
rotate_logs() {
    echo -e "${BLUE}=== 手动轮转日志 ===${NC}"

    MAIN_LOG="$LOG_DIR/maref_production.log"
    if [ ! -f "$MAIN_LOG" ]; then
        echo -e "${YELLOW}⚠️  主日志文件不存在，无需轮转${NC}"
        return 0
    fi

    # 检查日志是否在写入中
    if lsof "$MAIN_LOG" >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  日志文件正在被进程使用${NC}"
        if [ "$FORCE" = false ]; then
            read -p "是否继续轮转? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo -e "${YELLOW}取消轮转${NC}"
                return 0
            fi
        fi
    fi

    # 创建轮转文件
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    ROTATED_LOG="$LOG_DIR/maref_production.log.$TIMESTAMP"

    echo "轮转日志: $MAIN_LOG → $ROTATED_LOG"
    cp "$MAIN_LOG" "$ROTATED_LOG"

    if [ $? -eq 0 ]; then
        # 清空原日志文件
        > "$MAIN_LOG"
        echo -e "${GREEN}✅ 日志轮转完成${NC}"
        echo "  原文件: $MAIN_LOG (已清空)"
        echo "  轮转文件: $ROTATED_LOG"

        # 压缩旧轮转文件
        compress_old_logs
    else
        echo -e "${RED}❌ 日志轮转失败${NC}"
        return 1
    fi
}

# 压缩旧日志文件
compress_old_logs() {
    echo -e "\n${BLUE}压缩旧日志文件...${NC}"

    # 找到未压缩的旧日志文件（超过1天）
    OLD_LOGS=$(find "$LOG_DIR" -name "*.log.*" -mtime +1 ! -name "*.gz" -type f 2>/dev/null)

    if [ -z "$OLD_LOGS" ]; then
        echo "  无需要压缩的旧日志"
        return 0
    fi

    COUNT=0
    for log in $OLD_LOGS; do
        echo "  压缩: $(basename "$log")"
        gzip -f "$log" 2>/dev/null && COUNT=$((COUNT + 1)) || echo "  压缩失败: $log"
    done

    echo -e "${GREEN}✅ 压缩完成: $COUNT 个文件${NC}"
}

# 清理旧日志
cleanup_logs() {
    echo -e "${BLUE}=== 清理旧日志 ===${NC}"
    echo "保留天数: $DAYS_TO_KEEP"

    # 确认
    if [ "$FORCE" = false ]; then
        echo -e "${YELLOW}即将删除 $LOG_DIR 中超过 $DAYS_TO_KEEP 天的日志文件${NC}"
        read -p "是否继续? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}取消清理${NC}"
            return 0
        fi
    fi

    # 清理旧文件
    echo "查找超过 $DAYS_TO_KEEP 天的日志文件..."

    # 1. 轮转日志文件
    ROTATED_TO_DELETE=$(find "$LOG_DIR" \( -name "*.log.*" -o -name "*.log.[0-9]" -o -name "*.log.[0-9].gz" \) -mtime +$DAYS_TO_KEEP -type f 2>/dev/null)

    # 2. 按日期命名的日志文件
    DATE_LOGS_TO_DELETE=$(find "$LOG_DIR" \( -name "*_*.log" -o -name "*_*.log.gz" \) -mtime +$DAYS_TO_KEEP -type f 2>/dev/null)

    ALL_TO_DELETE=$(echo "$ROTATED_TO_DELETE" "$DATE_LOGS_TO_DELETE" | tr '\n' ' ' | xargs)

    if [ -z "$ALL_TO_DELETE" ]; then
        echo -e "${GREEN}✅ 无需要清理的旧日志${NC}"
        return 0
    fi

    echo "找到以下需要清理的文件:"
    for file in $ALL_TO_DELETE; do
        SIZE=$(du -h "$file" 2>/dev/null | cut -f1 || echo "N/A")
        MOD_TIME=$(stat -f "%Sm" "$file" 2>/dev/null || stat -c "%y" "$file")
        echo "  $(basename "$file") ($SIZE, $MOD_TIME)"
    done

    # 执行删除
    DELETED_COUNT=0
    for file in $ALL_TO_DELETE; do
        rm -f "$file"
        if [ $? -eq 0 ]; then
            DELETED_COUNT=$((DELETED_COUNT + 1))
            echo "  已删除: $(basename "$file")"
        else
            echo "  删除失败: $(basename "$file")"
        fi
    done

    echo -e "${GREEN}✅ 清理完成: 删除了 $DELETED_COUNT 个文件${NC}"

    # 更新目录大小
    TOTAL_SIZE=$(du -sh "$LOG_DIR" | cut -f1)
    echo "日志目录当前大小: $TOTAL_SIZE"
}

# 显示日志统计信息
show_stats() {
    echo -e "${BLUE}=== 日志统计信息 ===${NC}"

    # 主日志统计
    MAIN_LOG="$LOG_DIR/maref_production.log"
    if [ -f "$MAIN_LOG" ]; then
        echo -e "${GREEN}主日志统计:${NC}"
        echo "  行数: $(wc -l < "$MAIN_LOG" 2>/dev/null || echo "N/A")"
        echo "  错误数: $(grep -i "error\|exception\|critical" "$MAIN_LOG" 2>/dev/null | wc -l || echo "0")"
        echo "  警告数: $(grep -i "warning" "$MAIN_LOG" 2>/dev/null | wc -l || echo "0")"
        echo "  最近错误:"
        grep -i "error\|exception\|critical" "$MAIN_LOG" 2>/dev/null | tail -5 | sed 's/^/    /'
    fi

    # 按错误类型统计
    echo -e "\n${GREEN}错误类型分布:${NC}"
    if [ -f "$MAIN_LOG" ]; then
        grep -i "error" "$MAIN_LOG" 2>/dev/null | grep -o "\[[^]]*\]" | sort | uniq -c | sort -rn | head -10 | sed 's/^/  /'
    fi

    # 按组件统计
    echo -e "\n${GREEN}组件日志统计:${NC}"
    if [ -f "$MAIN_LOG" ]; then
        grep -o " - [^ ]* - " "$MAIN_LOG" 2>/dev/null | cut -d' ' -f3 | sort | uniq -c | sort -rn | head -10 | sed 's/^/  /'
    fi
}

# 根据操作执行相应函数
case "$ACTION" in
    status)
        show_status
        ;;
    rotate)
        rotate_logs
        ;;
    cleanup)
        cleanup_logs
        ;;
    stats)
        show_stats
        ;;
    *)
        echo -e "${RED}❌ 未知操作: $ACTION${NC}"
        echo "可用操作: status, rotate, cleanup, stats"
        exit 1
        ;;
esac

exit 0