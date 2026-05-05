# Knowledge Base Seed Index — Karpathy AutoResearch v0.2.0

> 种子来源：四轮研究的 50+ 份文档
> 编译时间：2026-05-03
> 状态：初始种子填充 (D10-1)

## 种子文档清单

本知识库的 raw/ 层应引用以下已有研究文档作为初始编译种子：

### 第一轮：Karpathy 方法论全量研究

| 文档 | 路径 | 关键概念 |
|------|------|---------|
| 综合研究总报告 | 019-工作台/收件箱/完成/v0.2.0 归档/Karpathy-AutoResearch-软件开发迁移-综合研究总报告.md | 方法论映射、4原则、ratchet loop |
| 方法论全量研究 | 019-工作台/收件箱/完成/v0.2.0 归档/Karpathy方法论全量研究.md | Karpathy 原始博客、视频、推文分析 |
| 量化评分标准 | 019-工作台/收件箱/完成/v0.2.0 归档/量化评分标准.md | 5维评分、阈值、val_bpb 对齐 |
| 工作流架构设计 | 019-工作台/收件箱/完成/v0.2.0 归档/智能工作流架构设计.md | 触发链、协同激活、Token 预算 |

### 第二轮：工具扫描与配置

| 文档 | 路径 | 关键概念 |
|------|------|---------|
| 全域代码生成工具扫描 | 019-工作台/收件箱/完成/v0.2.0 归档/全域代码生成工具扫描报告.md | 5 工具对比、Claude Code/OpenCode/Trae CN/VSCode/Codex |
| 各工具配置规范 | 019-工作台/收件箱/完成/v0.2.0 归档/各工具配置规范.md | 三层配置体系、安全约束、跨工具一致性 |

### 第三轮：部署与消费

| 文档 | 路径 | 关键概念 |
|------|------|---------|
| 全链路部署与消费审计 | 019-工作台/收件箱/完成/v0.2.0 归档/Karpathy-AutoResearch-全链路部署与消费-全量审计报告.md | 部署完整性、消费路径、41 项检查 |
| Skill 部署报告 | 019-工作台/收件箱/完成/v0.2.0 归档/Karpathy经验Skill部署报告.md | 7 Skill 源部署差分、版本追踪 |
| 已批准项目消费路径分析 | 019-工作台/收件箱/完成/v0.2.0 归档/已批准项目消费路径分析.md | 6 项目、3 消费路径、Human Gate 集成 |
| 全域压力测试报告 | 019-工作台/收件箱/已批准/Karpathy-AutoResearch-全链路-全域压力测试报告.md | 154 项检查、10 维度、89.2/100 |

### 第四轮：Skill 与素材库

| 文档 | 路径 | 关键概念 |
|------|------|---------|
| Karpathy 经验 Skill 素材库 | 019-工作台/收件箱/完成/v0.2.0 归档/Karpathy经验Skill素材库.md | Ratchet Loop 模板、决策矩阵、反模式 |
| 消费示例 (OpenHuman) | 019-工作台/收件箱/完成/v0.2.0 归档/消费示例-OpenHuman-v0.2.0-Dashboard.md | Dashboard 消费实战 |

### v0.1.0 归档参考

| 文档 | 路径 | 状态 |
|------|------|------|
| OpenHuman-Athena-autoresearch 五维灵魂拷问 | 017-v0.1.0-归档/007-AI-plan-完成/ | 已归档 |
| OpenHuman-Athena-autoresearch Claude-Code 拆解 | 017-v0.1.0-归档/007-AI-plan-完成/ | 已归档 |
| 内容蒸馏报告 | 017-v0.1.0-归档/007-AI-plan-完成/ | 已蒸馏到 v0.2.0 |

### 7 Karpathy Skills (作为 raw/ 源)

| Skill | 部署位置 | 核心协议 |
|-------|---------|---------|
| karpathy-principles.json | ~/.claude/skills/ | 4 核心原则 + autoApply |
| karpathy-autoresearch-loop.md | ~/.claude/skills/ | 10 步 ratchet loop |
| karpathy-code-quality.md | ~/.claude/skills/ | 5 维评分标准 |
| karpathy-simplicity.md | ~/.claude/skills/ | 简洁决策矩阵 |
| karpathy-knowledge-bases.md | ~/.claude/skills/ | 三层架构 |
| karpathy-goal-driven.md | ~/.claude/skills/ | 目标拆解协议 |
| karpathy-multi-agent.md | ~/.claude/skills/ | 多 Agent 协调 |

## 编译状态

| 指标 | 值 |
|------|-----|
| 种子文档数 | 17+ |
| 已编译页面 | 0 (待首次 compile) |
| 待编译概念 | 5 维评分、Ratchet Loop、Human Gate、消费路径、一票否决 |
| 建议首次编译命令 | `compile knowledge_base/raw/` |

## 编译后目标

编译完成后应生成：
- `index.md` — 全文摘要索引
- `concepts/ratchet-loop.md`
- `concepts/scoring.md`
- `concepts/human-gate.md`
- `concepts/consumption-path.md`
- `entities/athena.md` / `entities/openclaw.md` / `entities/openhuman.md`
- `relations.md`
