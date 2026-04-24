"""
Queue Runner — 从 Athena plan_queue 消费任务并执行

核心组件:
- QueueConsumer: 从 .openclaw/plan_queue/ 拉取任务
- BuildWorker: 执行 AI Plan 的 build 阶段
- BudgetController: 预算感知的执行控制
- PreflightGate: 执行前验证
- MemoryWriter: 结果回写到记忆系统
"""
