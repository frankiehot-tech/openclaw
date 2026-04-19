#!/bin/bash
# 设置MAREF性能监控cron任务
# 此脚本显示cron配置，用户可手动添加到crontab

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== MAREF性能监控cron任务设置 ==="
echo ""
echo "以下cron任务可用于定期执行MAREF性能监控："
echo ""

# 性能监控（每5分钟）
echo "# 每5分钟收集性能指标"
echo "*/5 * * * * /Volumes/1TB-M2/openclaw/scripts/clawra/run_performance_monitor_cron.sh"
echo ""

# 日度汇总（每天凌晨1点）
echo "# 每天执行性能数据汇总"
echo "0 1 * * * cd /Volumes/1TB-M2/openclaw/scripts/clawra && python3 collect_performance_metrics.py --mode summary --days 1 >> logs/performance_summary_cron.log 2>&1"
echo ""

# 周度分析（每周一凌晨2点）
echo "# 每周执行性能趋势分析"
echo "0 2 * * 1 cd /Volumes/1TB-M2/openclaw/scripts/clawra && python3 collect_performance_metrics.py --mode weekly-analysis >> logs/performance_weekly_cron.log 2>&1"
echo ""

echo "=== 安装说明 ==="
echo ""
echo "1. 查看当前cron任务:"
echo "   crontab -l"
echo ""
echo "2. 添加性能监控任务到crontab:"
echo "   crontab -e"
echo ""
echo "3. 将以下行复制粘贴到编辑器中:"
echo "   # MAREF性能监控（每5分钟）"
echo "   */5 * * * * /Volumes/1TB-M2/openclaw/scripts/clawra/run_performance_monitor_cron.sh"
echo ""
echo "4. 保存并退出编辑器"
echo ""
echo "5. 验证cron任务:"
echo "   crontab -l"
echo ""
echo "6. 测试性能监控脚本:"
echo "   ./run_performance_monitor_cron.sh"
echo "   # 检查日志文件:"
echo "   ls -la logs/performance_monitor/"
echo "   tail -f logs/performance_monitor/performance_*.log"
echo ""
echo "注意："
echo "- 确保脚本具有执行权限: chmod +x run_performance_monitor_cron.sh"
echo "- 首次运行建议手动测试脚本"
echo "- 性能指标将保存在 logs/metrics/ 目录"
echo "- 监控日志将保存在 logs/performance_monitor/ 目录"
echo "- 根据系统负载调整收集频率（*/5 表示每5分钟）"
echo ""

# 可选：自动添加cron任务（需要用户确认）
if [[ "$1" == "--auto-install" ]]; then
    read -p "是否自动添加性能监控cron任务？(y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "正在添加cron任务..."
        (crontab -l 2>/dev/null; echo "") | crontab -
        (crontab -l; echo "# MAREF性能监控（每5分钟）") | crontab -
        (crontab -l; echo "*/5 * * * * /Volumes/1TB-M2/openclaw/scripts/clawra/run_performance_monitor_cron.sh") | crontab -
        echo "✅ 性能监控cron任务已添加"
        echo "当前cron任务:"
        crontab -l
    else
        echo "已跳过自动安装"
    fi
fi

echo "✅ cron配置生成完成"
