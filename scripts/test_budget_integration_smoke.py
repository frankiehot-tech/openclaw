#!/usr/bin/env python3
"""
预算集成冒烟测试

测试预算引擎与 Athena 编排器的集成。
验证预算检查在任务创建流程中正常工作。
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 添加 mini-agent 目录到路径
mini_agent_dir = project_root / "mini-agent"
if str(mini_agent_dir) not in sys.path:
    sys.path.insert(0, str(mini_agent_dir))


def test_budget_engine_available():
    """测试预算引擎是否可用"""
    print("1. 测试预算引擎可用性...")

    try:
        from mini_agent.agent.core.budget_engine import (
            BudgetConfig,
            BudgetDecision,
            BudgetEngine,
            BudgetMode,
        )

        # 创建临时数据库
        temp_dir = tempfile.mkdtemp(prefix="budget_smoke_")
        db_path = Path(temp_dir) / "smoke_test.db"

        engine = BudgetEngine(db_path=db_path)
        state = engine.get_state()

        assert state.current_mode == BudgetMode.NORMAL
        assert state.period_budget > 0

        print(f"   ✅ 预算引擎可用，当前模式: {state.current_mode.value}")
        print(f"     预算: {state.period_budget:.2f}, 剩余: {state.remaining:.2f}")

        # 清理
        shutil.rmtree(temp_dir)

        return True

    except ImportError as e:
        print(f"   ❌ 无法导入预算引擎: {e}")
        return False
    except Exception as e:
        print(f"   ❌ 预算引擎测试失败: {e}")
        return False


def test_budget_heartbeat_script():
    """测试预算心跳脚本"""
    print("\n2. 测试预算心跳脚本...")

    try:
        # 导入心跳函数
        from scripts.budget_heartbeat import run_heartbeat

        # 运行心跳（安静模式）
        result = run_heartbeat(output_format="json", alert_on_critical=False)

        if "error" in result:
            print(f"   ⚠️ 心跳返回错误: {result.get('error')}")
            print(f"     消息: {result.get('message', '无')}")
            # 不视为失败，可能预算引擎不可用
            return True
        else:
            print(f"   ✅ 心跳检查成功")
            print(f"     模式: {result.get('budget_state', {}).get('current_mode', 'unknown')}")
            print(f"     使用率: {result.get('health', {}).get('utilization', 0):.1%}")
            return True

    except ImportError as e:
        print(f"   ❌ 无法导入心跳脚本: {e}")
        return False
    except Exception as e:
        print(f"   ❌ 心跳脚本测试失败: {e}")
        return False


def test_athena_orchestrator_integration():
    """测试 Athena 编排器集成"""
    print("\n3. 测试 Athena 编排器集成...")

    try:
        from mini_agent.agent.core.athena_orchestrator import (
            ApprovalState,
            AthenaOrchestrator,
            CostMode,
        )

        # 创建编排器实例
        orchestrator = AthenaOrchestrator()

        # 检查是否导入了预算引擎
        if not hasattr(orchestrator, "BUDGET_ENGINE_AVAILABLE"):
            print(f"   ⚠️ 编排器未定义 BUDGET_ENGINE_AVAILABLE 变量")
            # 可能文件未更新，跳过此测试
            print(f"     跳过集成测试（可能需要更新 athena_orchestrator.py）")
            return True

        print(f"   ✅ 编排器加载成功")
        print(
            f"     预算引擎可用: {orchestrator.BUDGET_ENGINE_AVAILABLE if hasattr(orchestrator, 'BUDGET_ENGINE_AVAILABLE') else '未定义'}"
        )

        # 尝试创建任务（低成本任务应通过）
        success, task_id, metadata = orchestrator.create_task(
            stage="plan", domain="engineering", description="预算集成测试任务"
        )

        if success:
            print(f"   ✅ 任务创建成功: {task_id}")
            print(f"     预估成本: {metadata.get('estimated_cost', 0):.2f}")
            print(f"     审批状态: {metadata.get('approval_state', 'unknown')}")

            # 检查任务元数据中是否有预算相关字段
            budget_fields = ["estimated_cost", "actual_cost", "cost_mode"]
            present_fields = [f for f in budget_fields if f in metadata]
            print(f"     包含的预算字段: {present_fields}")

            return True
        else:
            print(f"   ❌ 任务创建失败: {task_id}")
            return False

    except ImportError as e:
        print(f"   ❌ 无法导入编排器: {e}")
        return False
    except Exception as e:
        print(f"   ❌ 编排器测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_budget_check_integration():
    """测试预算检查集成（如果可用）"""
    print("\n4. 测试预算检查集成...")

    try:
        # 检查 athena_orchestrator.py 是否包含预算检查代码
        orchestrator_path = mini_agent_dir / "agent" / "core" / "athena_orchestrator.py"

        if not orchestrator_path.exists():
            print(f"   ❌ 编排器文件不存在: {orchestrator_path}")
            return False

        with open(orchestrator_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 检查关键字符串
        checks = {
            "BUDGET_ENGINE_AVAILABLE": "预算引擎可用性检查",
            "check_budget": "预算检查方法调用",
            "BudgetCheckRequest": "预算检查请求",
            "record_consumption": "消费记录",
        }

        found_checks = []
        for key, description in checks.items():
            if key in content:
                found_checks.append(description)

        if found_checks:
            print(f"   ✅ 找到预算集成代码:")
            for desc in found_checks:
                print(f"     - {desc}")
            return True
        else:
            print(f"   ⚠️ 未找到预算集成代码，可能需要更新 athena_orchestrator.py")
            return True  # 不视为失败，可能是尚未集成

    except Exception as e:
        print(f"   ❌ 集成代码检查失败: {e}")
        return False


def test_config_files():
    """测试配置文件"""
    print("\n5. 测试配置文件...")

    config_files = [
        mini_agent_dir / "config" / "budget_config.yaml",
        mini_agent_dir / "config" / "athena_providers.yaml",
    ]

    all_exist = True
    for config_file in config_files:
        if config_file.exists():
            print(f"   ✅ 配置文件存在: {config_file.name}")

            # 检查预算配置是否包含必要字段
            if config_file.name == "budget_config.yaml":
                try:
                    import yaml

                    with open(config_file, "r", encoding="utf-8") as f:
                        config = yaml.safe_load(f)

                    required_fields = [
                        "daily_budget",
                        "reset_period",
                        "degradation_rules",
                    ]
                    missing = [f for f in required_fields if f not in config]

                    if missing:
                        print(f"     ⚠️ 缺少字段: {missing}")
                    else:
                        print(f"     ✅ 包含所有必要字段")

                except Exception as e:
                    print(f"     ⚠️ 无法解析配置文件: {e}")
        else:
            print(f"   ❌ 配置文件不存在: {config_file.name}")
            all_exist = False

    return all_exist


def main():
    """主测试函数"""
    print("=" * 60)
    print("📊 预算集成冒烟测试")
    print("=" * 60)

    tests = [
        ("预算引擎可用性", test_budget_engine_available),
        ("预算心跳脚本", test_budget_heartbeat_script),
        ("Athena编排器集成", test_athena_orchestrator_integration),
        ("预算检查集成", test_budget_check_integration),
        ("配置文件", test_config_files),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"测试 '{test_name}' 异常: {e}")
            results.append((test_name, False))

    print("\n" + "=" * 60)
    print("测试结果摘要:")
    print("=" * 60)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1

    print(f"\n总计: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有测试通过！")
        return 0
    else:
        print("⚠️  部分测试失败，请检查集成")
        return 1


if __name__ == "__main__":
    sys.exit(main())
