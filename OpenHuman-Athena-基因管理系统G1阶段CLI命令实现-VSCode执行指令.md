# OpenHuman-Athena-基因管理系统 G1 阶段 CLI 命令实现-VSCode 执行指令

**优先级**: S0 (最高优先级)
**执行阶段**: build
**风险等级**: low
**自动执行**: true

## 🎯 任务概述

实现基因管理系统的核心 CLI 命令，包括基因提案、审核、演进等基础功能。

## 📋 具体执行指令

### 1. 创建 CLI 脚本目录结构
```bash
# 创建 CLI 脚本目录
mkdir -p scripts/gene_mgmt
```

### 2. 创建基因提案命令
```bash
cat > scripts/gene_mgmt/propose_gene.sh << 'EOF'
#!/bin/bash
# 基因提案命令

GENE_NAME=$1
DESCRIPTION=$2

echo "🧬 创建基因提案：${GENE_NAME}"

# 创建基因提案文件
cat > EVO/proposals/${GENE_NAME}.md << 'PROPOSAL'
---
gene: ${GENE_NAME}
date: $(date +%Y-%m-%d)
status: proposed
---

## 提案描述
${DESCRIPTION}

## 假设
- 基因演进应基于历史数据
- 自动审核机制确保质量
PROPOSAL

echo "✅ 基因提案创建成功"
EOF

chmod +x scripts/gene_mgmt/propose_gene.sh
```

### 3. 创建基因审核命令
```bash
cat > scripts/gene_mgmt/review_gene.sh << 'EOF'
#!/bin/bash
# 基因审核命令

GENE_NAME=$1
APPROVAL=$2

echo "🔍 审核基因：${GENE_NAME}"

# 更新审核状态
if [ "$APPROVAL" = "approve" ]; then
    echo "✅ 基因 ${GENE_NAME} 审核通过"
elif [ "$APPROVAL" = "reject" ]; then
    echo "❌ 基因 ${GENE_NAME} 审核拒绝"
fi
EOF

chmod +x scripts/gene_mgmt/review_gene.sh
```

### 4. 创建基因演进命令
```bash
cat > scripts/gene_mgmt/evolve_gene.sh << 'EOF'
#!/bin/bash
# 基因演进命令

PARENT_GENE=$1
CHILD_GENE=$2
CHANGES=$3

echo "🔄 基因演进：${PARENT_GENE} -> ${CHILD_GENE}"

# 创建子基因
cp EVO/proposals/${PARENT_GENE}.md EVO/proposals/${CHILD_GENE}.md

echo "✅ 基因演进完成"
EOF

chmod +x scripts/gene_mgmt/evolve_gene.sh
```

### 5. 创建 CLI 命令入口
```bash
cat > scripts/gene_mgmt/README.md << 'EOF'
# 基因管理系统 CLI 命令

## 使用方法

### 基因提案
```bash
./scripts/gene_mgmt/propose_gene.sh "G1_CLI" "实现 CLI 命令系统"
```

### 基因审核
```bash
./scripts/gene_mgmt/review_gene.sh "G1_CLI" approve
```

### 基因演进
```bash
./scripts/gene_mgmt/evolve_gene.sh "G0" "G1" "添加 CLI 命令"
```
EOF
```

### 6. 验证 CLI 命令创建
```bash
# 验证脚本创建成功
ls -la scripts/gene_mgmt/

# 测试脚本可执行性
bash scripts/gene_mgmt/propose_gene.sh "TEST_GENE" "测试基因"

# 验证基因提案文件
cat EVO/proposals/TEST_GENE.md | head -10
```

## ✅ 验收标准

- [ ] CLI 脚本目录创建成功
- [ ] propose_gene.sh 脚本创建成功并可执行
- [ ] review_gene.sh 脚本创建成功并可执行
- [ ] evolve_gene.sh 脚本创建成功并可执行
- [ ] README.md 文档创建成功
- [ ] 所有脚本功能验证通过

**预计执行时间**: 20 分钟
**风险等级**: 低（脚本创建）
**依赖**: G0 阶段基础设施已完成
