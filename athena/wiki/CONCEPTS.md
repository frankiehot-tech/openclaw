# Athena 语义层概念体系

> 版本：men0.semantic.v1 | 2026-05-04

## 核心概念树

```
Athena 语义层
├── 意图语义核 (Intent Core)
│   ├── IntentPacket — 意图数据包（顶层语义对象）
│   ├── SemanticFrame — 语义框架（动作+对象+上下文）
│   ├── AmbiguityVector — 歧义向量（四维歧义量化）
│   └── L1/L2/L3 分层解析
│
├── 认知模式 (Cognitive Mode)
│   ├── instant — 即时响应（本地 Gemma 4-E2B, <300ms）
│   ├── thinking — 深度推理（云端 DeepSeek V4 Pro）
│   ├── agent — 工具执行（Kimi 2.6 + MCP）
│   ├── swarm — 蜂群并行（100+ 子Agent）
│   └── carbon-silicon — 人机回环（HITL）
│
├── 记忆语义塔 (Memory Semantic Tower)
│   ├── Layer 1: Persistent Memory — athena_memory.md
│   ├── Layer 2: Active Retrieval — Semantic Grep
│   ├── Layer 3: Semantic Daemon — 后台索引（对标Chyros）
│   ├── Layer 4: Procedural Memory — Skill Patterns
│   └── Layer 5: Shared Context — Men0 跨Agent共享
│
├── 提示语义层 (Prompt Semantic Layer)
│   ├── PromptSegmentType — 12种标准化语义段
│   ├── SemanticPromptCompiler — 段级增量编译器
│   ├── SemanticPromptGraph — 语义Prompt图
│   └── AmbiguityInjector — 歧义注入器
│
├── 工具语义路由 (Tool Semantic Router)
│   ├── ToolSemanticRegistry — 工具语义注册表
│   ├── ToolSemanticSearchResult — 语义匹配结果
│   └── ToolExecutionPlan — 工具执行计划
│
├── 状态语义编码 (State Semantic Codec)
│   ├── SemanticStateSnapshot — 认知状态快照
│   ├── StateDiff — 状态差分
│   ├── FactTriple — 可查询事实三元组
│   └── DecisionPoint — 待决策点
│
└── 跨Agent语义互操作 (Men0 Bridge)
    ├── SemanticMessage — 语义消息
    ├── Men0SharedState — 共享状态
    ├── CRDT Merge — 最终一致性合并
    └── ConfidenceGating — 置信度门控
```

## 关键术语

| 术语 | 定义 | 类比 |
|------|------|------|
| **语义对象** | 携带类型标记的结构化数据，可跨子系统传递 | JSON-LD 的 @type |
| **语义段** | Prompt 中具有独立语义标记的区块 | HTTP Header vs Body |
| **意图指纹** | SHA256(verb+object_type+context_hash) | Git commit hash |
| **认知状态** | Agent 当前的心理状态标记 (planning/executing/reflecting/blocked/ambiguous/awaiting_human) | 进程状态 (RUNNING/BLOCKED/WAITING) |
| **置信度门控** | 借鉴Engram的σ(W·[hidden, memory])，决定知识是否全局化 | Circuit Breaker 的阈值 |
| **N-gram签名** | 借鉴Engram的多重哈希，用于语义事实的近似去重 | SimHash |
| **Carbon-Silicon** | 需要人类判断的认知模式，Agent主动暂停等待语义注入 | Kernel的WAIT_FOR_USER_INPUT |
| **歧义显式化** | 不"猜测"歧义消解，而是标记歧义维度并触发澄清循环 | Rust的Result<T, E>必须显式处理 |
