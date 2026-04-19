#!/bin/bash
# 每日文档质量检查脚本
set -e

echo "🔍 运行每日文档质量检查..."
cd "$(dirname "$0")/.." || exit 1

# 确保quality目录存在
mkdir -p docs/quality

# 获取当前日期
DATE=$(date +%Y%m%d)

# 1. 检查文档链接
echo "🔗 检查文档链接..."
python3 scripts/check_document_links.py --directory docs/ --repair --output docs/quality/daily_link_report_${DATE}.md

# 2. 检查文档格式
echo "📝 检查文档格式..."
python3 scripts/validate_document_format.py --directory docs/ --output docs/quality/daily_format_report_${DATE}.json 2>/dev/null || true

echo "✅ 每日文档检查完成，报告已保存到 docs/quality/"