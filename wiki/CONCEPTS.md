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

## HappyHorse 视觉工程概念

### PENTA 五层提示词架构

HappyHorse 提示词库的标准化架构。所有提示词必须按五个层次组织，顺序不可打乱：

| 层级 | 名称 | 功能 | 权重 |
|------|------|------|------|
| L1 | 风格锚定层 | 锁定整体视觉风格与格式 | 20% |
| L2 | 镜头语言层 | 定义机位、运镜、构图 | 20% |
| L3 | 主体刻画层 | 角色/物体/场景的详细描述 | 25% |
| L4 | 光影氛围层 | 光照、色彩、粒子、特效 | 20% |
| L5 | 技术输出层 | 分辨率、格式、负空间、质量词 | 15% |

视觉锚点：Marvel Cinematic Universe 预告片美学 | 竖屏 9:16 | IMAX 级史诗感
主题内核：碳基-硅基共生、OpenClaw 蜂群网络、MAREF 协议、Athena Agent

参考: `.claude/skills/happyhorse-prompt-library/SKILL.md`

### Playwright Persistent Context 自动登录 ⚠️ 已废弃 (deprecated — 2026-04-16)

> **废弃原因**: 千问 HappyHorse 频道需要扫码登录且 cookie 有效期仅 72h，该方案已被 DashScope API 直连方案替代。相关脚本 `comfyui_workspace/Pixelle-Video/scripts/` 不再维护。

千问（qianwen.com）需要微信/支付宝扫码登录。使用 Playwright 的 `launch_persistent_context` API 将浏览器 profile（含 cookie、localStorage）持久化到 `.qianwen-auth/chrome-persistent/` 目录。

首次运行弹窗让用户扫码一次 → cookie 自动保存 → 后续 headless 运行自动恢复登录态。Cookie 有效期 72h，过期后需重新扫码。

脚本: `comfyui_workspace/Pixelle-Video/scripts/ensure_login.py`

### HappyHorse E2E 自动化流水线 ⚠️ 已废弃 (deprecated — 2026-04-16)

> **废弃原因**: 同上。当前使用 DashScope API 直连方案：`scripts/clawra/generate_happyhorse_video.py`

千问 HappyHorse 1.0 图生视频的完整自动化流程：
1. `ensure_login` → 检查 cookie 新鲜度
2. 打开 qianwen.com → 进入 HappyHorse 频道
3. 通过 `expect_file_chooser` + `set_files` 上传参考图（触发 OSS 上传链）
4. Slate.js contenteditable 编辑器中填入提示词
5. 点击发送 → 轮询视频生成 → 下载 mp4

已验证完整管道可通（gate validation 1-5），当前唯一阻塞是账户额度（需 2 点/次生成）。

脚本: `comfyui_workspace/Pixelle-Video/scripts/daily_hh_test.py`

### DashScope API 直连方案

通过百炼 DashScope `/api/v1/services/aigc/video-generation/video-synthesis` 端点直接调用 `happyhorse-1.0-i2v` 模型。与百炼账户余额共享，按秒计费（720P: 0.9 元/秒，Pro 会员 0.44 元/秒）。

核心流程：构建 PENTA 五层提示词 → 提交异步任务（获取 task_id）→ 轮询任务状态（PENDING → RUNNING → SUCCEEDED/FAILED）→ 下载 mp4 视频（含音频）。

主脚本: `scripts/clawra/generate_happyhorse_video.py`

### jsDelivr CDN 图片托管

GitHub Raw URL（`raw.githubusercontent.com`）在国内网络环境下可能被墙，导致 HappyHorse 服务器无法下载参考图。解决方案是使用 jsDelivr CDN 镜像：

- GitHub Raw: `https://raw.githubusercontent.com/frankiehot-tech/openclaw/main/assets/athena_ref.jpg`
- jsDelivr CDN: `https://cdn.jsdelivr.net/gh/frankiehot-tech/openclaw@main/assets/athena_ref.jpg`

