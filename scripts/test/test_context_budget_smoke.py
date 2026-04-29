#!/usr/bin/env python3
"""
上下文预算与约束恢复基础层 - 运行时冒烟测试

验证 Athena 可以读取这套基础层配置或协议。
"""

import sys
from pathlib import Path

import yaml

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_config_loading():
    """测试配置加载"""
    print("1. 测试上下文预算配置加载...")

    config_path = project_root / "mini-agent" / "config" / "context_budget.yaml"
    if not config_path.exists():
        print(f"  ❌ 配置文件不存在: {config_path}")
        return False

    try:
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        print("  ✅ 配置文件加载成功")

        # 检查必需部分
        required_sections = [
            "context_budget",
            "progressive_disclosure",
            "constraint_recovery",
        ]
        for section in required_sections:
            if section in config:
                print(f"  ✅ 配置部分存在: {section}")
            else:
                print(f"  ⚠️  配置部分缺失: {section}")

        return True
    except Exception as e:
        print(f"  ❌ 配置加载失败: {e}")
        return False


def test_module_import():
    """测试模块导入"""
    print("2. 测试模块导入...")

    try:
        from mini_agent.agent.core.context_budget import (
            get_budget_manager,
            get_disclosure_manager,
            get_recovery_manager,
        )

        print("  ✅ 核心模块导入成功")

        # 测试单例获取
        get_budget_manager()
        get_disclosure_manager()
        get_recovery_manager()

        print("  ✅ 管理器单例获取成功")
        return True
    except ImportError as e:
        print(f"  ❌ 模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"  ❌ 管理器初始化失败: {e}")
        return False


def test_budget_operations():
    """测试预算操作"""
    print("3. 测试预算操作...")

    try:
        from mini_agent.agent.core.context_budget import get_budget_manager

        manager = get_budget_manager()

        # 测试获取预算
        budget = manager.get_budget("build")
        print(f"  ✅ 获取build阶段预算: {budget.max_tokens} tokens")

        # 测试使用率检查
        status, overflow, _ = manager.check_utilization("build", 50000)
        print(f"  ✅ 使用率检查: status={status}, overflow={overflow}")

        # 测试可用token计算
        available = manager.get_available_tokens("build", 50000)
        print(f"  ✅ 可用token计算: {available} tokens")

        return True
    except Exception as e:
        print(f"  ❌ 预算操作失败: {e}")
        return False


def test_constraint_recovery():
    """测试约束恢复"""
    print("4. 测试约束恢复...")

    try:
        from mini_agent.agent.core.context_budget import (
            ConstraintSeverity,
            ConstraintType,
            get_recovery_manager,
            handle_constraint_violation,
        )

        manager = get_recovery_manager()

        # 测试创建约束
        constraint = manager.create_constraint(
            constraint_type=ConstraintType.SYNTAX,
            severity=ConstraintSeverity.WARNING,
            message="测试约束消息",
            detection_source="smoke_test",
            violation_context={"file": "test.py", "line": 42},
        )
        print(f"  ✅ 约束创建: {constraint.message}")

        # 测试约束验证
        is_valid, errors = manager.validate_constraint(constraint)
        if is_valid:
            print("  ✅ 约束验证通过")
        else:
            print(f"  ⚠️  约束验证失败: {errors}")

        # 测试恢复动作获取
        actions = manager.get_recovery_actions(constraint)
        print(f"  ✅ 恢复动作获取: {len(actions)} 个动作")

        # 测试约束违规处理
        result = handle_constraint_violation(constraint)
        print(f"  ✅ 约束违规处理: {result['status']}")

        return True
    except Exception as e:
        print(f"  ❌ 约束恢复测试失败: {e}")
        return False


def test_progressive_disclosure():
    """测试渐进式披露"""
    print("5. 测试渐进式披露...")

    try:
        from mini_agent.agent.core.context_budget import (
            ContextLayerType,
            ResetTrigger,
            get_disclosure_manager,
        )

        manager = get_disclosure_manager()

        # 测试层获取
        layer = manager.get_layer("full")
        if layer:
            print(f"  ✅ 上下文层获取: {layer.name.value}")

        # 测试降级路径
        degrade_path = manager.degrade_context(
            ContextLayerType.FULL, ResetTrigger.UTILIZATION_EXCEEDS
        )
        print(f"  ✅ 降级路径计算: {[layer.value for layer in degrade_path]}")

        # 测试重置动作
        reset_actions = manager.get_reset_actions(ResetTrigger.UTILIZATION_EXCEEDS)
        print(f"  ✅ 重置动作获取: {len(reset_actions)} 个动作")

        return True
    except Exception as e:
        print(f"  ❌ 渐进式披露测试失败: {e}")
        return False


def test_athena_integration():
    """测试Athena集成"""
    print("6. 测试Athena集成...")

    try:
        # 测试控制面配置引用
        control_plane_path = project_root / "mini-agent" / "config" / "control_plane.yaml"
        if not control_plane_path.exists():
            print(f"  ⚠️  控制面配置文件不存在: {control_plane_path}")
            return True  # 不是致命错误

        with open(control_plane_path, encoding="utf-8") as f:
            control_plane = yaml.safe_load(f)

        # 检查上下文预算配置引用
        if "project" in control_plane and "context_budget" in control_plane["project"]:
            print("  ✅ 控制面中已配置上下文预算引用")

            config_source = control_plane["project"]["context_budget"].get("config_source")
            if config_source == "context_budget.yaml":
                print(f"  ✅ 配置源正确: {config_source}")
            else:
                print(f"  ⚠️  配置源可能不正确: {config_source}")
        else:
            print("  ⚠️  控制面中未找到上下文预算配置引用")

        # 测试兼容桥映射
        if "compatibility_bridge" in control_plane:
            mapping = control_plane["compatibility_bridge"].get("existing_config_mapping", {})
            if "context_budget.yaml" in mapping:
                print("  ✅ 兼容桥中已配置context_budget.yaml映射")
            else:
                print("  ⚠️  兼容桥中未配置context_budget.yaml映射")

        return True
    except Exception as e:
        print(f"  ❌ Athena集成测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("=" * 60)
    print("上下文预算与约束恢复基础层 - 运行时冒烟测试")
    print("=" * 60)

    tests = [
        test_config_loading,
        test_module_import,
        test_budget_operations,
        test_constraint_recovery,
        test_progressive_disclosure,
        test_athena_integration,
    ]

    results = []
    for test_func in tests:
        try:
            success = test_func()
            results.append((test_func.__name__, success))
        except Exception as e:
            print(f"  ❌ 测试执行异常: {e}")
            results.append((test_func.__name__, False))

        print()

    # 汇总结果
    print("=" * 60)
    print("测试结果汇总:")
    print("=" * 60)

    passed = 0
    failed = 0

    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{test_name}: {status}")

        if success:
            passed += 1
        else:
            failed += 1

    print()
    print(f"总计: {passed} 通过, {failed} 失败")

    # 最终建议
    if failed == 0:
        print("\n🎉 所有测试通过！上下文预算与约束恢复基础层已就绪。")
        print("下一步：在Athena运行时中集成预算检查与约束恢复。")
        return 0
    else:
        print("\n⚠️  部分测试失败，需要检查配置或代码。")
        print("建议：")
        print("  1. 检查配置文件 context_budget.yaml 格式")
        print("  2. 确保模块路径正确")
        print("  3. 验证控制面配置引用")
        return 1


if __name__ == "__main__":
    sys.exit(main())
