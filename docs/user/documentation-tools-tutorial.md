# 文档工具使用教程

## 概述
本文档介绍OpenClaw项目中使用的文档工具链，包括质量检查、格式验证、链接修复等自动化工具的使用方法。

## 工具链概览

### 核心工具分类
| 工具类别 | 主要工具 | 用途 |
|----------|----------|------|
| **质量检查** | `check_document_links.py` | 检查文档链接有效性 |
| **格式验证** | `validate_document_format.py` | 验证Markdown格式规范 |
| **内容分析** | `check_document_completeness.py` | 分析文档内容完整性 |
| **可读性评估** | `analyze_document_readability.py` | 评估文档可读性水平 |
| **批量操作** | `batch_update_documents.py` | 批量更新文档元数据 |
| **链接修复** | `fix_internal_links.py` | 修复迁移后的内部链接 |
| **版本管理** | `document_version_manager.py` | 管理文档语义化版本 |
| **归档管理** | `archive_old_documents.py` | 归档旧文档 |

## 安装与配置

### 环境要求
```bash
# Python 3.8+
python3 --version

# 安装依赖
pip install -r docs/requirements.txt
```

### 依赖包
`docs/requirements.txt`内容：
```text
markdown==3.5.2
pyyaml==6.0.1
requests==2.31.0
beautifulsoup4==4.12.3
nltk==3.8.1
textstat==0.7.3
```

## 核心工具详解

### 1. 文档链接检查器 (`check_document_links.py`)

#### 基本用法
```bash
# 检查整个docs目录
python3 scripts/check_document_links.py --directory docs/

# 检查特定目录
python3 scripts/check_document_links.py --directory docs/user/

# 生成修复建议
python3 scripts/check_document_links.py --repair --output link_issues.md

# 详细模式
python3 scripts/check_document_links.py --verbose
```

#### 高级功能
```bash
# 只检查特定文件
python3 scripts/check_document_links.py --file docs/user/getting-started.md

# 输出JSON格式报告
python3 scripts/check_document_links.py --directory docs/ --format json

# 忽略外部链接检查
python3 scripts/check_document_links.py --skip-external
```

#### 配置选项
可以通过环境变量配置：
```bash
export DOCUMENT_LINK_CHECK_TIMEOUT=10  # 链接检查超时时间（秒）
export DOCUMENT_LINK_MAX_REDIRECTS=3   # 最大重定向次数
export DOCUMENT_LINK_USER_AGENT="OpenClaw-Doc-Check/1.0"  # User-Agent
```

### 2. 文档格式验证器 (`validate_document_format.py`)

#### 基本用法
```bash
# 验证单个文件
python3 scripts/validate_document_format.py --file docs/user/user-guide.md

# 验证整个目录
python3 scripts/validate_document_format.py --directory docs/architecture/

# 自动修复格式问题
python3 scripts/validate_document_format.py --file <文件> --fix

# 严格模式（任何错误都导致失败）
python3 scripts/validate_document_format.py --strict
```

#### 验证规则
格式验证器检查以下内容：
1. **标题层级**: 确保从h1开始，层级连续
2. **列表格式**: 有序列表和无序列表格式正确
3. **代码块**: 代码块语法正确
4. **表格**: 表格格式规范
5. **链接格式**: 链接语法正确
6. **图片引用**: 图片链接格式正确
7. **元数据**: 文档末尾包含必要元数据

#### 配置文件
创建`.document_format_rules.yaml`自定义规则：
```yaml
rules:
  require_metadata: true
  metadata_fields:
    - last_updated
    - version
    - maintainer
  max_title_level: 4
  require_image_alt: true
  code_block_languages:
    - python
    - bash
    - yaml
    - json
```

### 3. 文档完整性分析器 (`check_document_completeness.py`)

#### 基本用法
```bash
# 分析单个文档
python3 scripts/check_document_completeness.py --file docs/architecture/system-design.md

# 分析目录中文档
python3 scripts/check_document_completeness.py --directory docs/technical/

# 生成详细报告
python3 scripts/check_document_completeness.py --file <文件> --report
```

#### 检查维度
1. **结构完整性**: 必需章节是否存在
2. **内容覆盖率**: 主题是否全面覆盖
3. **示例充分性**: 代码示例和配置示例是否足够
4. **引用完整性**: 相关文档是否都有引用
5. **更新及时性**: 文档最后更新时间是否合理

