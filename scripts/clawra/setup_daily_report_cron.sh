#!/bin/bash
# 设置MAREF日报生成cron任务

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== MAREF日报生成cron任务设置 ==="
echo ""

echo "# MAREF日报生成 - 每天上午9点"
echo "0 9 * * * cd /Volumes/1TB-M2/openclaw/scripts/clawra && python3 run_maref_daily_report.py --mode integration >> logs/maref_daily_report_cron.log 2>&1"
echo ""

echo "=== 安装说明 ==="
echo ""
echo "1. 查看当前cron任务:"
echo "   crontab -l"
echo ""
echo "2. 添加以上任务到crontab:"
echo "   crontab -e"
echo ""
echo "3. 将以下行复制粘贴到编辑器中，保存并退出:"
echo "   # MAREF日报生成 - 每天上午9点"
echo "   0 9 * * * cd /Volumes/1TB-M2/openclaw/scripts/clawra && python3 run_maref_daily_report.py --mode integration >> logs/maref_daily_report_cron.log 2>&1"
echo ""
echo "4. 验证cron任务:"
echo "   crontab -l"
echo ""
echo "5. 测试日报生成脚本:"
echo "   python3 run_maref_daily_report.py --mode integration --help"
echo ""
echo "注意："
echo "- 确保Python环境正确配置"
echo "- 确保logs目录存在: mkdir -p logs"
echo "- 日报将生成到默认目录: /Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/015-mailbox"
echo "- 可通过修改maref_daily_reporter.py中的get_default_output_dir()方法更改输出目录"
echo ""

# 可选：自动添加cron任务（需要用户确认）
if [[ "$1" == "--auto-install" ]]; then
    read -p "是否自动添加cron任务？(y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "正在添加cron任务..."
        # 备份当前crontab
        crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S) 2>/dev/null || true

        # 添加新的cron任务
        (crontab -l 2>/dev/null | grep -v "run_maref_daily_report.py" | grep -v "# MAREF日报生成"; echo "# MAREF日报生成 - 每天上午9点"; echo "0 9 * * * cd /Volumes/1TB-M2/openclaw/scripts/clawra && python3 run_maref_daily_report.py --mode integration >> logs/maref_daily_report_cron.log 2>&1") | crontab -

        echo "✅ cron任务已添加"
        echo "当前cron任务:"
        crontab -l | grep -A2 -B2 "MAREF"
    else
        echo "已跳过自动安装"
    fi
fi

echo "✅ cron配置生成完成"