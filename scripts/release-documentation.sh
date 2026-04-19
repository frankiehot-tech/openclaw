#!/bin/bash
# 文档发布脚本
set -e

echo "📦 准备发布文档..."

cd "$(dirname "$0")/.." || exit 1

# 1. 验证所有质量检查通过
python3 scripts/validate_document_format.py --directory docs/ --strict
python3 scripts/check_document_links.py --directory docs/

# 2. 生成发布版本报告
VERSION=$(date +%Y.%m.%d)
python3 scripts/generate_document_quality_report.py --output docs/quality/release_${VERSION}.json

# 3. 更新文档索引和元数据（如果有索引更新脚本）
if [ -f "scripts/update_document_index.py" ]; then
    python3 scripts/update_document_index.py --version ${VERSION}
fi

# 4. 创建文档快照（用于归档）
if [ -f "scripts/create_document_snapshot.py" ]; then
    python3 scripts/create_document_snapshot.py --output docs/archives/snapshot_${VERSION}.tar.gz
fi

echo "✅ 文档版本 ${VERSION} 发布就绪"