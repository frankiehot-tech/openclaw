# OpenClaw项目

> **多智能体协作的工程化AI开发平台**

## 概述

OpenClaw是一个基于MAREF（多智能体递归进化框架）构建的工程化AI开发平台，专注于Athena队列系统和智能工作流管理。项目采用三才六层架构模型，实现超稳定系统设计和契约驱动开发。

## 核心功能

### 🧠 智能工作流管理
- **Athena队列系统**: 基于契约框架的任务编排和智能路由
- **智能工作流引擎**: SmartOrchestrator实现执行器智能决策
- **状态同步机制**: 原子状态更新确保系统一致性

### 📚 文档驱动开发
- **三才六层文档架构**: 战略层→环境层的完整文档体系
- **知识蒸馏管道**: 自动提取和沉淀项目知识
- **认知DNA维护**: 保持项目核心认知框架

### 🚀 工程化部署
- **阶段性部署计划**: 分阶段、批次的工程化部署流程
- **质量门禁检查**: 每个部署阶段前的严格质量检查
- **回滚能力**: 快速回滚到稳定状态的能力

## 快速开始

### 环境配置
```bash
# 设置环境变量
export OPENCLAW_ROOT="/Volumes/1TB-M2/openclaw"
export ATHENA_RUNTIME_ROOT="/Volumes/1TB-M2/openclaw"

# 添加到PATH（可选）
export PATH="$OPENCLAW_ROOT/scripts:$PATH"

# 验证配置
python3 setup_environment.py
```

### 路径配置验证
```bash
# 验证路径配置完整性
python3 validate_path_config.py
```

### 文档导航
项目文档已按MAREF三才六层模型组织：

| 文档类型 | 目录 | 主要文档 |
|----------|------|----------|
| **架构文档** | `docs/architecture/` | 认知DNA、智能体架构、系统设计 |
| **技术文档** | `docs/technical/` | 技术规范、部署指南、运维文档 |
| **审计文档** | `docs/audit/` | 审计报告、分析文档（按年月组织） |
| **用户文档** | `docs/user/` | 用户指南、配置说明、工具参考 |
| **技能文档** | `skills/` | 智能体技能定义（保持原结构） |
| **第三方文档** | `vendor/` | 第三方库文档（保持原结构） |

**完整文档索引**: [docs/README.md](docs/README.md)

## 项目结构

```
openclaw/
├── .openclaw/                    # OpenClaw运行时状态目录
├── scripts/                      # 脚本目录
├── config/                       # 配置文件目录
│   └── paths.py                  # 路径配置模块（单一事实源）
├── docs/                         # 文档根目录（按三才六层模型组织）
├── skills/                       # 智能体技能定义
├── vendor/                       # 第三方依赖
├── CLAUDE.md                     # Claude Code项目配置
├── README.md                     # 项目主README（本文件）
├── setup_environment.py          # 环境变量设置工具
├── validate_path_config.py       # 路径配置验证脚本
└── document_migration_plan.md    # 文档迁移实施计划
```

## 核心原则

### MAREF框架指导
1. **超稳定性要求**: 系统在状态空间中收敛到稳定区域
2. **递归进化机制**: 智能体通过递归学习和进化提升能力
3. **多智能体协作**: 明确角色和职责的智能体协同工作
4. **契约驱动设计**: 明确的契约定义组件交互
5. **可观测性优先**: 系统状态完全透明，变更可追溯

### gstack工程化原则
- **质量门禁检查**: 每个关键节点前的严格质量检查
- **风险控制矩阵**: 识别风险并制定缓解措施
- **文档驱动**: 所有决策、配置、验证结果记录在案

## 开发指南

### 新贡献者
1. 阅读[认知DNA](docs/architecture/cognitive-dna.md)了解项目核心框架
2. 查看[快速开始](docs/user/getting-started.md)设置开发环境
3. 熟悉[系统设计](docs/architecture/system-design.md)理解架构

### 代码规范
1. 使用`config.paths`模块处理路径，避免硬编码
2. 遵循契约驱动设计原则，定义明确的接口契约
3. 保持文档与代码同步更新

### 文档贡献
1. 根据文档类型选择对应目录
2. 遵循命名规范：`{domain}-{topic}-{date}.md`
3. 更新相关索引文件

## 相关资源

### 项目文档
- [文档索引](docs/README.md) - 完整文档导航
- [CLAUDE.md](CLAUDE.md) - Claude Code项目配置
- [文档迁移计划](document_migration_plan.md) - 文档重组实施计划

### 工具脚本
- [环境变量设置](setup_environment.py) - 环境配置工具
- [路径配置验证](validate_path_config.py) - 配置完整性验证
- [代码质量审计](audit_code_quality.py) - 代码质量检查工具

### 部署计划
- [阶段性部署计划](docs/technical/deployment/staged-deployment-plan.md) - 工程化部署实施
- [部署指南](docs/technical/deployment/deployment-guide.md) - 部署操作指南

## 许可证

[待添加许可证信息]

---
**最后更新**: 2026-04-19  
**维护者**: OpenClaw核心团队  
**状态**: 活跃开发中