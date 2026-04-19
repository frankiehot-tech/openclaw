#!/bin/bash
GENE_NAME=$1
DESCRIPTION=$2
echo "创建基因提案：${GENE_NAME}"
cat > EVO/proposals/${GENE_NAME}.md << PROPOSAL
---
gene: ${GENE_NAME}
date: $(date +%Y-%m-%d)
status: proposed
---
## 提案描述
${DESCRIPTION}
PROPOSAL
echo "基因提案创建成功"