jsDelivr 全球 CDN 不依赖 GitHub Raw 服务器，HappyHorse 可稳定访问。

### 异步任务轮询

HappyHorse 视频生成是异步任务模式：
1. **提交任务** → API 返回 `task_id`
2. **PENDING** → 任务排队中
3. **RUNNING** → 模型推理中（通常 2-5 分钟）
4. **SUCCEEDED** → 生成完成，可从 `video_url` 下载
5. **FAILED** / **CANCELED** → 任务失败或取消

脚本通过 `poll_task_status()` 每 10 秒轮询一次状态，带网络重试机制（最多 5 次）。

## 外部概念

### 知识优先级

Wiki 知识查找时的优先级顺序：
1. `wiki/`（蒸馏后的结构化知识）
2. claude-mem（原始记忆搜索）
3. `memory/`（人类可读的会话日志）

## Athena 语义层概念 (v0.2.0)

### 提示语义层 (Prompt Semantic Layer)

将传统文本 Prompt 升级为 12 段语义图结构。每段有独立类型、Token 预算、Cache 锚点：
- **不可变段** (4): ROLE_DEFINITION, CAPABILITY_MANIFEST, CONSTRAINT_SET, TOOL_REGISTRY
- **会话级** (4): TASK_GRAPH, MEMORY_SNAPSHOT, AMBIGUITY_CONTEXT, DECISION_QUEUE
- **请求级** (3): USER_INTENT, MODE_DECLARATION, ROUTING_SIGNALS
- **元数据** (1): META

实现位置: `athena/semantic_layer/prompt/`

### 12 段编译器

`SemanticPromptCompiler` 做段级增量编译：只重编译哈希变更的段，不变段复用 HTML 注释边界标记作为 Cache 锚点。编译引擎通过 `create_full_registry()` 注册全部 12 段。

实现位置: `athena/semantic_layer/prompt/prompt_compiler.py`

### Carbon-Silicon 模式

5 种认知模式之一：Agent 检测到 2+ 维度歧义 > 0.7 时自动暂停，推送决策点等待人类判断。由 `ModeSwitchingEngine` 和 `AmbiguityInjector` 联合驱动。

### 歧义显式化 (Ambiguity Explicitification)

不猜测歧义消解，而是量化为四维 `AmbiguityVector` (scope/target/modality/authority)，自动注入澄清问题。`AmbiguityInjector` 提供 12 个模板跨维度轮转。

### CRDT 无冲突数据类型

跨Agent 语义同步的数学基础：
- **LWW-Register**: 时间戳大的胜出 → 事实同步
- **OR-Set**: 元素有唯一 ID，移除不逆向 → 意图队列
- **Two-Phase Set**: 分 added/removed 两阶段 → 约束集

实现位置: `athena/semantic_layer/crdt/`

### 向量时钟 (VectorClock)

分布式逻辑时钟，用于检测并发事件的因果/并发关系。支持 merge、tick、happened_before、is_concurrent 操作。

### 置信度门控 (Confidence Gating)

借鉴 DeepSeek V4 Engram 的 Gated Fusion：confidence = σ(α·confirm_ratio + β·consistency + γ·freshness)。
- >0.8: 自动升级为全局事实
- 0.5-0.8: 待验证
- <0.5: 仅本地保留

### Men0 Bridge (文件系统 MVP)

JSONL + flock 实现跨Agent 语义消息交换。不依赖 gRPC，提供 publish/consume/sync 完整生命周期。

实现位置: `athena/semantic_layer/men0/`

### Pydantic↔Proto 互转

`ProtoConvertible` mixin 提供 `to_proto()` / `from_proto()` 方法。Pydantic 为 Source of Truth，Proto 通过 `generate_proto.py` 脚本生成，JSON Schema 通过 `generate_json_schema.py` 生成。

### Schema 版本注册

`SchemaRegistry` 管理 `men0.semantic.v1` → v2 演进，支持版本冲突检测、向后兼容检查和兼容性验证。
