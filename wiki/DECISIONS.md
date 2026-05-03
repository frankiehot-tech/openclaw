---
type: decision
created: 2026-04-24
updated: 2026-05-03
tags: [decisions, adr]
---

# 设计决策记录

每个决策记录包括：上下文 → 选项 → 决策 → 理由 → 后果

---

## 架构决策

### ADR-001: 使用文件系统而非数据库存储 wiki

- **上下文**: 需要持久化、结构化、可版本控制的知识存储
- **选项**:
  1. Markdown 文件（Git 版本化，人类可读，LLM 原生）
  2. SQLite 数据库（可查询，但不易读）
  3. claude-mem（已有，但非结构化）
- **决策**: 采用 Markdown 文件系统
- **理由**:
  - 文件可被 Git 追踪（版本历史免费）
  - 人类可直接阅读和编辑
  - LLM 原生理解 Markdown
  - 零依赖
  - 与现有 `memory/` 模式一致
- **后果**: 需要维护页面大小和索引，避免文件过多

### ADR-002: 使用 claude-mem 作为 L1 原始记忆层

- **上下文**: 需要快速捕获和检索会话中的事实
- **选项**:
  1. 仅用 claude-mem
  2. 仅用 wiki 文件
  3. 两者结合：claude-mem 为 L1，wiki 为 L2
- **决策**: 两者结合
- **理由**:
  - claude-mem 快且自动（已有 MCP 工具）
  - wiki 提供结构化蒸馏
  - 互补而非替代
- **后果**: Agent 需要维护两个知识源的一致性

---

## 项目历史决策

### 四级生存模式设计 (2026-04-03)

- **上下文**: 预算控制需要精细化管理，避免 AI 在无预算时继续消耗 token
- **选项**:
  1. 硬性停止（on/off）
  2. 四级模式（normal/low/critical/paused）
  3. 按 token 百分比动态调整
- **决策**: 四级生存模式
- **理由**: 提供平滑降级而非二值切换，让系统在预算紧张时仍能维持关键功能
- **后果**: 需要实现模式映射、自动转换逻辑、心跳检测集成

### Execution Harness 重构 (2026-03-28 → 2026-04-01)

- **上下文**: 任务执行缺少标准化框架，导致路径漂移、导入错误、状态不一致
- **决策**: 从 ad-hoc 脚本执行迁移到 Harness 框架
- **关键特性**:
  - Manifest 自动生成
  - Preflight 门禁验证
  - 多队列分类
  - 暂停原因结构化
  - Memory 回写自动集成
- **后果**: 所有新任务执行需要经过 Harness 流程

### 本地优先控制面 (2026-04-20)

- **上下文**: 部分操作需要在本地完成，不能依赖远程服务
- **决策**: 实现 `control_plane.yaml` 配置本地优先策略
- **关键规则**: `local_first_policy.explicit_rules` 指定哪些操作强制本地执行
- **后果**: 控制面分层：本地层 vs 远程层

### Event Bus 驱动的 Subagent 架构 (2026-04-02)

- **上下文**: Agent 间需要异步通信，避免同步阻塞
- **决策**: 基于 `hook_event_bus` 的事件驱动 subagent 架构
- **关键组件**: Subagent Registry 注册所有子 Agent，Event Bus 传递消息
- **后果**: 需要维护 subagent 生命周期和事件路由

### ADR-003: SAST + LLM 双层审计架构

- **上下文**: 需要构建自动化审计流水线替代人工代码审查。AI 直接裸扫代码库成本高、误报多
- **选项**:
  1. LLM 直接扫描全量代码（23K 初始告警，95%+ 误报）
  2. SAST 工具（Ruff/SonarQube）先做规则过滤 → LLM 复核 SAST 告警 + 检测逻辑漏洞
  3. 仅用 SAST 工具，不用 LLM
- **决策**: SAST + LLM 双层架构
- **理由**:
  - SAST 层（Ruff）快速、便宜、确定性强，过滤 90%+ 噪声
  - LLM 层只复核 SAST 无法检测的语义问题（逻辑漏洞、安全后门）
  - 成本降低约 10 倍 vs LLM 直接裸扫
  - 实际验证：23K → 137 的真实问题压缩比
- **后果**: 需要维护 SAST 规则配置 + LLM 提示词两套系统

### ADR-004: 第三方目录排除策略

- **上下文**: `scripts/clawra/`, `backups/`, `tools/claude-code-setup/` 等目录包含第三方/生成代码，不应计入项目质量指标
- **决策**: 在 `pyproject.toml` 的 `[tool.ruff] exclude` 中排除所有第三方/外部目录
- **理由**: 避免质量门禁被外部代码的噪音误导，聚焦核心代码质量
- **后果**: 需要明确界定核心代码 vs 外部代码的边界

### ADR-006: 采纳 Karpathy AutoResearch 工作流

- **日期**: 2026-05-03
- **上下文**: Andrej Karpathy 的 AutoResearch 方法论（ratchet loop 自主实验循环）已从 Python/ML 领域完整迁移到软件开发领域，本地基础设施已就绪
- **选项**:
  1. 全自动 ratchet loop（v0.2.0 目标，需 LLM Gateway + CodeFlow 管道）
  2. 手动/半自动 ratchet loop（现在可用：Claude Code + 5维评分 + git commit/reset）
  3. 仅嵌入原则，不运行自主循环
- **决策**: 立即采用手动/半自动模式（选项2），在 openclaw 和自动化工作流中嵌入 Karpathy 原则，逐步向 v0.2.0 全自动模式演进
- **理由**:
  - 基础设施已就绪（Claude Code + 5维评分标准 + git 机制）
  - 不需要等 v0.2.0 即可获得方法论收益
  - openclaw AGENTS.md 已内建代码生成四原则 + 5维评分 + ratchet loop 协议
  - Claude Code 端已部署 5 个 Karpathy Skill（principles + code-quality + simplicity + autoresearch-loop + knowledge-bases）
- **后果**: 每次代码改动需自我评估 5 维评分；自主迭代时遵循 ratchet loop 协议；wiki 需定期健康检查
- **来源**: [[CROSS_PROJECT]] → AutoResearch/Karpathy软件开发迁移/

### ADR-005: 采用 llm-wiki 模式实现知识复利

- **上下文**: 当前 wiki/ 基础设施存在但未充分利用；会话知识在每次会话后丢失
- **参考**: [karpathy/llm-wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- **决策**: 按 llm-wiki 模式强化 wiki/ 使用：每次会话结束时自动写入 session 摘要、更新索引和日志
- **理由**:
  - 会话上下文有限，知识需要持久化
  - wiki 是 Markdown 文件，可 Git 版本化
  - LLM 原生理解 Markdown，零依赖
- **后果**: 每次会话结束需额外 token 用于 wiki 写入；长期收益远大于成本
