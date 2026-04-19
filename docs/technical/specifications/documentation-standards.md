# OpenClaw项目文档分类标准

## 概述

本文档定义了OpenClaw项目的文档分类、组织结构和生命周期管理标准。遵循此标准可确保文档的可查找性、一致性和可维护性。

## 文档分类体系

### 1. 按文档类型分类

| 类别 | 描述 | 目录位置 | 示例 |
|------|------|----------|------|
| **架构文档** | 系统架构、设计决策、技术规范 | `/docs/architecture/` | 系统架构图、组件设计、API规范 |
| **用户指南** | 用户操作手册、使用教程、快速入门 | `/docs/guides/` | 安装指南、配置教程、用户手册 |
| **开发文档** | 开发者指南、API文档、代码规范 | `/docs/development/` | 开发环境搭建、代码贡献指南、API参考 |
| **运维文档** | 部署、监控、故障排除、性能优化 | `/docs/operations/` | 部署指南、监控配置、故障排除手册 |
| **项目文档** | 项目规划、进度报告、会议记录 | `/docs/project/` | 项目计划、会议纪要、进度报告 |
| **参考文档** | 配置参考、命令参考、术语表 | `/docs/reference/` | 配置参数说明、命令行参考、术语词典 |
| **设计文档** | UI/UX设计、交互设计、视觉规范 | `/docs/design/` | 界面设计稿、交互流程图、视觉规范 |
| **策略文档** | 业务策略、安全策略、合规要求 | `/docs/policies/` | 安全策略、合规要求、业务规则 |

### 2. 按文档状态分类

| 状态 | 描述 | 存储位置 | 管理规则 |
|------|------|----------|----------|
| **活跃文档** | 当前有效、正在使用的文档 | 对应类型目录 | 定期更新，版本控制 |
| **草案文档** | 正在编写、未批准的文档 | `/docs/drafts/` | 前缀标注`[DRAFT]`，不用于生产 |
| **归档文档** | 历史版本、已废弃的文档 | `/docs/archive/` | 按日期组织，保留历史记录 |
| **临时文档** | 临时性、过渡性文档 | `/docs/temp/` | 定期清理（30天保留期） |

### 3. 按重要性分类

| 等级 | 描述 | 标识 | 更新频率 |
|------|------|------|----------|
| **核心文档** | 系统运行必需的关键文档 | `[CORE]`前缀 | 实时更新 |
| **重要文档** | 重要但不是必需的文档 | `[IMPORTANT]`前缀 | 每周更新 |
| **参考文档** | 辅助性、参考性文档 | 无特殊标识 | 每月更新 |
| **临时文档** | 临时性、一次性文档 | `[TEMP]`前缀 | 用后即删 |

## 目录结构规范

```
docs/
├── architecture/          # 架构文档
│   ├── system-architecture.md
│   ├── component-design/
│   └── api-specifications/
├── guides/               # 用户指南
│   ├── getting-started/
│   ├── user-manual/
│   └── tutorials/
├── development/          # 开发文档
│   ├── setup-guide/
│   ├── coding-standards/
│   └── api-reference/
├── operations/           # 运维文档
│   ├── deployment/
│   ├── monitoring/
│   └── troubleshooting/
├── project/              # 项目文档
│   ├── planning/
│   ├── meetings/
│   └── reports/
├── reference/            # 参考文档
│   ├── configuration/
│   ├── commands/
│   └── glossary/
├── design/               # 设计文档
│   ├── ui-ux/
│   ├── interaction/
│   └── visual/
├── policies/             # 策略文档
│   ├── security/
│   ├── compliance/
│   └── business/
├── drafts/               # 草案文档
│   └── [按日期组织]/
├── archive/              # 归档文档
│   └── [按年份-月份组织]/
├── temp/                 # 临时文档
│   └── [自动清理]
├── templates/            # 文档模板
│   ├── architecture-template.md
│   ├── guide-template.md
│   └── report-template.md
└── DOCUMENTATION_STANDARDS.md  # 本文档
```

## 文件命名规范

### 命名规则
1. **小写字母+连字符**: 使用小写字母和连字符，避免空格和下划线
   - ✅ `system-architecture.md`
   - ❌ `System_Architecture.md`

2. **描述性名称**: 名称应清晰描述文档内容
   - ✅ `queue-monitoring-guide.md`
   - ❌ `monitoring.md`

3. **版本标识**: 重要文档可包含版本号
   - ✅ `api-specification-v2.1.md`
   - ❌ `api-specification-new.md`

