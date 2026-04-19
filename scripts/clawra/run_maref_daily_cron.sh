#!/bin/bash
# MAREF日报生成cron包装脚本
# 设置正确的环境变量供cron使用

set -e

# 设置环境变量
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export PYTHONPATH="/Volumes/1TB-M2/openclaw/scripts/clawra:/Volumes/1TB-M2/openclaw/scripts/clawra/external/ROMA:$PYTHONPATH"

# 切换到脚本目录
cd "/Volumes/1TB-M2/openclaw/scripts/clawra"

# 记录开始时间
echo "=== MAREF日报生成开始 $(date) ===" >> logs/maref_daily_report_cron.log

# 运行日报生成
python3 run_maref_daily_report.py --mode integration >> logs/maref_daily_report_cron.log 2>&1

# 记录结束状态
EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ MAREF日报生成成功 $(date)" >> logs/maref_daily_report_cron.log
else
    echo "❌ MAREF日报生成失败，退出码: $EXIT_CODE $(date)" >> logs/maref_daily_report_cron.log
fi

exit $EXIT_CODE