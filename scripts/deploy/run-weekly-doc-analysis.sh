#!/bin/bash
# 每周文档质量分析脚本
set -e

echo "📊 运行每周文档质量分析..."
cd "$(dirname "$0")/.." || exit 1

# 确保quality目录存在
mkdir -p docs/quality

# 获取当前日期
DATE=$(date +%Y%m%d)

# 1. 生成完整质量报告
echo "📋 生成完整质量报告..."
python3 scripts/generate_document_quality_report.py --output docs/quality/weekly_quality_report_${DATE}.json

# 2. 分析可读性趋势
echo "📈 分析可读性趋势..."
python3 scripts/analyze_document_readability.py --directory docs/ --json --output docs/quality/weekly_readability_${DATE}.json 2>/dev/null || true

# 3. 检查文档完整性
echo "✅ 检查文档完整性..."
python3 scripts/check_document_completeness.py --directory docs/ --output docs/quality/weekly_completeness_${DATE}.json 2>/dev/null || true

echo "✅ 每周文档分析完成，报告已保存到 docs/quality/"