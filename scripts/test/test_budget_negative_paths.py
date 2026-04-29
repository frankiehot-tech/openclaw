#!/usr/bin/env python3
"""
预算负路径测试

测试预算不足场景下的降级行为：
1. 模拟预算消耗
2. 验证模式自动转换
3. 测试预算检查决策
"""

import shutil
import sys
import tempfile
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 添加 mini-agent 目录到路径（通过符号链接）
mini_agent_dir = project_root / "mini_agent"  # 使用符号链接名称
if str(mini_agent_dir) not in sys.path:
    sys.path.insert(0, str(mini_agent_dir))

# 也添加实际的 mini-agent 目录
mini_agent_actual = project_root / "mini-agent"
if str(mini_agent_actual) not in sys.path:
    sys.path.insert(0, str(mini_agent_actual))

try:
    from mini_agent.agent.core.budget_engine import (
        BudgetCheckRequest,
        BudgetDecision,
        BudgetEngine,
        BudgetMode,
    )
except ImportError:
    # 尝试使用绝对导入
    import sys

    sys.path.insert(0, "/Volumes/1TB-M2/openclaw/mini-agent")
    sys.path.insert(0, "/Volumes/1TB-M2/openclaw")
    from mini_agent.agent.core.budget_engine import (
        BudgetCheckRequest,
        BudgetDecision,
        BudgetEngine,
        BudgetMode,
    )


