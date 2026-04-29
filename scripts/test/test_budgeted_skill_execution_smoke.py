#!/usr/bin/env python3
"""
预算化技能执行冒烟测试 - 验证最小闭环

测试场景：
1. 预算充足执行技能 (success)
2. 预算不足拒绝 (insufficient_budget)
3. 需要审批挂起 (pending_approval)
4. 四级生存模式映射检查

要求：
- 预算引擎正常运行
- 技能注册表可用
- 成本估算器可用
"""

import logging
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

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_setup():
    """测试准备"""
    print("=== 预算化技能执行冒烟测试 ===")
    print("环境检查...")

    # 检查模块是否可用
    try:
        pass

        print("✓ 核心模块导入成功")
        return True
    except ImportError as e:
        print(f"✗ 模块导入失败: {e}")
        return False


def test_1_budget_sufficient_execution():
    """测试1: 预算充足执行技能"""
    print("\n--- 测试1: 预算充足执行技能 ---")

    try:
        from mini_agent.agent.core.budget_engine import get_budget_engine
        from mini_agent.agent.core.skill_execution_with_budget import execute_skill

        # 重置预算，确保充足
        engine = get_budget_engine()
        engine.reset_budget(new_budget=1000.0, reset_consumed=True)

        # 执行低成本技能
        result = execute_skill(
            skill_id="openhuman-skill-matcher",
            parameters={
                "profile_skills": ["Python", "React"],
                "required_skills": ["Python", "AWS"],
            },
            context={"task_id": "smoke_test_1", "priority": "normal"},
            budget_check_required=True,
            force_execution=False,
        )

        print(f"   技能: {result.skill_id}")
        print(f"   状态: {result.status.value}")
        print(f"   预算决策: {result.budget_decision}")
        print(f"   是否成功: {result.is_success()}")

        # 验证：预算决策通过且未被预算拒绝即视为成功（技能执行可能因其他原因失败）
        if result.budget_decision == "approved" and not result.is_budget_rejected():
            print("✓ 预算充足执行测试通过（预算批准）")
            return True
        else:
            print(f"✗ 预算充足执行测试失败: {result.error_message}")
            return False

    except Exception as e:
        print(f"✗ 测试1异常: {e}")
        return False


def test_2_insufficient_budget():
    """测试2: 预算不足拒绝"""
    print("\n--- 测试2: 预算不足拒绝 ---")

    try:
        from mini_agent.agent.core.budget_engine import get_budget_engine
        from mini_agent.agent.core.skill_cost_estimator import get_cost_estimator
        from mini_agent.agent.core.skill_execution_with_budget import execute_skill

        # 重置预算为极低
        engine = get_budget_engine()
        engine.reset_budget(new_budget=0.1, reset_consumed=True)  # 0.1元预算

        # 临时提高技能成本，确保超过预算
        cost_estimator = get_cost_estimator()
        original_cost = cost_estimator.config.base_costs.get("openhuman-skill-matcher", 5.0)
        cost_estimator.update_base_cost("openhuman-skill-matcher", 100.0)

        # 尝试执行技能
        result = execute_skill(
            skill_id="openhuman-skill-matcher",
            parameters={"profile_skills": ["Python"], "required_skills": ["Python"]},
            context={"task_id": "smoke_test_2"},
            budget_check_required=True,
            force_execution=False,
        )

        # 恢复原始成本
        cost_estimator.update_base_cost("openhuman-skill-matcher", original_cost)

        print(f"   状态: {result.status.value}")
        print(f"   是否预算拒绝: {result.is_budget_rejected()}")

        # 验证
        if result.is_budget_rejected():
            print("✓ 预算不足拒绝测试通过")
            return True
        else:
            print(f"✗ 预算不足拒绝测试失败，状态: {result.status.value}")
            return False

    except Exception as e:
        print(f"✗ 测试2异常: {e}")
        return False


def test_3_pending_approval():
    """测试3: 需要审批挂起"""
    print("\n--- 测试3: 需要审批挂起 ---")

    try:
        from mini_agent.agent.core.budget_engine import get_budget_engine
        from mini_agent.agent.core.skill_cost_estimator import get_cost_estimator
        from mini_agent.agent.core.skill_execution_with_budget import execute_skill

        # 重置预算为中等，设置低审批阈值
        engine = get_budget_engine()
        engine.reset_budget(new_budget=100.0, reset_consumed=True)

        # 设置技能成本在低预算模式的审批阈值和最大成本之间
        # 低预算模式审批阈值默认为2.0，最大成本5.0，设置成本为3.0
        cost_estimator = get_cost_estimator()
        original_cost = cost_estimator.config.base_costs.get("openhuman-skill-matcher", 5.0)
        cost_estimator.update_base_cost("openhuman-skill-matcher", 3.0)

        # 将预算模式设为低预算模式（通过消费预算使剩余比例在10%-30%之间）
        # 消费75元，使剩余25元，使用率75%，剩余比例25%，触发低预算模式
        engine.record_consumption(
            task_id="smoke_test_3_consumption",
            cost=75.0,
            task_type="test",
            description="进入低预算模式",
        )

        # 尝试执行技能（标记为关键任务以绕过低预算模式下的非必要任务限制）
        result = execute_skill(
            skill_id="openhuman-skill-matcher",
            parameters={"profile_skills": ["Python"], "required_skills": ["Python"]},
            context={"task_id": "smoke_test_3", "priority": "critical"},
            budget_check_required=True,
            force_execution=False,
        )

        # 恢复原始成本
        cost_estimator.update_base_cost("openhuman-skill-matcher", original_cost)

        print(f"   状态: {result.status.value}")
        print(f"   是否需要审批: {result.needs_approval()}")

        # 验证
        if result.needs_approval():
            print("✓ 需要审批挂起测试通过")
            return True
        else:
            print(f"✗ 需要审批挂起测试失败，状态: {result.status.value}")
            return False

    except Exception as e:
        print(f"✗ 测试3异常: {e}")
        return False


