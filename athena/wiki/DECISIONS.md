# Athena 语义层架构决策记录 (ADR)

> 版本：men0.semantic.v1 | 2026-05-04 | 更新：2026-05-04 实施后

---

## ADR-001: 采用六维语义层架构

**状态**：✅ 已实施
**日期**：2026-05-04
**决策者**：基于四轮全量研究综合分析

**背景**：
Athena 需要统一的语义层来处理意图解析、记忆管理、模式切换、工具路由、状态观测和跨Agent协作。当前 v0.2.0 工程中这些功能散落在各子系统中。

**决策**：
采用六维架构：意图语义核 + 认知模式切换 + 记忆语义塔 + 工具语义路由 + 状态语义编码 + 跨Agent互操作层。

**理由**：
- 六维是覆盖 Agent 完整生命周期的最小完备集
- 对标并超越了 Claude Code（三层记忆）和 Kimi K2.5（四模式）
- Carbon-Silicon 模式是独有创新

**后果**（实施后）：
- 35 源文件部署于 `openclaw/athena/semantic_layer/`
- 349 测试覆盖全模块
- 各子系统 Schema 已适配完成

---

## ADR-002: MVSL 策略——先做3段而非全量

**状态**：✅ 已实施（MVSL 3段 → 全量12段）
**日期**：2026-05-04

**背景**：
全量12个语义段 + Proto/JSON + Men0同步需要10周，但 v0.2.0 Phase 2 上下文压缩窗口只有4周。

**决策**：
采用最小可行语义层（MVSL）：仅 ROLE_DEFINITION / MEMORY_SNAPSHOT / ROUTING_SIGNALS 三个段 + 基础版 SemanticPromptCompiler。Carbon-Silicon 和 Men0 同步推迟到 v0.3.0。

**理由**：
- 与 Phase 2 上下文压缩强耦合，错过此窗口需额外3周
- 段级 Prompt Cache 优化（聚焦 ROLE 段不变性）对成本立竿见影
- 不显著增加工程复杂度
- v0.2.0 先验证语义段概念，v0.3.0 全量铺开

**后果**（实施后）：
- MVSL 3 段编译器已投产，12 段全量编译器已扩展
- `create_mvsl_registry()` + `create_full_registry()` 双工厂就绪

---

## ADR-003: Schema版本策略 men0.semantic.v1

**状态**：✅ 已实施
**日期**：2026-05-04

**背景**：
语义 Schema 将被子系统和跨Agent消息消费，需要版本策略管控演进。

**决策**：
- 初始版本号 `men0.semantic.v1.0`
- 首次发布前允许 Breaking Change
- 发布后严格向后兼容：新增字段OK，删除/重命名字段必须 bump 大版本
- 每个 SemanticMessage 携带 `schema_version` 字段

**理由**：
- 跨Agent场景下版本不匹配会导致语义解析失败
- 向后兼容保证旧版 Agent 仍能部分消费新消息

**后果**（实施后）：
- `SchemaRegistry` + `SchemaVersion` 类已实现
- 支持版本解析、兼容检查、冲突检测

---

## ADR-004: Proto + JSON 双 Schema 策略

**状态**：✅ 已实施
**日期**：2026-05-04

**背景**：
语义对象需要高性能跨语言传输（gRPC）和灵活的结构化生成（SGLang）。单一格式无法满足两个场景。

**决策**：
- 高性能路径（Men0 gRPC通信）：Protobuf
- 结构化生成路径（SGLang约束解码）：JSON Schema
- Python内部使用：Pydantic（与 Proto/JSON 互转）
- Pydantic 为 Source of Truth，Proto 和 JSON 通过代码生成

**理由**：
- Proto 比 JSON 在 gRPC 上快 3-10x
- SGLang XGrammar 原生支持 JSON Schema，不支持 Proto
- Pydantic 作为 Python 生态标准，提供最佳开发体验

**后果**（实施后）：
- `generate_proto.py` + `generate_json_schema.py` 脚本就绪
- `ProtoConvertible` mixin 提供 `to_proto()`/`from_proto()` 往返转换
- IntentPacket / SemanticStateSnapshot / SemanticMessage 三类互通

---

## ADR-005: Engram Gated Fusion → 置信度门控内存

**状态**：✅ 已实施
**日期**：2026-05-04

**背景**：
DeepSeek V4 的 Engram 模块实现了条件记忆的 gated fusion（σ(W·[hidden, memory])），Athena Layer 5 需要在分布式Agent间实现类似的"何时信任共享记忆"机制。

**决策**：
将 Engram 的 Gated Fusion 思想从模型内部迁移到系统级：
- confidence = σ(α·confirm_ratio + β·consistency + γ·freshness)
- N个Agent确认 → 置信度超阈值 → 自动升级为全局事实
- 矛盾检测 → 自动降级 → 触发澄清

