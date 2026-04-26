---
type: concept
created: 2026-04-24
updated: 2026-04-24
tags: [concepts, glossary, athena]
---

# 领域概念

## 项目核心概念

### OpenHuman（碳硅基共生）

项目代号。碳硅基 = 碳基（人类）+ 硅基（AI）共生协作。目标不是用 AI 替代人类，而是让两者在工程流程中互补协作。

### LLM Wiki

让 AI 自动将原始资料编译为持久化 Markdown 知识库的模式。后续查询直接读 wiki 而非重新解析原始文档，实现知识复利。

核心原则：
- **Source → Compile → Query**：原始资料读一次，编译为 wiki，之后只查 wiki
- **Atomic pages**：单页大小有上限，不堆积
- **Index-first**：通过索引导航，不全盘扫描
- **[[wikilinks]]**：交叉引用形成知识图谱

### 知识复利 (Knowledge Compounding)

每次会话产生的知识不会丢失。新知识在已有知识基础上叠加而非重复。类似金融复利——知识积累得越多，Agent 越智能。

### 蒸馏 (Distillation)

将原始、冗余的信息提炼为精炼、结构化的知识。类似从原油中精炼汽油。在项目上下文中：
- `memory/*.md` = 原油（原始日志）
- claude-mem = 仓储（可搜索）
- `wiki/` = 精炼汽油（结构化知识）

## 工作流概念

### AI Plan (AI 计划卡)

Athena 的任务单元。每个 AI plan 是一个 Markdown 文档，描述一个需要 AI 执行的任务。包含：
- `queue_item_id`：唯一标识
- `root_task_id`：根任务 ID
- 阶段（stage）：proposal → approved → build → completed
- 执行说明文档路径

### 四级生存模式 (Budget Survival Modes)

预算控制的四级状态，控制 Agent 行为：
- **normal**：正常模式，无限制
- **low**：低预算模式，限制 token 使用
- **critical**：关键模式，仅允许关键操作
- **paused**：暂停模式，停止所有操作

### Execution Harness

任务执行框架，提供标准化执行环境。核心概念：
- **Preflight**：执行前验证（路径、依赖、权限）
- **Manifest**：任务清单（描述任务范围）
- **Lane**：执行通道（支持多 lane 并行/重放）
- **Memory 回写**：执行结果自动写回记忆系统

### 路径漂移 (Path Drift)

项目中常见的反模式：AI plan 文档中引用的文件路径与工作区实际路径不一致。通常是因为文件被移动、重命名后文档没有同步更新。执行任务时 Agent 需主动检测并纠正。

### 自动修复链

当系统检测到队列异常（如任务卡住、导入失败）时，自动触发修复流程：
1. 检测异常 → 2. 定位根因 → 3. 执行修复 → 4. Smoke 验证 → 5. 状态回写

## 技术概念

### MCP (Model Context Protocol)

AI 模型与外部工具/数据之间的标准通信协议。claude-mem 通过 MCP 提供记忆工具给 opencode Desktop App。

### 河图策略

MAREF 工作流的安全策略体系。所有 MAREF 工作流变更需要经过河图策略验证，确保变更不影响系统稳定性。

### 子 Agent 注册 (Subagent Registry)

Agent 管理子 Agent 的注册中心。主 Agent 可以将子任务委派给专门的子 Agent，子 Agent 执行完毕后返回结果。

### 事件总线 (Event Bus)

Agent 间的异步通信机制。`hook_event_bus` 负责在组件之间传递事件，驱动工作流执行。

### 本地优先策略 (Local-First Policy)

控制面配置策略。优先在本地执行操作，只有在本地无法完成时才请求远程资源。通过 `control_plane.yaml` 配置。

## 外部概念

### 知识优先级

Wiki 知识查找时的优先级顺序：
1. `wiki/`（蒸馏后的结构化知识）
2. claude-mem（原始记忆搜索）
3. `memory/`（人类可读的会话日志）
