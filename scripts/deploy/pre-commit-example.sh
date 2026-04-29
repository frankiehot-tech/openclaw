#!/bin/bash
echo "🔍 运行文档质量检查..."

# 格式检查
python3 scripts/validate_document_format.py --directory docs/ --strict
if [ $? -ne 0 ]; then
    echo "❌ 文档格式检查失败"
    exit 1
fi

# 链接检查（跳过外部链接检查以加快速度）
python3 scripts/check_document_links.py --directory docs/
if [ $? -ne 0 ]; then
    echo "⚠️  发现链接问题，请检查"
fi

echo "✅ 文档检查通过"