def test_budget_exhaustion():
    """测试预算耗尽场景"""
    print("=" * 60)
    print("📉 预算耗尽负路径测试")
    print("=" * 60)

    # 创建临时数据库
    temp_dir = tempfile.mkdtemp(prefix="budget_negative_")
    db_path = Path(temp_dir) / "test.db"

    try:
        # 创建预算引擎（使用临时数据库）
        engine = BudgetEngine(db_path=db_path)

        print("\n1. 初始状态:")
        state = engine.get_state()
        print(f"   模式: {state.current_mode.value}")
        print(f"   预算: {state.period_budget:.2f}")
        print(f"   剩余: {state.remaining:.2f}")

        # 测试预算检查（应通过）
        print("\n2. 初始预算检查（应通过）:")
        req = BudgetCheckRequest(
            task_id="test_initial",
            estimated_cost=20.0,
            task_type="general",
            description="初始测试任务",
        )
        result = engine.check_budget(req)
        print(f"   任务: {req.task_id}, 成本: {req.estimated_cost:.2f}")
        print(f"   决定: {result.decision.value}, 允许: {result.allowed}, 原因: {result.reason}")

        # 记录消费（模拟使用预算）
        print("\n3. 模拟预算消费:")

        # 消费到 low 模式边界（剩余 < 30元）
        # 初始预算100元，消费71元 => 剩余29元 (<30元 = low模式)
        consumption_1 = 71.0
        engine.record_consumption(
            task_id="consumption_1",
            cost=consumption_1,
            task_type="general",
            description="消费到low模式边界",
        )

        state = engine.get_state()
        print(f"   消费 {consumption_1:.2f} 后:")
        print(f"   模式: {state.current_mode.value}")
        print(f"   已消费: {state.consumed:.2f}")
        print(f"   剩余: {state.remaining:.2f}")
        print(f"   使用率: {state.utilization:.1%}")

        # 验证模式转换到 low
        assert state.current_mode == BudgetMode.LOW, (
            f"预期 LOW 模式，实际 {state.current_mode.value}"
        )

        # 测试 low 模式下的预算检查
        print("\n4. LOW 模式预算检查:")
        req_low = BudgetCheckRequest(
            task_id="test_low",
            estimated_cost=10.0,  # 超过 low 模式的 max_cost_per_task (5.0)
            task_type="general",
            description="LOW模式测试任务",
        )
        result_low = engine.check_budget(req_low)
        print(f"   任务: {req_low.task_id}, 成本: {req_low.estimated_cost:.2f}")
        print(
            f"   决定: {result_low.decision.value}, 允许: {result_low.allowed}, 原因: {result_low.reason}"
        )

        # 在 low 模式下，非核心任务成本超过5元应该被拒绝或降级
        assert result_low.decision != BudgetDecision.APPROVED, (
            "在LOW模式下，高成本非核心任务应被拒绝"
        )

        # 测试核心任务
        print("\n5. LOW 模式核心任务检查:")
        req_essential = BudgetCheckRequest(
            task_id="test_low_essential",
            estimated_cost=3.0,
            task_type="maintenance",
            is_essential=True,
            description="LOW模式核心任务",
        )
        result_essential = engine.check_budget(req_essential)
        print(f"   任务: {req_essential.task_id}, 成本: {req_essential.estimated_cost:.2f}")
        print(
            f"   决定: {result_essential.decision.value}, 允许: {result_essential.allowed}, 原因: {result_essential.reason}"
        )

        # 核心任务应该被允许（即使成本超过限制？）
        # 根据配置，low_mode: max_cost_per_task=5.0, require_approval_above=2.0
        # 成本3.0 > 2.0，可能需要审批

        # 进一步消费到 critical 模式（剩余 < 10元）
        print("\n6. 模拟进一步消费到 CRITICAL 模式:")
        # 当前剩余29元，再消费20元 => 剩余9元 (<10元 = critical模式)
        consumption_2 = 20.0
        engine.record_consumption(
            task_id="consumption_2",
            cost=consumption_2,
            task_type="general",
            description="消费到critical模式边界",
        )

        state = engine.get_state()
        print(f"   消费 {consumption_2:.2f} 后:")
        print(f"   模式: {state.current_mode.value}")
        print(f"   已消费: {state.consumed:.2f}")
        print(f"   剩余: {state.remaining:.2f}")
        print(f"   使用率: {state.utilization:.1%}")

        # 验证模式转换到 critical
        assert state.current_mode == BudgetMode.CRITICAL, (
            f"预期 CRITICAL 模式，实际 {state.current_mode.value}"
        )

        # 测试 critical 模式下的预算检查
        print("\n7. CRITICAL 模式预算检查:")
        req_critical = BudgetCheckRequest(
            task_id="test_critical",
            estimated_cost=2.0,  # 超过 critical 模式的 max_cost_per_task (1.0)
            task_type="general",  # 非允许的任务类型
            description="CRITICAL模式测试任务",
        )
        result_critical = engine.check_budget(req_critical)
        print(f"   任务: {req_critical.task_id}, 成本: {req_critical.estimated_cost:.2f}")
        print(
            f"   决定: {result_critical.decision.value}, 允许: {result_critical.allowed}, 原因: {result_critical.reason}"
        )

        # 非核心、非允许任务类型的任务应该被拒绝
        assert result_critical.decision != BudgetDecision.APPROVED, (
            "在CRITICAL模式下，非允许任务类型应被拒绝"
        )

        # 测试允许的任务类型
        print("\n8. CRITICAL 模式允许任务类型检查:")
        req_allowed = BudgetCheckRequest(
            task_id="test_critical_allowed",
            estimated_cost=0.5,
            task_type="maintenance",  # 允许的任务类型
            is_essential=True,
            description="CRITICAL模式维护任务",
        )
        result_allowed = engine.check_budget(req_allowed)
        print(f"   任务: {req_allowed.task_id}, 成本: {req_allowed.estimated_cost:.2f}")
        print(
            f"   决定: {result_allowed.decision.value}, 允许: {result_allowed.allowed}, 原因: {result_allowed.reason}"
        )

        # 允许的任务类型应该被允许（如果成本在限制内）

        # 消费到 paused 模式（剩余 ≤ 2元）
        print("\n9. 模拟消费到 PAUSED 模式:")
        # 当前剩余9元，再消费7.5元 => 剩余1.5元 (≤2元 = paused模式)
        consumption_3 = 7.5
        engine.record_consumption(
            task_id="consumption_3",
            cost=consumption_3,
            task_type="general",
            description="消费到paused模式",
        )

        state = engine.get_state()
        print(f"   消费 {consumption_3:.2f} 后:")
        print(f"   模式: {state.current_mode.value}")
        print(f"   已消费: {state.consumed:.2f}")
        print(f"   剩余: {state.remaining:.2f}")
        print(f"   使用率: {state.utilization:.1%}")

        # 验证模式转换到 paused
        assert state.current_mode == BudgetMode.PAUSED, (
            f"预期 PAUSED 模式，实际 {state.current_mode.value}"
        )

        # 测试 paused 模式下的预算检查
        print("\n10. PAUSED 模式预算检查:")
        req_paused = BudgetCheckRequest(
            task_id="test_paused",
            estimated_cost=0.1,
            task_type="general",  # 非系统维护任务
            description="PAUSED模式测试任务",
        )
        result_paused = engine.check_budget(req_paused)
        print(f"   任务: {req_paused.task_id}, 成本: {req_paused.estimated_cost:.2f}")
        print(
            f"   决定: {result_paused.decision.value}, 允许: {result_paused.allowed}, 原因: {result_paused.reason}"
        )

        # 在paused模式下，非系统任务应该被拒绝
        assert result_paused.decision != BudgetDecision.APPROVED, (
            "在PAUSED模式下，非系统任务应被拒绝"
        )

        # 测试系统维护任务
        print("\n11. PAUSED 模式系统任务检查:")
        req_system = BudgetCheckRequest(
            task_id="test_paused_system",
            estimated_cost=0.5,
            task_type="system_maintenance",  # 允许的系统任务类型
            description="PAUSED模式系统维护",
        )
        result_system = engine.check_budget(req_system)
        print(f"   任务: {req_system.task_id}, 成本: {req_system.estimated_cost:.2f}")
        print(
            f"   决定: {result_system.decision.value}, 允许: {result_system.allowed}, 原因: {result_system.reason}"
        )

        # 系统维护任务应该被允许

        print("\n" + "=" * 60)
        print("✅ 所有负路径测试通过！")
        print("=" * 60)

        return True

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        # 清理临时目录
        if Path(temp_dir).exists():
            shutil.rmtree(temp_dir)
        print(f"\n🧹 清理临时目录: {temp_dir}")


def main():
    """主函数"""
    success = test_budget_exhaustion()

    if success:
        print("\n🎉 负路径测试完成，预算引擎降级行为正常！")
        return 0
    else:
        print("\n⚠️  负路径测试失败，请检查预算引擎逻辑")
        return 1


if __name__ == "__main__":
    sys.exit(main())
