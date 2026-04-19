# OpenClaw 文档贡献指南

## 📖 概述

欢迎为OpenClaw项目贡献文档！本指南详细说明如何参与文档创建、更新和维护。OpenClaw采用MAREF三才六层模型组织文档体系，确保知识管理的系统性和一致性。

### 文档体系概览
OpenClaw文档按三才六层模型组织：

| 层级 | 目录 | 文档类型 | 贡献重点 |
|------|------|----------|----------|
| **战略层** | `docs/architecture/` | 架构设计、智能体定义、核心框架 | 系统设计文档、架构演进提案 |
| **管理层** | `docs/technical/specifications/` | 技术规范、接口定义、协议说明 | API文档、接口规范、技术标准 |
| **流程层** | `docs/technical/operations/` | 运维指南、操作手册、故障处理 | 运维文档、操作流程、故障排除 |
| **应用层** | `docs/technical/deployment/` | 部署指南、配置说明、环境设置 | 部署文档、配置模板、环境说明 |
| **平台层** | `docs/audit/YYYY-MM/` | 审计报告、性能分析、问题跟踪 | 审计记录、性能分析、问题总结 |
| **环境层** | `docs/user/` | 用户指南、快速开始、工具参考 | 用户文档、入门指南、工具说明 |

## 🚀 快速开始贡献

### 1. 环境准备
```bash
# 克隆项目
git clone <repository-url>
cd openclaw

# 设置环境变量
export OPENCLAW_ROOT="$(pwd)"
export ATHENA_RUNTIME_ROOT="$(pwd)"

# 验证环境
python3 validate_path_config.py
```

### 2. 文档工具安装
```bash
# 安装文档工具依赖
pip install -r docs/requirements.txt

# 验证文档工具
python3 scripts/check_document_links.py --test
```

### 3. 创建贡献分支
```bash
# 基于main创建贡献分支
git checkout main
git pull origin main
git checkout -b docs/feature-name
```

## 📝 文档创建流程

### 步骤1：确定文档类型和位置

根据文档内容选择正确的分类目录：

```bash
# 架构设计文档 → docs/architecture/
echo "# 新架构设计" > docs/architecture/new-architecture-design.md

# 技术规范文档 → docs/technical/specifications/
echo "# 新接口规范" > docs/technical/specifications/new-api-specification.md

# 运维指南 → docs/technical/operations/
echo "# 新运维流程" > docs/technical/operations/new-operation-guide.md

# 审计报告 → docs/audit/YYYY-MM/ (按年月组织)
YEAR_MONTH=$(date +%Y-%m)
mkdir -p docs/audit/$YEAR_MONTH
echo "# 审计报告" > docs/audit/$YEAR_MONTH/new-audit-report.md

# 用户文档 → docs/user/
echo "# 新用户指南" > docs/user/new-user-guide.md
```

### 步骤2：使用文档模板

OpenClaw提供标准化文档模板：

```bash
# 复制模板
cp docs/templates/architecture-template.md docs/architecture/new-design.md
cp docs/templates/operations-template.md docs/technical/operations/new-guide.md
cp docs/templates/audit-template.md docs/audit/$(date +%Y-%m)/new-report.md
```

### 步骤3：遵循命名规范

| 规则 | 正确示例 | 错误示例 |
|------|----------|----------|
| **英文优先** | `system-architecture.md` | `系统架构.md` |
| **短横线分隔** | `user-guide.md` | `user_guide.md` 或 `userGuide.md` |
| **日期格式** | `2026-04-19-audit-report.md` | `04-19-2026-audit.md` |
| **描述性名称** | `queue-monitoring-setup.md` | `monitoring.md` |

### 步骤4：编写文档内容

