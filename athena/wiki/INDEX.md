# Athena 语义层 Wiki Index

> 版本：men0.semantic.v1 | 更新：2026-05-04

## 快速导航

- [概念体系](CONCEPTS.md) — 语义层的核心概念定义与关系
- [设计决策](DECISIONS.md) — 架构决策记录 (ADR)
- [Schema 定义](../schemas/) — Proto / JSON / Pydantic 数据模型
- [核心引擎](../core/) — 意图核、模式切换、状态编码
- [提示语义层](../prompt/) — Prompt 编译器与段构建器
- [工具路由](../routing/) — 工具语义路由
- [记忆系统](../memory/) — 五层记忆语义塔

## 入口文档

| 文档 | 路径 | 说明 |
|------|------|------|
| Athena 语义层研究方案 | /Volumes/.../待审批/Athena语义层研究方案.md | 现状分析 + 改进方案 |
| SGLang 结构化生成 | ../8.2.1-SGLang结构化生成集成方案.md | 约束解码集成 |
| Gemma 4 L1 意图分类 | ../8.2.2-Gemma4-26B-A4B本地意图分类基准.md | 本地分类器基准 |
| DeepSeek V4 Engram | ../8.2.3-DeepSeek-V4-Engram与语义塔Layer5对齐.md | 条件记忆对齐 |

## 项目依赖

```
athena/semantic_layer
├── 依赖 OpenClaw: Men0 Protocol v2 (通信)
├── 依赖 OpenHuman: Human Gate v2 (审批)
├── 依赖 Skillos: Skill 签名验证
└── 组合 MAREF: 状态机 + TLA+ 验证
```

## 版本

| Schema 版本 | 状态 | 发布时间 |
|------------|------|---------|
| men0.semantic.v1 | 设计中 | 2026-05-04 |
