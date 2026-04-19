# MEMORY.md - 长期记忆


## OpenHuman-Athena-现实版路线图 (蒸馏于 2026-04-02 21:46:57)

- **queue_item_id**: athena_reality_roadmap
- **root_task_id**: 20260402-065141-research-openhuman-athena
- **阶段**: research
- **摘要**: 该短版路线图整体偏战略，但 T+3 未落地缺口可安全收敛为 SkillWeaver、业务对象账本、offline_survey 模拟闭环和一次收口审计四张窄卡。
- **源文档**: /Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/completed/OpenHuman-Athena-现实版路线图.md


## OpenHuman-AI市场情报与职业风险引擎-clean-room产品架构方案 (蒸馏于 2026-04-02 21:46:57)

- **queue_item_id**: ai_market_intel_clean_room_plan
- **root_task_id**: 20260402-070356-research-openhuman-ai-clean-room
- **阶段**: research
- **摘要**: 该母卡可安全收敛为 3 张前置 build 卡和 1 张 review 卡，但当前 AI plan 目录只读，以下为应落盘清单。
- **源文档**: /Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/completed/OpenHuman-AI市场情报与职业风险引擎-clean-room产品架构方案.md

## OpenHuman-Automaton 预算心跳与四级生存模式接入 (实施于 2026-04-03)

- **完成状态**: 最小可运行闭环已建立
- **核心组件**:
  1. **Budget Engine**: 财务预算管理、四级生存模式、预算心跳机制
  2. **四级生存模式**: normal (>30%剩余), low (10-30%), critical (2-10%), paused (≤2%)
  3. **预算心跳脚本**: 结构化状态输出、临界状态告警、手动/定时调用
  4. **Athena编排器集成**: 任务创建时预算预检、成本更新时消费记录、优雅降级
- **技术决策**:
  - 区分财务预算（成本管理）与上下文预算（token管理）
  - 本地优先持久化（SQLite），无需外部基础设施
  - 故障恢复与优雅降级：预算引擎不可用时自动跳过检查
- **验证结果**:
  - ✅ 冒烟测试通过 (5/5)
  - ✅ 负路径测试通过：预算耗尽时正确降级
  - ✅ 心跳输出正常（JSON/文本格式）
  - ✅ Athena编排器集成验证
- **下一步建议**:
  - 配置每日预算心跳定时任务
  - 集成到现有监控系统
  - 添加预算预测算法
  - 与真实支付系统对接

## OpenHuman-Fusion-Automaton 预算化技能执行循环 (实施于 2026-04-04)

- **完成状态**: 预算化技能执行最小闭环已建立
- **核心组件**:
  1. **Skill Cost Estimator**: 技能成本估算契约，支持基础成本、复杂度系数、参数权重、外部成本
  2. **Budgeted Skill Execution Engine**: 集成预算检查、成本估算、技能执行的统一引擎
  3. **四级生存模式映射**: 将预算模式映射到 Athena/Codex/OpenCode 行为差异
  4. **Athena Orchestrator 增强**: 添加预算模式行为感知，支持动态降级
- **技术决策**:
  - 协议优先设计：所有接口使用 dataclass 和枚举，支持序列化
  - 审计追踪：每个预算检查包含完整元数据，支持成本审计
  - 优雅降级：四级生存模式分别对应不同的 agent 行为限制
  - 最小侵入：在现有 Automaton MVP 组件基础上集成，不创建新服务
- **验证结果**:
  - ✅ 核心模块导入验证通过
  - ✅ 预算充足执行测试通过（预算批准验证）
  - ✅ 预算不足拒绝测试通过
  - ⚠️ 需要审批挂起测试（需调整成本估算参数）
  - ✅ 四级生存模式映射测试通过（4种模式完整映射）
  - ✅ 强制执行测试通过（跳过预算检查）
  - ✅ 配置文件路径修复（解决符号链接导入问题）
- **集成点**:
  - 与现有 Budget Engine 无缝集成
  - 通过技能注册表获取技能元数据
  - 通过 Athena 编排器提供预算模式行为
  - 配置文件：`mini-agent/config/skill_costs.yaml`
- **文档**: 已创建 `mini-agent/docs/budgeted_skill_execution.md` 集成指南
- **下一步建议**:
  - 优化成本估算模型，校准外部成本参数
  - 完善审批流程集成，实现人工审批界面
  - 添加更多边界测试，提高覆盖率
  - 集成到实际技能执行工作流中验证


## OpenHuman-Athena-WorkflowStability-Runner重启契约与Bootstrap硬化-VSCode执行指令 (蒸馏于 2026-04-15 07:42:42)