**理由**：
- CRDT Merge 只解决同步，不解决"该不该信"
- 置信度门控提供自适应知识质量评估
- Engram 的 O(1) N-gram 查表可直接用于近似去重

**后果**（实施后）：
- `ConfidenceGatedMemoryStore` 已实现（ingest / compute_confidence / promote / demote / detect_contradiction）
- 阈值：high=0.8, medium=0.5；权重：α=0.4, β=0.35, γ=0.25

---

## ADR-006: 提示语义层优先于 Men0 同步

**状态**：✅ 已实施（提示语义层全量12段 + Men0 Bridge MVP 均已实现）
**日期**：2026-05-04

**背景**：
六维架构中，提示语义层和Men0 Bridge是两个独立的子系统。在资源有限时需排优先级。

**决策**：
Phase 2 优先实现提示语义层（Prompt Semantic Layer），Men0 Bridge 推迟到 Phase 4。

**理由**：
- 提示语义层是"单Agent内的语义结构化"，Men0是"跨Agent语义同步"
- 单Agent语义层先行，验证语义段概念后再做跨Agent扩展
- 提示语义层对 Prompt Cache 优化有直接收益
- Men0 依赖 OpenClaw Men0 v2 的就绪状态

**后果**（实施后）：
- v0.2.0: MVSL 3段 + 全量12段 均已投产
- v0.2.0: Men0 Bridge JSONL MVP 已实现（文件系统降级方案，待 gRPC 就绪后升级）

---

## ADR-007: CRDT 类型选型

**状态**：✅ 已实施
**日期**：2026-05-04

**背景**：
跨Agent语义同步需要解决并发冲突。三种主流 CRDT 方案可选：State-based、Operation-based、Delta-based。

**决策**：
针对不同语义数据类型选择不同 CRDT：
- 事实（单值更新）→ **LWW-Register**：时间戳大者胜出，平局按 agent_id 字典序
- 意图队列（增删）→ **OR-Set**：元素有唯一ID，tombstone 防逆向恢复
- 约束集（正交集操作）→ **Two-Phase Set**：added/removed 两阶段分离

**理由**：
- LWW-Register 语义简单，适合 "key→value" 的事实更新
- OR-Set 的 tombstone 机制保证"删除后不会被并发添加恢复"
- Two-Phase Set 的 added/removed 分离确保"移除优先于添加"

**后果**：
- 3 类 CRDT 部署于 `athena/semantic_layer/crdt/`
- 26 个测试覆盖全部 merge/roundtrip/edge cases

---

## ADR-008: Men0 Bridge — gRPC vs 文件系统 MVP

**状态**：✅ 文件系统 MVP 已实施；gRPC 待 Phase 4 后期
**日期**：2026-05-04

**背景**：
Men0 Protocol v2 设计为 gRPC 通信，但 Phase 4 启动时 gRPC 基础设施未就绪。

**决策**：
- 立即采用 JSONL + flock 文件系统作为 Men0 Bridge MVP
- gRPC 作为 Phase 4 后期升级路径

**理由**：
- JSONL 文件零依赖、可审计、可 Git 版本化
- 与现有 Men0 v2 的 JSONL 方案一致
- 不影响 CRDT 核心逻辑（CRDT 层与传输层解耦）
- gRPC 就绪后，Men0Bridge 仅需替换 `_write_message/_read_messages`

**后果**：
- `Men0Bridge` 实现 publish/consume/sync 完整生命周期
- 性能基准：单次 message write <1ms
- 路径：`athena/semantic_layer/men0/bridge.py`

---

## ADR-009: ConfidenceGate 阈值标定

**状态**：✅ 已实施
**日期**：2026-05-04

**背景**：
Engram Gated Fusion 的置信度公式需要标定阈值和权重参数。

**决策**：
- high_threshold=0.8, medium_threshold=0.5（基于 sigmoid 激活函数）
- α=0.4 (确认率), β=0.35 (一致性), γ=0.25 (新鲜度)
- sigmoid slope=6 (steeper 区分度)
- max_age=86400s (24h 过期)

**理由**：
- 0.8 阈值在 sigmoid 函数中对应 raw≈0.61，需要至少 2/3 Agent 确认
- 确认率权重最高（0.4）——多Agent共识是最强信号
- freshness 权重 0.25——防止过时知识持久化
- sigmoid 提供平滑过渡而非硬阈值

**后果**：
- 性能基准：compute_confidence <1ms
- 实测：verification=50 → confidence>0.8, verification=0+contradictions=10 → <0.3
- 实现：`athena/semantic_layer/bridge/confidence_gate.py`
