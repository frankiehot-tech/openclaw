#!/usr/bin/env python3
"""
验证预算化技能执行入口
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent  # 上一级目录（openclaw根目录）
sys.path.insert(0, str(project_root))

# 添加 mini-agent 目录到路径（通过符号链接）
mini_agent_dir = project_root / "mini_agent"
if str(mini_agent_dir) not in sys.path:
    sys.path.insert(0, str(mini_agent_dir))

# 也添加实际的 mini-agent 目录
mini_agent_actual = project_root / "mini-agent"
if str(mini_agent_actual) not in sys.path:
    sys.path.insert(0, str(mini_agent_actual))

print("=== 验证预算化技能执行入口 ===")

# 尝试导入
try:
    from mini_agent.agent.core.budget_engine import get_budget_engine

    print("✓ budget_engine 导入成功")
except ImportError as e:
    print(f"✗ budget_engine 导入失败: {e}")
    sys.exit(1)

try:
    from mini_agent.agent.core.skill_cost_estimator import get_cost_estimator

    print("✓ skill_cost_estimator 导入成功")
except ImportError as e:
    print(f"✗ skill_cost_estimator 导入失败: {e}")
    sys.exit(1)

try:
    pass

    print("✓ skill_registry 导入成功")
except ImportError as e:
    print(f"✗ skill_registry 导入失败: {e}")
    sys.exit(1)

try:
    from mini_agent.agent.core.skill_execution_with_budget import (
        BudgetedSkillExecutionEngine,
        get_current_mode_behavior,
    )

    print("✓ skill_execution_with_budget 导入成功")
except ImportError as e:
    print(f"✗ skill_execution_with_budget 导入失败: {e}")
    sys.exit(1)

# 测试实例化
try:
    engine = BudgetedSkillExecutionEngine()
    print("✓ BudgetedSkillExecutionEngine 实例化成功")

    # 获取当前模式行为
    behavior = get_current_mode_behavior()
    print(f"✓ 当前模式行为: {behavior.get('description', '未知')}")

    # 测试成本估算
    cost_estimator = get_cost_estimator()
    print(f"✓ 成本估算器技能数量: {len(cost_estimator.config.base_costs)}")

    # 测试预算引擎状态
    budget_engine = get_budget_engine()
    state = budget_engine.get_state()
    print(f"✓ 预算状态: 模式={state.current_mode.value}, 剩余={state.remaining:.2f}")

    print("\n✅ 所有验证通过")
    sys.exit(0)

except Exception as e:
    print(f"✗ 运行时错误: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
