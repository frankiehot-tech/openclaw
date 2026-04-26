---
type: architecture
created: 2026-04-24
updated: 2026-04-24
tags: [openclaw, architecture, athena, maref]
---

# 系统架构

## 项目概述

OpenHuman（碳硅基共生）是一个 AI 驱动的开发环境，核心目标是让 AI Agent 能够自动执行复杂工程任务。

### 定位

- **不是**普通的代码仓库
- **是**一个 AI Agent 工作流引擎 + 任务执行平台
- Agent 通过 `AGENTS.md`/`CLAUDE.md` 定义行为规范，通过任务队列驱动工作

## 核心组件

### Athena 工作流引擎

核心任务编排系统，负责：

- **任务队列管理**：AI plan 的入队、分类、消费、状态维护
- **Agent 编排**：多 Agent 协作、子 Agent 注册 (`subagent_registry`)
- **事件总线**：`hook_event_bus` 驱动 Agent 间通信
- **Build Runner**：`athena_ai_plan_runner.py` 执行 build 任务
- **预算管理**：四级生存模式（normal/low/critical/paused），控制 token 消耗
- **控制面**：`control_plane.yaml` 配置本地优先策略和显式规则

相关代码：`athena/`、`scripts/athena_*.py`

### MAREF 记忆系统

记忆与沙箱子系统：

- **记忆存储**：SQLite (`maref_memory.db`) + JSONL 日志
- **沙箱隔离**：Agent 的实验性操作在沙箱中执行
- **河图策略**：所有 MAREF 工作流变更需经过河图策略验证

相关代码：`maref_sandbox/`、`memory/maref/`

### Execution Harness

任务执行框架：

- **多队列分类**：按任务类型自动分配队列
- **Manifest 自动生成**：build 前生成任务清单
- **Preflight 门禁**：入队前验证
- **暂停原因结构化**：暂停状态有结构化原因说明
- **Memory 回写**：完成后自动将摘要写回记忆
- **空闲态提示**：无事可做时给出下一步建议

相关代码：`harness/`

### TenacitOS Web Dashboard

可视化面板（基于 `carlosazaustre/tenacitOS`）：

- **Mission Control**：任务状态总览
- **System Monitor**：系统资源监控（内存、CPU）
- **队列管理界面**：卡片级拉起、暂停、重试
- **仓库锚点**：管理项目关联

路径：`vendor/tenacitOS`，运行在 `localhost:3000`

### 自动修复链 (nanobot)

自动化故障恢复系统：

- **自动修复桥接器**：检测队列异常并自动修复
- **幂等入队**：同一故障不重复入队
- **Smoke 测试**：修复后自动验证
- **状态回写**：修复结果写回记忆

### 其他组件

| 组件 | 用途 | 路径 |
|------|------|------|
| OpenSpace | 技能进化与安全沙箱 | `agent_system/` |
| Research Engine | BLS 数据接入、评分热力图 | `athena/research/` |
| AutoResearch | 自动实验迭代引擎 | `athena/autoresearch/` |
| Observability | OpenTelemetry 监控 | `observability/` |
| Guardrails | 前置授权与安全策略 | `agents/guardrails/` |

## 数据流

```
用户请求
    ↓
Athena 任务队列 (Queue)
    ↓
Build Runner → Preflight 验证 → 执行
    ↓                        ↓
  Manifest 生成          Execution Harness
    ↓                        ↓
  记忆回写 (MEMORY/MAREF)    结果交付
    ↓
  Session 摘要 → wiki/sessions/ (LLM Wiki 蒸馏)
```

## 技术栈

| 层 | 技术 |
|---|------|
| 后端语言 | Python（主要）、少量 TypeScript |
| AI 模型 | DeepSeek（首选）、Claude |
| IDE/工具 | opencode Desktop App、Claude Code CLI |
| 记忆存储 | claude-mem (MCP)、MAREF (SQLite)、memory/*.md |
| 知识蒸馏 | LLM Wiki (`wiki/`) |
| 前端 | TenacitOS (React, Next.js) |
| 监控 | OpenTelemetry、SigNoz |
| 包管理 | pip、npm、Bun |

## 版本状态

- **opencode**: v1.14.22
- **claude-mem**: v12.3.8
- **LLM Wiki**: v1.0（2026-04-24 初始化）