#### 文档结构要求
所有文档应包含：
1. **标题** (# 一级标题)
2. **元数据** (最后更新日期、版本、维护者)
3. **目录** (可选，长文档建议添加)
4. **正文内容** (按逻辑组织)
5. **相关链接** (指向其他文档)

#### 内容质量要求
- **准确性**: 确保技术内容准确无误
- **完整性**: 覆盖主题所有重要方面
- **一致性**: 术语和格式与现有文档一致
- **实用性**: 提供实际可操作的指导
- **可读性**: 语言清晰，结构合理

### 步骤5：添加文档链接

在相关文档中添加交叉引用：

```markdown
## 相关文档
- [系统架构](../architecture/system-design.md)
- [用户指南](user/user-guide.md)
- [快速开始](user/getting-started.md)
```

## 🔍 文档质量检查

### 自动检查工具

#### 1. 链接有效性检查
```bash
# 检查所有文档链接
python3 scripts/check_document_links.py --directory docs/

# 检查特定目录
python3 scripts/check_document_links.py --directory docs/user/

# 生成修复建议
python3 scripts/check_document_links.py --repair --output link_issues.md
```

#### 2. 格式规范检查
```bash
# 验证文档格式
python3 scripts/validate_document_format.py --file docs/user/user-guide.md

# 批量检查
python3 scripts/validate_document_format.py --directory docs/architecture/

# 自动修复格式问题
python3 scripts/validate_document_format.py --file <文件> --fix
```

#### 3. 内容质量检查
```bash
# 检查文档完整性
python3 scripts/check_document_completeness.py --file <文档>

# 分析文档可读性
python3 scripts/analyze_document_readability.py --file <文档>

# 生成质量报告
python3 scripts/generate_document_quality_report.py --output quality_report.json
```

### 手动检查清单

提交前请确认：
- [ ] 文档位于正确的分类目录
- [ ] 遵循命名规范
- [ ] 包含必要的元数据
- [ ] 技术内容准确无误
- [ ] 链接指向正确的目标
- [ ] 无拼写或语法错误
- [ ] 图片和代码示例正确显示
- [ ] 文档通过自动检查工具

## 🔄 文档更新流程

### 小规模更新（单文件）
```bash
# 1. 直接编辑文档
vim docs/user/user-guide.md

# 2. 运行质量检查
python3 scripts/validate_document_format.py --file docs/user/user-guide.md

# 3. 更新元数据（最后更新日期）
# 手动更新文档末尾的"最后更新"日期
```

### 大规模更新（多文件）
```bash
# 1. 使用批量更新工具
python3 scripts/batch_update_documents.py --pattern "*.md" --update-metadata

# 2. 重新生成文档索引
python3 scripts/update_document_index.py

# 3. 验证更新结果
python3 scripts/validate_document_format.py --directory docs/
```

### 文档重构（结构调整）
```bash
# 1. 使用文档迁移工具
python3 scripts/automate_document_migration.py --source . --target docs/ --dry-run

# 2. 执行迁移
python3 scripts/automate_document_migration.py --execute --report migration_report.md

# 3. 清理原始文件（使用回收站）
python3 scripts/cleanup_migrated_files.py --execute
```

## 📚 版本管理策略

### 文档版本控制

#### 1. 版本号规范
使用语义化版本控制：
- **主版本 (MAJOR)**: 架构重大变更 (1.0 → 2.0)
- **次版本 (MINOR)**: 功能添加或内容扩展 (1.0 → 1.1)
- **修订版本 (PATCH)**: 错误修复或小更新 (1.0.0 → 1.0.1)

#### 2. 版本记录
在文档末尾添加版本历史：

```markdown
## 版本历史

| 版本 | 日期 | 更改说明 | 贡献者 |
|------|------|----------|--------|
| 1.0 | 2026-04-19 | 初始版本 | 文档团队 |
| 1.1 | 2026-04-20 | 添加新功能说明 | 用户名 |
| 1.1.1 | 2026-04-21 | 修复链接错误 | 用户名 |
```

#### 3. 版本兼容性
- **向前兼容**: 新版本不应破坏现有链接和引用
- **向后兼容**: 旧版本文档应保留归档副本
- **迁移指南**: 重大变更时提供迁移说明

### 归档策略

#### 1. 按时间归档
```bash
# 将旧文档移动到归档目录
mkdir -p docs/archive/2026-Q1/
mv docs/technical/specifications/old-spec.md docs/archive/2026-Q1/

# 更新索引文件
python3 scripts/update_archive_index.py
```

#### 2. 版本归档
```bash
# 创建文档版本快照
python3 scripts/create_document_snapshot.py --version 1.0 --output docs/archive/v1.0/
```

## 🔧 自动化工作流集成

### 预提交检查
在`.git/hooks/pre-commit`中添加：

```bash
#!/bin/bash
# 文档质量预检查
echo "🔍 运行文档质量检查..."
python3 scripts/validate_document_format.py --directory docs/ --strict
if [ $? -ne 0 ]; then
    echo "❌ 文档格式检查失败，请修复后再提交"
    exit 1
fi

echo "🔗 检查文档链接..."
python3 scripts/check_document_links.py --directory docs/
if [ $? -ne 0 ]; then
    echo "⚠️  发现链接问题，请检查"
    # 不阻止提交，仅警告
fi

echo "✅ 文档检查通过"
```

### CI/CD集成
在GitHub Actions工作流中添加文档检查：

```yaml
name: Document Quality Check
on: [push, pull_request]
jobs:
  document-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install -r docs/requirements.txt
      - name: Check document format
        run: python3 scripts/validate_document_format.py --directory docs/ --strict
      - name: Check document links
        run: python3 scripts/check_document_links.py --directory docs/
      - name: Generate documentation report
        run: python3 scripts/generate_documentation_report.py --output document_report.html
```

### 定期维护任务
使用cron定期执行文档维护：

```bash
# 每日检查文档链接
0 2 * * * cd /Volumes/1TB-M2/openclaw && python3 scripts/check_document_links.py --directory docs/ --report

# 每周生成文档统计
0 3 * * 1 cd /Volumes/1TB-M2/openclaw && python3 scripts/generate_document_stats.py --output weekly_stats.json

# 每月归档旧文档
0 4 1 * * cd /Volumes/1TB-M2/openclaw && python3 scripts/archive_old_documents.py --days 30
```

## 🎯 贡献者分级

### 初级贡献者
**适合**: 文档校对、小规模更新、链接修复
**任务示例**:
- 修复拼写和语法错误
- 更新过时的信息
- 修复破损链接
- 添加示例代码

### 中级贡献者  
**适合**: 创建新文档、翻译、内容重组
**任务示例**:
- 基于模板创建新文档
- 翻译文档到其他语言
- 重组文档结构提高可读性
- 添加图表和示意图

### 高级贡献者
**适合**: 架构设计、规范制定、工具开发
**任务示例**:
- 设计新的文档分类体系
- 制定文档标准和规范
- 开发文档工具和脚本
- 管理文档版本和发布

## 📊 贡献度评估

### 评估指标
1. **文档数量**: 创建/更新的文档数量
2. **文档质量**: 通过自动化检查的比例
3. **影响范围**: 文档被引用的次数
4. **用户反馈**: 文档评分和用户评价
5. **维护贡献**: 长期维护的文档数量

### 贡献者认可
- **文档之星**: 每月选出贡献最突出的贡献者
- **质量奖**: 文档质量评分最高的贡献者
- **维护奖**: 长期维护重要文档的贡献者
- **创新奖**: 提出创新文档工具或方法的贡献者

## 🚨 常见问题

### Q1: 文档应该放在哪里？
**A**: 根据MAREF三才六层模型选择对应目录。不确定时，放在`docs/user/`目录，维护者会协助分类。

### Q2: 如何添加图片或图表？
**A**: 将图片放在`docs/assets/images/`目录，使用相对路径引用：
```markdown
![架构图](../assets/images/architecture-diagram.png)
```

### Q3: 文档需要审核吗？
**A**: 是的，所有文档变更需要通过PR审核流程。主要审核内容准确性、格式规范性和分类正确性。

### Q4: 如何报告文档问题？
**A**: 在GitHub Issues中使用`documentation`标签，或直接创建PR修复问题。

### Q5: 可以翻译文档吗？
**A**: 可以，将翻译文档放在对应语言目录，如`docs/zh-cn/user/`。请确保翻译准确并保持原意。

## 🤝 社区支持

### 文档讨论区
- **GitHub Discussions**: 文档相关讨论
- **Slack频道**: `#documentation` 频道
- **定期会议**: 每月文档工作组会议

### 导师计划
新贡献者可申请导师指导：
1. 在GitHub Issue中申请导师
2. 分配经验丰富的文档维护者作为导师
3. 获得一对一的指导和支持

### 学习资源
- [文档写作指南](docs/user/documentation-writing-guide.md)
- [Markdown高级技巧](docs/user/markdown-advanced.md)
- [文档工具使用教程](docs/user/documentation-tools-tutorial.md)

---

**最后更新**: 2026-04-19  
**版本**: 1.0  
**维护者**: OpenClaw文档团队  
**文档状态**: 活跃维护中  

> **提示**: 本贡献指南将持续更新。如有建议或发现问题，请在GitHub Issues中反馈。