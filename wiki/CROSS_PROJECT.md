# 跨项目知识索引 (Cross-Project Knowledge Bridge)

## 项目关系

```
openclaw (引擎层) ←→ 003-open human (方法论层)
    代码/CI/自动化          协议/文档/知识蒸馏
```

两个项目是碳硅基共生架构的两个面，互相依赖，知识共享。

## 关联点映射

### 共享知识域

| 知识域 | openclaw 路径 | 003-open human 路径 |
|--------|--------------|-------------------|
| 架构决策 | `wiki/ARCHITECTURE.md` | `MEMORY.md` (关键决策) |
| 工作流模式 | `wiki/PATTERNS.md` | `CLAUDE.md` (工作流规范) |
| 协作约定 | `MEMORY.md` | `MEMORY.md` (协作约定) |
| AI 执行计划 | `.openclaw/orchestrator/tasks/` | `007-AI-plan/` |
| 审计报告 | `docs/audit/` | `012-审计-分析-报告/` |

### 队列路由

```
003-open human AI-plan 任务
    ↓ 完成
    ↓ 归档到
    ↓
openclaw/completed/queue_archives/openhuman_*
```

### 同步规则

1. **CLAUDE.md 版本追踪**: openclaw 升级 → 003-open human 同步评估
2. **MEMORY.md 决策双向同步**: 任一方更新后须检查另一方是否需要同步
3. **wiki/ 知识优先**: 新知识优先蒸馏到 openclaw wiki/，003-open human 通过 claude-mem 可检索
4. **队列状态**: 003-open human 的队列状态在 openclaw `.openclaw/orchestrator/tasks/` 中可追踪

## 协作约定

- 003-open human 文档产出定期同步到 openclaw wiki/
- 跨项目决策写入各自的 MEMORY.md，标记 `跨项目:` 前缀
- Agent 工作区启动时，MAIN SESSION 读取双方 MEMORY.md 了解全局状态

## 版本历史

- **v1.0** (2026-04-26): 初始跨项目索引，Phase 4 知识桥接建立
