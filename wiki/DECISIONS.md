---
type: decision
created: 2026-04-24
updated: 2026-05-04
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

### ADR-007: HappyHorse 自动化采用 Playwright Persistent Context 替代 CDP ⚠️ [已废弃 — 2026-04-16]

> **废弃原因**: 千问 HappyHorse 频道登录态不稳定（cookie 有效期 72h），且依赖第三方网站而非官方 API。已由 ADR-015（DashScope API 直连方案）替代。相关脚本目录 `comfyui_workspace/Pixelle-Video/scripts/` 不再维护。

- **日期**: 2026-05-03
- **状态**: ⚠️ 已废弃 → 参见 ADR-015
- **上下文**: 千问 HappyHorse 自动化需要浏览器登录态维持。原方案使用 CDP 连接外部 Chrome 实例，存在 WAF 触发概率高、cookie 管理复杂、需要额外的 Chrome Daemon 进程等问题。
- **选项**:
  1. CDP 连接外部 Chrome（原方案：chrome_daemon.py + cdp_browser_client.py）
  2. Playwright `launch_persistent_context`（浏览器 profile 持久化，内置 cookie 管理）
  3. 纯 API 调用（千问无公开 API）
- **决策**: 采用 `launch_persistent_context`
- **理由**:
  - cookie/localStorage 自动持久化到文件系统，无需额外管理
  - headless 模式下 WAF 触发率显著低于 CDP
  - 无需维护独立的 Chrome 守护进程
  - `expect_file_chooser` API 是唯一能在千问 React 层正确触发文件上传的方式
  - 已验证 5 轮 gate validation 全部通过
- **后果**: 需要维护 persistent context 目录 `.qianwen-auth/chrome-persistent/`（~50MB）；每 72h 需重新扫码登录；需要 `ensure_login.py` 脚本管理登录状态

### ADR-008: HappyHorse 提示词库采用版本化 Skill 模式管理

- **日期**: 2026-05-03
- **上下文**: 碳硅共生项目有完整的 HappyHorse 提示词库（PENTA 框架 + 4 文生图模板 + 4 图生视频模板 + 情绪变体矩阵 + 中文文案适配），需要纳入项目知识管理体系。
- **选项**:
  1. 仅保留原始 .md 文档在 Downloads 目录
  2. 编译为 `.claude/skills/` 下的版本化 Skill（SKILL.md 格式）
  3. 同时写入 wiki CONCEPTS.md
- **决策**: 选项 2 + 3 并行（Skill + Wiki 双层）
- **理由**:
  - Skill 格式支持版本号、user-invocable 触发，Claude Code 可直接调用
  - Wiki 格式提供交叉引用和知识图链接
  - 两层互补而不冗余
- **后果**: 提示词更新时需要同时维护两处；版本迭代需在 Skill 和 Wiki 中同步

### ADR-005: 采用 llm-wiki 模式实现知识复利

