#!/bin/bash
# MAREF生产环境备份脚本
# 支持每日自动备份和手动备份

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 默认配置
BACKUP_DIR="/backup/maref"
DB_PATH="/Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db"
CONFIG_DIR="config"
LOG_FILE="logs/backup_$(date +%Y%m%d).log"

# 参数解析
MODE="daily"
VERBOSE=false
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --mode)
            MODE="$2"
            shift 2
            ;;
        --backup-dir)
            BACKUP_DIR="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --help)
            echo "使用方法: $0 [选项]"
            echo "选项:"
            echo "  --mode <daily|weekly|monthly>  备份模式 (默认: daily)"
            echo "  --backup-dir <目录>            备份目录 (默认: $BACKUP_DIR)"
            echo "  --verbose                      详细输出"
            echo "  --force                        强制覆盖现有备份"
            echo "  --help                         显示此帮助信息"
            exit 0
            ;;
        *)
            echo "未知选项: $1"
            exit 1
            ;;
    esac
done

# 日志函数
log_message() {
    local level="$1"
    local message="$2"
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

# 检查备份目录
if [ ! -d "$BACKUP_DIR" ]; then
    log_message "INFO" "创建备份目录: $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"
    if [ $? -ne 0 ]; then
        log_message "ERROR" "无法创建备份目录: $BACKUP_DIR"
        exit 1
    fi
fi

# 检查数据库文件
if [ ! -f "$DB_PATH" ]; then
    log_message "ERROR" "数据库文件不存在: $DB_PATH"
    exit 1
fi

# 生成备份文件名
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
if [ "$MODE" = "daily" ]; then
    BACKUP_FILE="$BACKUP_DIR/maref_memory_${TIMESTAMP}_daily.db"
    RETENTION_DAYS=7
elif [ "$MODE" = "weekly" ]; then
    BACKUP_FILE="$BACKUP_DIR/maref_memory_${TIMESTAMP}_weekly.db"
    RETENTION_DAYS=28
elif [ "$MODE" = "monthly" ]; then
    BACKUP_FILE="$BACKUP_DIR/maref_memory_${TIMESTAMP}_monthly.db"
    RETENTION_DAYS=90
else
    log_message "ERROR" "无效的备份模式: $MODE (必须是 daily, weekly, monthly)"
    exit 1
fi

# 检查备份文件是否已存在
if [ -f "$BACKUP_FILE" ] && [ "$FORCE" = false ]; then
    log_message "ERROR" "备份文件已存在: $BACKUP_FILE (使用 --force 覆盖)"
    exit 1
fi

log_message "INFO" "开始MAREF生产环境备份"
log_message "INFO" "模式: $MODE"
log_message "INFO" "数据库: $DB_PATH"
log_message "INFO" "备份文件: $BACKUP_FILE"

# 1. 停止MAREF服务（可选）
log_message "INFO" "检查MAREF服务状态..."
if ps aux | grep -q -E "run_maref_daily|maref_monitor" | grep -v grep; then
    log_message "WARNING" "MAREF服务正在运行，建议在备份前停止服务"
    read -p "是否停止MAREF服务? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_message "INFO" "停止MAREF服务..."
        ./stop_maref_production.sh
        sleep 2
    else
        log_message "INFO" "继续备份（服务正在运行）"
    fi
fi

# 2. 备份数据库
log_message "INFO" "备份数据库..."
cp "$DB_PATH" "$BACKUP_FILE"
if [ $? -ne 0 ]; then
    log_message "ERROR" "数据库备份失败"
    exit 1
fi

BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
log_message "INFO" "数据库备份完成: $BACKUP_FILE ($BACKUP_SIZE)"

# 3. 备份配置文件
CONFIG_BACKUP="$BACKUP_DIR/maref_config_${TIMESTAMP}.tar.gz"
log_message "INFO" "备份配置文件..."
tar -czf "$CONFIG_BACKUP" "$CONFIG_DIR"/*.py 2>/dev/null || true
CONFIG_SIZE=$(du -h "$CONFIG_BACKUP" 2>/dev/null | cut -f1 || echo "N/A")
log_message "INFO" "配置文件备份完成: $CONFIG_BACKUP ($CONFIG_SIZE)"

# 4. 验证备份完整性
log_message "INFO" "验证备份完整性..."
sqlite3 "$BACKUP_FILE" "PRAGMA integrity_check;" > /tmp/backup_check.txt 2>&1
if grep -q "ok" /tmp/backup_check.txt; then
    log_message "INFO" "备份完整性检查通过"
else
    log_message "ERROR" "备份完整性检查失败:"
    cat /tmp/backup_check.txt >> "$LOG_FILE"
    exit 1
fi

# 5. 清理旧备份
log_message "INFO" "清理过期备份 (保留策略: ${RETENTION_DAYS}天)..."
find "$BACKUP_DIR" -name "maref_memory_*_${MODE}.db" -mtime +${RETENTION_DAYS} -type f -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "maref_config_*.tar.gz" -mtime +${RETENTION_DAYS} -type f -delete 2>/dev/null || true

BACKUP_COUNT=$(find "$BACKUP_DIR" -name "maref_memory_*_${MODE}.db" -type f | wc -l)
log_message "INFO" "当前${MODE}备份数量: $BACKUP_COUNT"

# 6. 记录备份元数据
META_FILE="$BACKUP_DIR/backup_metadata.json"
if [ ! -f "$META_FILE" ]; then
    echo "{\"backups\": []}" > "$META_FILE"
fi

python3 -c "
import json
import os
import sys

meta_file = '$META_FILE'
backup_info = {
    'timestamp': '$TIMESTAMP',
    'mode': '$MODE',
    'database_file': '$BACKUP_FILE',
    'config_file': '$CONFIG_BACKUP',
    'size_mb': os.path.getsize('$BACKUP_FILE') / (1024 * 1024) if os.path.exists('$BACKUP_FILE') else 0,
    'integrity_checked': True
}

try:
    with open(meta_file, 'r') as f:
        data = json.load(f)
except:
    data = {'backups': []}

data['backups'].insert(0, backup_info)
# 保留最近100条记录
data['backups'] = data['backups'][:100]

with open(meta_file, 'w') as f:
    json.dump(data, f, indent=2)
"

log_message "INFO" "备份元数据已更新: $META_FILE"

# 7. 重启服务（如果之前停止了）
if [ "$REPLY" =~ ^[Yy]$ ]; then
    log_message "INFO" "重启MAREF服务..."
    ./start_maref_production.sh
fi

log_message "INFO" "MAREF生产环境备份完成"
log_message "INFO" "备份文件: $BACKUP_FILE"
log_message "INFO" "日志文件: $LOG_FILE"

echo "✅ 备份完成: $BACKUP_FILE"
exit 0