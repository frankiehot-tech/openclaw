#!/bin/bash
GENE_NAME=$1
APPROVAL=$2
echo "审核基因：${GENE_NAME}"
if [ "$APPROVAL" = "approve" ]; then
    echo "基因 ${GENE_NAME} 审核通过"
else
    echo "基因 ${GENE_NAME} 审核拒绝"
fi