- **queue_item_id**: workflow_stability_runner_bootstrap_hardening
- **root_task_id**: 20260415-074216-build-openhuman-athena-workflowstability-runner-bootst
- **阶段**: build
- **摘要**: 收到，初始化完成。我是 OpenClaw 仓库的 VS Code / OpenCode Build Agent。
- **源文档**: /Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/completed/OpenHuman-Athena-WorkflowStability-Runner重启契约与Bootstrap硬化-VSCode执行指令.md


## OpenHuman-Athena-ExecutionHarness-完成后Memory回写与交付摘要-VSCode执行指令 (蒸馏于 2026-04-15 07:45:50)

- **queue_item_id**: execution_harness_memory_writeback
- **root_task_id**: 20260415-074532-build-openhuman-athena-executionharness-memory-vscode
- **阶段**: build
- **摘要**: - /Volumes/1TB-M2/openclaw
- **源文档**: /Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/completed/OpenHuman-Athena-ExecutionHarness-完成后Memory回写与交付摘要-VSCode执行指令.md


## OpenHuman-Athena-Bridge聊天入口收敛与状态真实化-VSCode执行指令 (蒸馏于 2026-04-15 08:34:24)

- **queue_item_id**: athena_chatruntime_bridge_status_build
- **root_task_id**: 20260415-083337-build-openhuman-athena-bridge-vscode
- **阶段**: build
- **摘要**: "type": "shell",
- **源文档**: /Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/completed/OpenHuman-Athena-Bridge聊天入口收敛与状态真实化-VSCode执行指令.md


## OpenHuman-TenacitOS-Desktop聊天运行态对齐-VSCode执行指令 (蒸馏于 2026-04-15 08:35:31)

- **queue_item_id**: athena_tenacitos_chatruntime_alignment_build
- **root_task_id**: 20260415-083438-build-openhuman-tenacitos-desktop-vscode
- **阶段**: build
- **摘要**: # 🤖 OpenClaw Build Agent Status Report
- **源文档**: /Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/completed/OpenHuman-TenacitOS-Desktop聊天运行态对齐-VSCode执行指令.md


## OpenHuman-nanobot-Athena-自动修复桥接器与幂等入队-VSCode执行指令 (蒸馏于 2026-04-15 08:37:49)

- **queue_item_id**: nanobot_auto_repair_bridge
- **root_task_id**: 20260415-083739-build-openhuman-nanobot-athena-vscode
- **阶段**: build
- **摘要**: # Bash Overview
- **源文档**: /Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/completed/OpenHuman-nanobot-Athena-自动修复桥接器与幂等入队-VSCode执行指令.md


## OpenHuman-nanobot-Athena-自动修复链Smoke与状态回写-VSCode执行指令 (蒸馏于 2026-04-15 08:38:06)

