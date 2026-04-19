#!/bin/bash
# 设置周度监控cron任务
# 此脚本显示cron配置，用户可手动添加到crontab

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== MAREF周度监控cron任务设置 ==="
echo ""
echo "以下cron任务可用于定期执行MAREF稳定性监控："
echo ""

# 周度监控（每周一凌晨2点）
echo "# 每周执行24小时稳定性监控"
echo "0 2 * * 1 cd /Volumes/1TB-M2/openclaw/scripts/clawra && ./run_weekly_stability_monitor.sh >> logs/weekly_monitor_cron.log 2>&1"
echo ""

# 日志管理（每天凌晨1点）
echo "# 每天执行日志管理"
echo "0 1 * * * cd /Volumes/1TB-M2/openclaw/scripts/clawra && ./manage_maref_logs.sh --action cleanup --days 90 >> logs/log_management_cron.log 2>&1"
echo ""

# 备份任务（基于运维计划）
echo "# 每日备份（凌晨3点）"
echo "0 3 * * * cd /Volumes/1TB-M2/openclaw/scripts/clawra && ./backup_maref_production.sh --mode daily --backup-dir ./backup/maref >> logs/backup_cron.log 2>&1"
echo ""
echo "# 每周完整备份（周日凌晨2点）"
echo "0 2 * * 0 cd /Volumes/1TB-M2/openclaw/scripts/clawra && ./backup_maref_production.sh --mode weekly --backup-dir ./backup/maref >> logs/backup_cron.log 2>&1"
echo ""
echo "# 每月完整备份（每月1日凌晨1点）"
echo "0 1 1 * * cd /Volumes/1TB-M2/openclaw/scripts/clawra && ./backup_maref_production.sh --mode monthly --backup-dir ./backup/maref >> logs/backup_cron.log 2>&1"
echo ""

echo "=== 安装说明 ==="
echo ""
echo "1. 查看当前cron任务:"
echo "   crontab -l"
echo ""
echo "2. 添加以上任务到crontab:"
echo "   crontab -e"
echo ""
echo "3. 将所需行复制粘贴到编辑器中，保存并退出"
echo ""
echo "4. 验证cron任务:"
echo "   crontab -l"
echo ""
echo "5. 测试周度监控脚本:"
echo "   ./run_weekly_stability_monitor.sh --help"
echo ""
echo "注意："
echo "- 确保所有脚本具有执行权限: chmod +x *.sh"
echo "- 首次运行建议手动测试脚本"
echo "- 监控日志将保存在 logs/weekly_monitor/ 目录"
echo "- 备份文件将保存在 backup/maref/ 目录"
echo ""

# 可选：自动添加cron任务（需要用户确认）
if [[ "$1" == "--auto-install" ]]; then
    read -p "是否自动添加cron任务？(y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "正在添加cron任务..."
        (crontab -l 2>/dev/null; echo "") | crontab -
        (crontab -l; echo "# MAREF周度监控（每周一凌晨2点）") | crontab -
        (crontab -l; echo "0 2 * * 1 cd /Volumes/1TB-M2/openclaw/scripts/clawra && ./run_weekly_stability_monitor.sh >> logs/weekly_monitor_cron.log 2>&1") | crontab -
        (crontab -l; echo "# MAREF日志管理（每天凌晨1点）") | crontab -
        (crontab -l; echo "0 1 * * * cd /Volumes/1TB-M2/openclaw/scripts/clawra && ./manage_maref_logs.sh --action cleanup --days 90 >> logs/log_management_cron.log 2>&1") | crontab -
        echo "✅ cron任务已添加"
        echo "当前cron任务:"
        crontab -l
    else
        echo "已跳过自动安装"
    fi
fi

echo "✅ cron配置生成完成"