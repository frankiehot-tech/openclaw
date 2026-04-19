# OpenClaw项目文档

## 文档结构

本项目使用标准化的文档管理体系，基于MAREF三才六层模型组织：

### 架构文档 (`architecture/`)
战略层和管理层文档，描述系统整体架构和设计原则。

- [认知DNA](architecture/cognitive-dna.md) - 项目核心认知框架
- [智能体架构](architecture/agents-overview.md) - 智能体系统和角色定义
- [系统设计](architecture/system-design.md) - 系统整体设计文档
- [MAREF框架应用指南](architecture/marer-framework.md) - MAREF框架实施指南

### 技术文档 (`technical/`)
平台层和应用层文档，包含技术规范和实现细节。

#### 技术规范 (`technical/specifications/`)
- 系统规范、API文档、接口定义

#### 部署指南 (`technical/deployment/`)
- 部署计划、生产环境配置、回滚指南

#### 运维文档 (`technical/operations/`)
- 监控指南、故障排除、备份恢复

### 审计文档 (`audit/`)
流程层文档，按年月组织的审计报告和分析。

- [2026年4月审计报告](audit/2026-04/) - 当月审计文档
- [审计汇总索引](audit/summary-index.md) - 所有审计报告索引

### 用户文档 (`user/`)
环境层文档，用户指南和配置说明。

- [快速开始](user/getting-started.md) - 新用户入门指南
- [用户指南](user/user-guide.md) - 详细功能说明
- [Claude Code配置](user/claude-code-config.md) - Claude Code集成配置
- [工具参考](user/tools-reference.md) - 工具使用说明

### 技能文档 (`skills/`)
智能体技能定义和说明文档。

- 保持原有skills目录结构
- 每个技能子目录包含SKILL.md文件

### 第三方文档 (`vendor/`)
第三方库和框架文档。

- 保持原有vendor目录结构

## 文档维护

### 新增文档
1. 根据文档类型选择对应目录
2. 遵循命名规范：`{domain}-{topic}-{date}.md`
3. 更新相关索引文件

### 更新文档
1. 保持文档内容最新
2. 更新最后修改日期
3. 如有重大变更，创建新版本文档

### 查找文档
- 使用文档索引查找所需文档
- 按年月查找审计报告
- 使用项目根目录README.md作为入口

## 相关链接

- [项目主README](../README.md) - 项目整体介绍
- [CLAUDE.md](../CLAUDE.md) - Claude Code项目配置
- [文档迁移计划](../document_migration_plan.md) - 文档迁移实施计划

---
**最后更新**: 2026-04-19  
**维护者**: 文档架构团队