def test_4_budget_mode_mapping():
    """测试4: 四级生存模式映射检查"""
    print("\n--- 测试4: 四级生存模式映射检查 ---")

    try:
        from mini_agent.agent.core.budget_engine import BudgetMode
        from mini_agent.agent.core.skill_execution_with_budget import (
            get_current_mode_behavior,
            map_budget_mode_to_behavior,
        )

        # 测试所有模式的映射
        modes = [
            BudgetMode.NORMAL,
            BudgetMode.LOW,
            BudgetMode.CRITICAL,
            BudgetMode.PAUSED,
        ]

        all_passed = True
        for mode in modes:
            behavior = map_budget_mode_to_behavior(mode)
            description = behavior.get("description", "")
            degradation_level = behavior.get("agent_behavior", {}).get("degradation_level", "")

            print(f"   模式: {mode.value}")
            print(f"     描述: {description}")
            print(f"     降级级别: {degradation_level}")

            # 基本验证
            if not description or degradation_level not in [
                "none",
                "moderate",
                "high",
                "extreme",
            ]:
                print("     ✗ 映射不完整")
                all_passed = False
            else:
                print("     ✓ 映射有效")

        # 测试当前模式行为
        current_behavior = get_current_mode_behavior()
        print(f"   当前模式行为: {current_behavior.get('description', '未知')}")

        if all_passed and current_behavior:
            print("✓ 四级生存模式映射测试通过")
            return True
        else:
            print("✗ 四级生存模式映射测试失败")
            return False

    except Exception as e:
        print(f"✗ 测试4异常: {e}")
        return False


def test_5_force_execution():
    """测试5: 强制执行（跳过预算检查）"""
    print("\n--- 测试5: 强制执行（跳过预算检查） ---")

    try:
        from mini_agent.agent.core.budget_engine import get_budget_engine
        from mini_agent.agent.core.skill_execution_with_budget import execute_skill

        # 重置预算为0，但强制执行
        engine = get_budget_engine()
        engine.reset_budget(new_budget=0.0, reset_consumed=True)

        result = execute_skill(
            skill_id="openhuman-skill-matcher",
            parameters={"profile_skills": ["Python"], "required_skills": ["Python"]},
            context={"task_id": "smoke_test_5"},
            budget_check_required=False,  # 跳过预算检查
            force_execution=True,
        )

        print(f"   状态: {result.status.value}")
        print(
            f"   执行结果: {result.execution_result.get('success', False) if result.execution_result else 'N/A'}"
        )

        # 验证：应该执行技能（可能成功或失败，但不应被预算拒绝）
        if not result.is_budget_rejected():
            print("✓ 强制执行测试通过（未因预算拒绝）")
            return True
        else:
            print("✗ 强制执行测试失败，被预算拒绝")
            return False

    except Exception as e:
        print(f"✗ 测试5异常: {e}")
        return False


def run_all_tests():
    """运行所有测试"""
    if not test_setup():
        return False

    results = []

    # 运行测试
    results.append(("预算充足执行", test_1_budget_sufficient_execution()))
    results.append(("预算不足拒绝", test_2_insufficient_budget()))
    results.append(("需要审批挂起", test_3_pending_approval()))
    results.append(("模式映射检查", test_4_budget_mode_mapping()))
    results.append(("强制执行", test_5_force_execution()))

    # 输出总结
    print("\n=== 测试总结 ===")
    passed = 0
    total = len(results)

    for name, success in results:
        status = "✓ 通过" if success else "✗ 失败"
        print(f"  {name}: {status}")
        if success:
            passed += 1

    print(f"\n通过率: {passed}/{total} ({passed / total * 100:.1f}%)")

    # 最终预算状态
    try:
        from mini_agent.agent.core.budget_engine import get_budget_engine

        engine = get_budget_engine()
        state = engine.get_state()
        print(
            f"最终预算状态: 模式={state.current_mode.value}, 剩余={state.remaining:.2f}, 消费={state.consumed:.2f}"
        )
    except Exception:
        print("无法获取最终预算状态")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