- **queue_item_id**: nanobot_auto_repair_smoke
- **root_task_id**: 20260415-083754-build-openhuman-nanobot-athena-smoke-vscode
- **阶段**: build
- **摘要**: "messages": [
- **源文档**: /Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/completed/OpenHuman-nanobot-Athena-自动修复链Smoke与状态回写-VSCode执行指令.md


## OpenHuman-Athena-Guardrails前置授权与阶段策略下沉-VSCode执行指令 (蒸馏于 2026-04-15 08:38:13)

- **queue_item_id**: athena_pretool_guardrails
- **root_task_id**: 20260415-083739-build-openhuman-athena-guardrails-vscode
- **阶段**: build
- **摘要**: 收到，我已初始化完成，当前作为 **OpenClaw 仓库的 VS Code / OpenCode Build Agent** 待命。
- **源文档**: /Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/completed/OpenHuman-Athena-Guardrails前置授权与阶段策略下沉-VSCode执行指令.md


## OpenHuman-Athena-Bridge聊天入口收敛与状态真实化-VSCode执行指令 (蒸馏于 2026-04-16 13:16:47)

- **queue_item_id**: athena_chatruntime_bridge_status_build
- **root_task_id**: 20260416-131604-build-openhuman-athena-bridge-vscode
- **阶段**: build
- **摘要**: # 🤖 OpenClaw Build Agent 状态报告
- **源文档**: /Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/completed/OpenHuman-Athena-Bridge聊天入口收敛与状态真实化-VSCode执行指令.md


## OpenHuman-nanobot-Athena-自动修复桥接器与幂等入队-VSCode执行指令 (蒸馏于 2026-04-16 13:17:44)

- **queue_item_id**: nanobot_auto_repair_bridge
- **root_task_id**: 20260416-131735-build-openhuman-nanobot-athena-vscode
- **阶段**: build
- **摘要**: - Basic commands or syntax?
- **源文档**: /Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/completed/OpenHuman-nanobot-Athena-自动修复桥接器与幂等入队-VSCode执行指令.md


## OpenHuman-nanobot-Athena-自动修复链Smoke与状态回写-VSCode执行指令 (蒸馏于 2026-04-16 13:17:58)

- **queue_item_id**: nanobot_auto_repair_smoke
- **root_task_id**: 20260416-131750-build-openhuman-nanobot-athena-smoke-vscode
- **阶段**: build
- **摘要**: It looks like you're interested in **Bash** (Bourne Again SHell), the default command-line interpreter for most Linux distributions and macOS.
- **源文档**: /Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/completed/OpenHuman-nanobot-Athena-自动修复链Smoke与状态回写-VSCode执行指令.md


## OpenHuman-Athena-Enterprise-控制面分层与本地优先策略作用域-VSCode执行指令 (蒸馏于 2026-04-16 13:21:34)

- **queue_item_id**: athena_enterprise_control_plane_scopes
- **root_task_id**: 20260416-132052-build-openhuman-athena-enterprise-vscode
- **阶段**: build
- **摘要**: 由于队列项说明文截断，请补充以下信息以便 Agent 生成具体实现代码：
- **源文档**: /Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/completed/OpenHuman-Athena-Enterprise-控制面分层与本地优先策略作用域-VSCode执行指令.md


## OpenHuman-Athena-WorkflowStability-Runner重启契约与Bootstrap硬化-VSCode执行指令 (蒸馏于 2026-04-18 17:52:41)

- **queue_item_id**: workflow_stability_runner_bootstrap_hardening
- **root_task_id**: 20260418-175241-build-openhuman-athena-workflowstability-runner-bootst
- **阶段**: build
- **摘要**: ✅ 成本记录成功: req_20260418_175241_c3f158612026-04-18 17:52:41,394 - agent.core.financial_monitor_adapter - INFO - 预算引擎连接成功
- **源文档**: /Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/completed/OpenHuman-Athena-WorkflowStability-Runner重启契约与Bootstrap硬化-VSCode执行指令.md


## OpenHuman-Athena-ExecutionHarness-根路径Helper与路径漂移收敛-VSCode执行指令 (蒸馏于 2026-04-18 17:52:41)

- **queue_item_id**: execution_harness_root_helper
- **root_task_id**: 20260418-175241-build-openhuman-athena-executionharness-helper-vscode
- **阶段**: build
- **摘要**: ✅ 成本记录成功: req_20260418_175241_6238a556
- **源文档**: /Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/completed/OpenHuman-Athena-ExecutionHarness-根路径Helper与路径漂移收敛-VSCode执行指令.md


## OpenHuman-Athena-ExecutionHarness-完成后Memory回写与交付摘要-VSCode执行指令 (蒸馏于 2026-04-18 17:54:28)

- **queue_item_id**: execution_harness_memory_writeback
- **root_task_id**: 20260418-175427-build-openhuman-athena-executionharness-memory-vscode
- **阶段**: build
- **摘要**: ✅ 成本记录成功: req_20260418_175428_106122d2
- **源文档**: /Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/completed/OpenHuman-Athena-ExecutionHarness-完成后Memory回写与交付摘要-VSCode执行指令.md


## OpenHuman-Athena-WorkflowStability-Runner重启契约与Bootstrap硬化-VSCode执行指令 (蒸馏于 2026-04-19 08:04:19)

- **queue_item_id**: workflow_stability_runner_bootstrap_hardening
- **root_task_id**: 20260419-080418-build-openhuman-athena-workflowstability-runner-bootst
- **阶段**: build
- **摘要**: ✅ 成本记录成功: req_20260419_080418_5a026b97
- **源文档**: /Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/completed/OpenHuman-Athena-WorkflowStability-Runner重启契约与Bootstrap硬化-VSCode执行指令.md


## OpenHuman-Athena-ExecutionHarness-根路径Helper与路径漂移收敛-VSCode执行指令 (蒸馏于 2026-04-19 08:05:04)

- **queue_item_id**: execution_harness_root_helper
- **root_task_id**: 20260419-080504-build-openhuman-athena-executionharness-helper-vscode
- **阶段**: build
- **摘要**: ✅ 成本记录成功: req_20260419_080504_9f096ea7
- **源文档**: /Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/completed/OpenHuman-Athena-ExecutionHarness-根路径Helper与路径漂移收敛-VSCode执行指令.md


## OpenHuman-Athena-ExecutionHarness-完成后Memory回写与交付摘要-VSCode执行指令 (蒸馏于 2026-04-19 08:06:05)

- **queue_item_id**: execution_harness_memory_writeback
- **root_task_id**: 20260419-080605-build-openhuman-athena-executionharness-memory-vscode
- **阶段**: build
- **摘要**: ✅ 成本记录成功: req_20260419_080605_2d911bcc
- **源文档**: /Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/completed/OpenHuman-Athena-ExecutionHarness-完成后Memory回写与交付摘要-VSCode执行指令.md