#### 完整性评分
工具会生成0-100分的完整性评分：
- 90+分: 优秀
- 70-89分: 良好
- 50-69分: 需要改进
- <50分: 不完整

### 4. 文档可读性分析器 (`analyze_document_readability.py`)

#### 基本用法
```bash
# 分析可读性
python3 scripts/analyze_document_readability.py --file docs/user/getting-started.md

# 批量分析
python3 scripts/analyze_document_readability.py --directory docs/user/

# 输出改进建议
python3 scripts/analyze_document_readability.py --file <文件> --suggestions
```

#### 评估指标
1. **Flesch Reading Ease**: 易读性分数（越高越易读）
2. **Flesch-Kincaid Grade Level**: 美国年级水平
3. **Gunning Fog Index**: 雾化指数
4. **SMOG Index**: 简单测量戈贝尔指数
5. **Coleman-Liau Index**: 科尔曼-廖指数
6. **Automated Readability Index**: 自动可读性指数

#### 目标标准
- **技术文档**: Flesch Reading Ease 50-70，Grade Level 8-12
- **用户指南**: Flesch Reading Ease 70-80，Grade Level 6-8
- **API文档**: Flesch Reading Ease 40-60，Grade Level 10-14

### 5. 批量文档更新器 (`batch_update_documents.py`)

#### 基本用法
```bash
# 更新所有文档元数据
python3 scripts/batch_update_documents.py --pattern "*.md" --update-metadata

# 更新特定目录
python3 scripts/batch_update_documents.py --directory docs/audit/2026-04/ --update-last-modified

# 重命名文件（下划线转短横线）
python3 scripts/batch_update_documents.py --rename-underscore-to-hyphen

# 更新文档标题
python3 scripts/batch_update_documents.py --update-titles --title-template "{filename} - OpenClaw文档"
```

#### 批量操作类型
1. **元数据更新**: 更新最后修改日期、版本号等
2. **格式标准化**: 统一代码块格式、表格格式等
3. **链接修复**: 批量修复相对路径链接
4. **重命名操作**: 统一文件名格式
5. **内容替换**: 批量替换术语或短语

#### 安全模式
```bash
# 先预览更改
python3 scripts/batch_update_documents.py --dry-run --verbose

# 确认后执行
python3 scripts/batch_update_documents.py --execute --backup
```

### 6. 内部链接修复器 (`fix_internal_links.py`)

#### 基本用法
```bash
# 修复迁移后的文档链接
python3 scripts/fix_internal_links.py --source . --target docs/

# 只修复特定文件
python3 scripts/fix_internal_links.py --files docs/user/contributing.md docs/user/getting-started.md

# 生成修复报告
python3 scripts/fix_internal_links.py --report --output link_fix_report.md
```

#### 修复策略
1. **路径映射**: 基于迁移前后的路径映射表
2. **智能猜测**: 基于文件名相似性猜测正确路径
3. **用户确认**: 交互式确认不确定的修复

#### 映射配置文件
创建`.link_mapping.yaml`自定义映射：
```yaml
mappings:
  "old/path/file.md": "new/path/file.md"
  "architecture/system_architecture.md": "architecture/system-design.md"
  "audit/deep_audit_report_20260419.md": "audit/2026-04/deep-audit-report-2026-04.md"
```

### 7. 文档版本管理器 (`document_version_manager.py`)

#### 基本用法
```bash
# 初始化版本管理
python3 scripts/document_version_manager.py --init --directory docs/architecture/

# 创建新版本
python3 scripts/document_version_manager.py --bump minor --file docs/user/user-guide.md

# 查看版本历史
python3 scripts/document_version_manager.py --history --file docs/architecture/system-design.md

# 比较版本差异
python3 scripts/document_version_manager.py --diff v1.0 v1.1 --file <文件>
```

#### 版本控制策略
- **MAJOR版本**: 架构重大变更或内容重构
- **MINOR版本**: 添加新功能或重要内容扩展
- **PATCH版本**: 错误修复或小范围更新