- **上下文**: 当前 wiki/ 基础设施存在但未充分利用；会话知识在每次会话后丢失
- **参考**: [karpathy/llm-wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- **决策**: 按 llm-wiki 模式强化 wiki/ 使用：每次会话结束时自动写入 session 摘要、更新索引和日志
- **理由**:
  - 会话上下文有限，知识需要持久化
  - wiki 是 Markdown 文件，可 Git 版本化
  - LLM 原生理解 Markdown，零依赖
- **后果**: 每次会话结束需额外 token 用于 wiki 写入；长期收益远大于成本

### ADR-009: Athena 语义层六维架构

- **日期**: 2026-05-04 (设计) → 2026-05-04 (实施)
- **状态**: ✅ 已实施
- **上下文**: Athena 需要统一的语义层处理意图解析、记忆管理、模式切换、工具路由、状态观测和跨Agent协作
- **决策**: 六维架构：意图语义核 + 认知模式切换 + 记忆语义塔 + 工具语义路由 + 状态语义编码 + 提示语义层 + 跨Agent互操作层
- **后果**: openclaw/athena/semantic_layer/ 已部署 28 个源文件 + 222 个测试

### ADR-010: MVSL 三步策略（最小可行语义层先行）

- **日期**: 2026-05-04
- **状态**: ✅ 已实施 (MVSL 3段) → ✅ 全量12段
- **上下文**: 全量12段需10周，但需快速验证语义段概念
- **决策**: Phase 2 先做 ROLE/MEMORY/ROUTING 三段 MVSL，Phase 3 补齐全量12段
- **后果**: Prompt Cache 命中率目标 76%→≥85%；12段全量编译器已投产

### ADR-011: Schema 三层定义 + 版本策略

- **日期**: 2026-05-04
- **状态**: ✅ 已实施
- **上下文**: 语义对象需高性能跨语言传输（gRPC）+ 灵活结构化生成（SGLang）+ Python 内部运行
- **决策**: Pydantic (Source of Truth) → Proto (gRPC) + JSON Schema (SGLang)，版本号 men0.semantic.v1
- **后果**: SchemaRegistry + SchemaVersion 已实现；Pydantic↔Proto 互转 (to_proto/from_proto) 已部署

### ADR-012: CRDT 语义同步内核

- **日期**: 2026-05-04
- **状态**: ✅ 已实施
- **上下文**: 跨Agent 语义状态同步需要无冲突合并
- **决策**: LWW-Register (事实同步) + OR-Set (意图队列) + Two-Phase Set (约束集)
- **后果**: CRDT 内核部署在 openclaw/athena/semantic_layer/crdt/；53 个测试覆盖

### ADR-013: Engram 置信度门控

- **日期**: 2026-05-04
- **状态**: ✅ 已实施
- **上下文**: DeepSeek V4 Engram 的 σ(W·[hidden, memory]) 门控，迁移到系统级
- **决策**: confidence = σ(α·confirm_ratio + β·consistency + γ·freshness)；>0.8 → global, 0.5-0.8 → pending, <0.5 → local
- **后果**: ConfidenceGatedMemoryStore 已实现；EngramInspiredFact 待后续增加

### ADR-014: Men0 文件系统 MVP

- **日期**: 2026-05-04
- **状态**: ✅ 已实施
- **上下文**: Men0 gRPC 未就绪时需降级方案
- **决策**: JSONL + flock 文件系统作为 Men0 Bridge MVP
- **后果**: Men0Bridge 实现 publish/consume/sync 完整生命周期；待 gRPC 就绪后升级

### ADR-015: HappyHorse 采用 DashScope API 直连方案替代浏览器自动化

- **日期**: 2026-04-16
- **状态**: ✅ 已实施
- **上下文**: ADR-007 的 Playwright 浏览器自动化方案存在根本性问题：
  1. 千问 HappyHorse 频道需要微信/支付宝扫码登录，cookie 有效期仅 72h
  2. 依赖第三方网站而非官方 API，稳定性无法保证
  3. WAF 可能触发反爬机制，headless 模式有封禁风险
  4. 需要维护浏览器 profile 目录（~50MB）和 Chrome 守护进程
  5. 该方案依赖的第三方网站 `happyhorse.cn` 并非阿里官方服务
- **选项**:
  1. 继续维护 Playwright 浏览器自动化（ADR-007 方案，维护成本高）
  2. 使用 DashScope 官方 `/video-synthesis` API + `happyhorse-1.0-i2v` 模型直连
  3. 自行搭建视频生成环境（GPU 成本极高）
- **决策**: 采用 DashScope API 直连方案（选项 2）
- **理由**:
  - 百炼（DashScope）是阿里云官方平台，`happyhorse-1.0-i2v` 是其正式发布的图生视频模型
  - 使用百炼 API Key（`sk-` 开头）直接调用，与 Qwen 等模型共享账户余额，无需独立充值
  - 按秒计费：720P 0.9 元/秒，Pro 会员 0.44 元/秒；1080P 1.6 元/秒
  - 异步任务模式稳定可靠，无需维护浏览器环境和登录态
  - 生成的视频包含音频（音画同步），无需额外合成步骤
- **后果**:
  - ADR-007 已废弃，相关脚本 `comfyui_workspace/Pixelle-Video/scripts/` 不再维护
  - 提示词需按 PENTA 五层架构组织，通过 `HAPPYHORSE_PROMPTS` 字典管理
  - 参考图需要通过公网可访问的 URL 传入（使用 jsDelivr CDN 托管 GitHub 图片）
  - 主脚本路径: `scripts/clawra/generate_happyhorse_video.py`
  - 提示词库维护: `.claude/skills/happyhorse-prompt-library/SKILL.md`