4. **日期标识**: 临时或时间敏感文档包含日期
   - ✅ `meeting-notes-2026-04-19.md`
   - ❌ `meeting-notes.md`

### 前缀约定
| 前缀 | 含义 | 示例 |
|------|------|------|
| `[DRAFT]` | 草案文档 | `[DRAFT]system-redesign.md` |
| `[REVIEW]` | 待审文档 | `[REVIEW]new-feature-spec.md` |
| `[CORE]` | 核心文档 | `[CORE]security-policy.md` |
| `[IMPORTANT]` | 重要文档 | `[IMPORTANT]deployment-guide.md` |
| `[TEMP]` | 临时文档 | `[TEMP]debug-notes.md` |

## 文档生命周期管理

### 1. 创建阶段
- 确定文档类型和分类
- 使用对应模板创建
- 存放在正确目录
- 添加适当的元数据

### 2. 维护阶段
- 定期审查和更新
- 跟踪版本变化
- 确保与其他文档的一致性
- 响应问题反馈

### 3. 归档阶段
- 文档不再活跃时移至`archive/`
- 按年份和月份组织归档
- 保留历史版本供参考
- 更新相关文档的引用

### 4. 清理阶段
- 临时文档30天后自动清理
- 定期审查归档文档，移除无用文档
- 确保存储空间优化

## 元数据规范

### 文档头部元数据 (YAML Frontmatter)
每个文档应在开头包含以下元数据：

```yaml
---
title: "文档标题"
description: "文档简短描述"
author: "作者姓名"
created: "2026-04-19"
updated: "2026-04-19"
version: "1.0"
status: "active"  # active, draft, archived, deprecated
category: "architecture"  # 文档类别
tags: ["系统架构", "设计", "API"]
importance: "core"  # core, important, reference, temp
---
```

### 版本控制
重要文档应包含版本历史部分：

```markdown
## 版本历史
| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|----------|
| 1.0 | 2026-04-19 | 张三 | 初始版本 |
| 1.1 | 2026-04-20 | 李四 | 添加API示例 |
```

## 现有文档迁移计划

### 迁移步骤
1. **目录创建**: 按照上述结构创建所有子目录
2. **文档分类**: 评估现有文档，确定分类
3. **文件迁移**: 将文档移动到对应目录
4. **元数据添加**: 为每个文档添加标准元数据
5. **链接修复**: 修复内部链接和引用
6. **清理冗余**: 移除重复和过时文档

### 迁移优先级
1. **P0 (立即)**: 核心架构和用户指南文档
2. **P1 (本周)**: 开发文档和运维文档
3. **P2 (本月)**: 项目文档和参考文档
4. **P3 (后续)**: 设计文档和策略文档

## 维护责任

### 文档维护者
| 文档类别 | 负责人 | 更新频率 | 审查周期 |
|----------|--------|----------|----------|
| 架构文档 | 架构团队 | 每月 | 每季度 |
| 用户指南 | 产品团队 | 每版本发布 | 每次发布 |
| 开发文档 | 开发团队 | 每周 | 每月 |
| 运维文档 | 运维团队 | 每月 | 每季度 |
| 项目文档 | 项目经理 | 每周 | 每月 |

### 审查流程
1. **创建/更新**: 作者创建或更新文档
2. **同行评审**: 至少1名同行评审
3. **技术评审**: 技术负责人批准
4. **发布**: 移动到正式目录
5. **定期审查**: 按计划定期审查

## 工具和自动化

### 推荐工具
1. **文档生成**: Docusaurus, MkDocs, Sphinx
2. **版本控制**: Git + GitHub/GitLab
3. **协作平台**: Confluence, Notion (仅限草案)
4. **自动化检查**: 脚本验证目录结构、元数据完整性

### 自动化脚本
项目提供以下维护脚本：
- `scripts/validate-docs-structure.py`: 验证文档结构
- `scripts/generate-docs-index.py`: 生成文档索引
- `scripts/cleanup-temp-docs.py`: 清理临时文档
- `scripts/migrate-legacy-docs.py`: 迁移旧文档

## 附则

### 生效日期
本规范自 **2026年4月19日** 起生效。

### 修订记录
对本规范的任何修订应记录在此部分。

### 例外处理
特殊情况下需偏离本规范的，应获得技术负责人批准并记录原因。

---
**文档状态**: active  
**最后更新**: 2026-04-19  
**维护团队**: Athena工程团队  
**适用范围**: OpenClaw所有项目文档