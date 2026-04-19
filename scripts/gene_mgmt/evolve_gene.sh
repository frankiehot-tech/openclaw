#!/bin/bash
PARENT_GENE=$1
CHILD_GENE=$2
echo "基因演进：${PARENT_GENE} -> ${CHILD_GENE}"
cp EVO/proposals/${PARENT_GENE}.md EVO/proposals/${CHILD_GENE}.md
echo "基因演进完成"