#### 版本元数据
```yaml
---
version: 1.2.1
changelog:
  - version: 1.2.1
    date: 2026-04-19
    changes:
      - 修复了链接错误
      - 更新了配置示例
  - version: 1.2.0
    date: 2026-04-18
    changes:
      - 添加了新功能说明
      - 扩展了API文档
---
```

## 集成工作流

### 预提交检查
在`.git/hooks/pre-commit`中添加：
```bash
#!/bin/bash
echo "🔍 运行文档质量检查..."

# 格式检查
python3 scripts/validate_document_format.py --strict --directory docs/
if [ $? -ne 0 ]; then
    echo "❌ 文档格式检查失败"
    exit 1
fi

# 链接检查（仅警告）
python3 scripts/check_document_links.py --directory docs/
if [ $? -ne 0 ]; then
    echo "⚠️  发现链接问题，请检查"
fi

echo "✅ 文档检查通过"
```

### CI/CD集成
GitHub Actions配置示例：
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
      - name: Check document completeness
        run: python3 scripts/check_document_completeness.py --directory docs/ --min-score 70
      - name: Generate documentation report
        run: python3 scripts/generate_documentation_report.py --output document_report.html
```

### 定期维护任务
cron配置示例：
```bash
# 每日检查文档链接
0 2 * * * cd /path/to/openclaw && python3 scripts/check_document_links.py --directory docs/ --report

# 每周生成文档统计
0 3 * * 1 cd /path/to/openclaw && python3 scripts/generate_document_stats.py --output weekly_stats.json

# 每月归档旧文档
0 4 1 * * cd /path/to/openclaw && python3 scripts/archive_old_documents.py --days 30
```

## 故障排除

### 常见问题

#### Q1: 链接检查器报告大量误报
**原因**: 代码片段被误识别为Markdown链接
**解决方案**: 
1. 更新正则表达式模式
2. 添加代码片段过滤逻辑
3. 使用`--strict`模式减少误报

#### Q2: 格式验证器失败但文档看起来正常
**原因**: 验证规则过于严格
**解决方案**:
1. 检查`.document_format_rules.yaml`配置
2. 使用`--fix`参数自动修复
3. 调整规则配置

#### Q3: 批量更新器修改了不应更改的内容
**原因**: 模式匹配过于宽泛
**解决方案**:
1. 先使用`--dry-run`预览更改
2. 使用更具体的文件模式
3. 使用`--exclude`参数排除特定文件

#### Q4: 版本管理器无法识别版本号
**原因**: 版本号格式不符合语义化版本规范
**解决方案**:
1. 确保版本号格式为`MAJOR.MINOR.PATCH`
2. 使用`--init`参数初始化版本管理
3. 手动添加版本元数据

### 调试技巧
```bash
# 启用调试模式
export DOCUMENT_TOOLS_DEBUG=1
python3 scripts/check_document_links.py --verbose

# 查看详细日志
tail -f document_tools.log

# 分析工具性能
python3 -m cProfile -s cumtime scripts/check_document_links.py --directory docs/
```

## 最佳实践

### 1. 渐进式采用
- 从核心工具开始（链接检查、格式验证）
- 逐步集成更多工具
- 根据团队需求定制工具链

### 2. 自动化优先
- 将工具集成到开发工作流
- 使用CI/CD自动执行检查
- 设置定期维护任务

### 3. 反馈循环
- 收集工具使用反馈
- 根据实际问题调整工具
- 定期评估工具效果

### 4. 文档化配置
- 记录所有工具配置
- 维护使用示例和常见问题
- 分享最佳实践和经验教训

## 扩展与定制

### 添加新工具
1. 在`scripts/`目录创建新工具
2. 遵循现有工具的模式和接口
3. 更新`docs/requirements.txt`依赖
4. 在本文档中添加说明

### 自定义检查规则
1. 创建自定义配置文件
2. 扩展现有工具的功能
3. 开发领域特定检查器

### 集成外部工具
```bash
# 集成markdownlint
npm install -g markdownlint-cli
markdownlint docs/**/*.md

# 集成vale（文档风格检查）
vale --config=.vale.ini docs/**/*.md
```

---

**最后更新**: 2026-04-19  
**版本**: 1.0  
**维护者**: OpenClaw文档团队  
**文档状态**: 活跃维护中  

> **提示**: 工具链持续演进中，欢迎提交改进建议和bug报告。