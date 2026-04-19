# 预算化技能执行循环集成指南

## 概述

预算化技能执行循环是 OpenHuman-Fusion-Automaton 的核心组件，实现了基于预算的技能执行控制。它集成了现有的预算引擎、技能注册表和成本估算器，提供了四级生存模式映射到 Athena/Codex/OpenCode 行为差异。

## 核心组件

### 1. 技能成本估算器 (`skill_cost_estimator.py`)

**功能**：
- 基于技能定义、参数和复杂度估算执行成本
- 支持基础成本、复杂度系数、参数权重、外部依赖成本等多维度计算
- 提供置信度和假设条件，支持审计追踪

**配置**：
- 配置文件：`mini-agent/config/skill_costs.yaml`
- 默认成本映射：6个核心技能的基础成本
- 复杂度系数：low(1.0), medium(1.5), high(2.5), critical(4.0)
- 外部成本规则：API调用、Docker容器、人工介入等

**使用示例**：
```python
from mini_agent.agent.core.skill_cost_estimator import get_cost_estimator

cost_estimator = get_cost_estimator()
request = SkillCostRequest(
    skill_id="openhuman-skill-matcher",
    skill_metadata={"category": "matching"},
    parameters={"profile_skills": ["Python"], "required_skills": ["AWS"]}
)
estimate = cost_estimator.estimate_cost(request)
print(f"估算成本: {estimate.total} 元")
```

### 2. 预算化技能执行引擎 (`skill_execution_with_budget.py`)

**功能**：
- 集成预算检查、成本估算和技能执行的完整流程
- 支持四种执行状态：success、budget_approved、pending_approval、insufficient_budget
- 提供强制执行模式（跳过预算检查）

**核心API**：
```python
from mini_agent.agent.core.skill_execution_with_budget import execute_skill

# 正常执行（需要预算检查）
result = execute_skill(
    skill_id="openhuman-skill-matcher",
    parameters={"profile_skills": ["Python"], "required_skills": ["AWS"]},
    context={"task_id": "task_001", "priority": "normal"},
    budget_check_required=True,
    force_execution=False
)

# 检查结果
if result.is_success():
    print("技能执行成功")
elif result.needs_approval():
    print("需要人工审批")
elif result.is_budget_rejected():
    print("预算不足被拒绝")
```

### 3. 四级生存模式映射

**模式到行为映射**：
| 预算模式 | 描述 | 降级级别 | 关键限制 |
|---------|------|----------|----------|
| NORMAL | 正常模式：预算充足，全功能运行 | none | 无限制 |
| LOW | 低预算模式：限制非必要任务，降级处理 | moderate | 单任务成本≤5.0，非必要任务需审批 |
| CRITICAL | 临界模式：仅允许核心任务，需要人工审批 | high | 单任务成本≤1.0，仅允许关键任务类型 |
| PAUSED | 暂停模式：停止所有新任务，仅处理维护任务 | extreme | 仅允许维护任务 |

**获取当前模式行为**：
```python
from mini_agent.agent.core.skill_execution_with_budget import get_current_mode_behavior

behavior = get_current_mode_behavior()
print(f"当前模式: {behavior['description']}")
print(f"允许非必要任务: {behavior['agent_behavior']['allow_non_essential_tasks']}")
```

## 集成点

### 与现有系统的集成

1. **预算引擎**：直接使用现有的 `BudgetEngine`，无需修改
2. **技能注册表**：通过 `SkillRegistry` 获取技能元数据
3. **Athena编排器**：通过 `athena_orchestrator.py` 的 `get_budget_mode_behavior()` 方法获取模式行为
4. **支付审批引擎**：集成 `PaymentContract` 处理需要审批的任务

### 路径依赖说明

所有模块使用相对路径导入，通过 `mini_agent` 符号链接访问 `mini-agent` 目录。关键路径配置：

- 项目根目录：`/Volumes/1TB-M2/openclaw/`
- 符号链接：`mini_agent` → `mini-agent`
- 配置文件：`mini-agent/config/skill_costs.yaml`
- 模块路径：`mini-agent/agent/core/`

### 测试验证

已实现冒烟测试脚本：`scripts/test_budgeted_skill_execution_smoke.py`

**测试场景**：
1. ✅ 预算充足执行技能（验证预算批准流程）
2. ✅ 预算不足拒绝（验证预算检查）
3. ⚠️ 需要审批挂起（需要调整成本估算参数）
4. ✅ 四级生存模式映射检查（验证模式行为映射）
5. ✅ 强制执行（跳过预算检查）

**运行测试**：
```bash
cd /Volumes/1TB-M2/openclaw
python3 scripts/test_budgeted_skill_execution_smoke.py
```

## 使用建议

### 新技能开发

1. 在 `skill_costs.yaml` 中添加技能基础成本
2. 在技能元数据中明确 `category` 和复杂度等级
3. 考虑参数对成本的影响，配置 `parameter_weights`

### 预算模式调整

1. 修改 `budget_config.yaml` 中的阈值配置：
   - `normal_threshold`: 30%（剩余预算低于此进入低模式）
   - `low_threshold`: 10%（进入临界模式）
   - `critical_threshold`: 2%（进入暂停模式）

2. 调整降级规则：
   - `degradation_rules.low_mode.max_cost_per_task`: 5.0
   - `degradation_rules.low_mode.require_approval_above`: 2.0
   - `degradation_rules.critical_mode.max_cost_per_task`: 1.0
   - `degradation_rules.critical_mode.require_approval_above`: 0.5

### 监控和审计

1. 预算检查结果包含完整审计信息：
   - 成本估算明细
   - 预算决策原因
   - 模式变更历史
   
2. 审批请求自动记录到支付审批引擎的审计目录

## 已知限制

1. **成本估算准确性**：外部成本默认较高（人工介入成本50.0），可能需要根据实际场景调整
2. **审批流程**：人工审批界面尚未集成，目前仅记录审批请求
3. **技能执行失败**：预算批准后技能执行失败不影响预算检查逻辑
4. **路径依赖**：依赖 `mini_agent` 符号链接，在非Unix系统上可能需要调整

## 下一步计划

1. 完善审批流程集成，实现人工审批界面
2. 优化成本估算模型，基于实际执行数据校准
3. 添加更多测试场景，包括边界条件和错误处理
4. 集成到 Athena 工作流编排器，实现自动模式切换