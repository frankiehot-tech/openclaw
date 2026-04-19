#!/usr/bin/env python3
"""
测试SmartOrchestrator集成到athena_orchestrator.py

验证智能路由决策是否正常工作，确保执行器映射正确。
"""

import logging
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_smart_orchestrator_import():
    """测试SmartOrchestrator导入"""
    print("🧪 测试SmartOrchestrator导入...")
    try:
        from workflow.smart_orchestrator import ExecutorType, SmartOrchestrator

        print("✅ SmartOrchestrator导入成功")

        # 创建实例
        orchestrator = SmartOrchestrator()
        print("✅ SmartOrchestrator实例创建成功")

        # 测试ExecutorType枚举
        print("📋 ExecutorType枚举值:")
        for executor in ExecutorType:
            print(f"   - {executor.name}: {executor.value}")

        # 测试from_internal_stage方法
        print("\n🔍 测试阶段到执行器映射:")
        stages = ["think", "plan", "build", "review", "qa", "browse"]
        for stage in stages:
            executor = ExecutorType.from_internal_stage(stage)
            print(f"   - {stage} -> {executor.name} ({executor.value})")

        return orchestrator

    except ImportError as e:
        print(f"❌ SmartOrchestrator导入失败: {e}")
        return None
    except Exception as e:
        print(f"❌ SmartOrchestrator创建失败: {e}")
        return None


def test_route_task(orchestrator):
    """测试智能路由决策"""
    if not orchestrator:
        print("⚠️  无法测试路由，SmartOrchestrator不可用")
        return

    print("\n🧪 测试智能路由决策...")

    # 测试用例
    test_cases = [
        {
            "name": "构建任务（正常负载）",
            "metadata": {
                "entry_stage": "build",
                "domain": "engineering",
                "description": "构建一个新功能模块",
                "resources": {"memory_mb": 512, "cpu_cores": 1},
                "budget_status": "NORMAL",
            },
        },
        {
            "name": "规划任务（高负载）",
            "metadata": {
                "entry_stage": "plan",
                "domain": "engineering",
                "description": "规划系统架构设计",
                "resources": {"memory_mb": 1024, "cpu_cores": 2},
                "budget_status": "WARNING",
            },
        },
        {
            "name": "审查任务（预算临界）",
            "metadata": {
                "entry_stage": "review",
                "domain": "openhuman",
                "description": "审查代码质量",
                "resources": {"memory_mb": 256, "cpu_cores": 1},
                "budget_status": "CRITICAL",
            },
        },
    ]

    for test_case in test_cases:
        print(f"\n📋 测试: {test_case['name']}")
        print(f"   元数据: {test_case['metadata']}")

        try:
            decision = orchestrator.route_task(test_case["metadata"])
            print(f"✅ 路由决策成功")
            print(f"   执行器: {decision.executor_type.name} ({decision.executor_type.value})")
            print(f"   理由: {decision.reasoning}")
            print(f"   置信度: {decision.confidence:.2f}")
            print(f"   预估成本: ${decision.estimated_cost:.4f}")
            print(f"   预估时长: {decision.estimated_duration:.1f}秒")

            if decision.fallback_executor:
                print(f"   备用执行器: {decision.fallback_executor.name}")

        except Exception as e:
            print(f"❌ 路由决策失败: {e}")
            import traceback

            traceback.print_exc()


def test_athena_orchestrator_integration():
    """测试AthenaOrchestrator集成"""
    print("\n🧪 测试AthenaOrchestrator集成...")

    try:
        from mini_agent.agent.core.athena_orchestrator import (
            SMART_ORCHESTRATOR_AVAILABLE,
            AthenaOrchestrator,
            get_orchestrator,
        )

        print(f"✅ AthenaOrchestrator导入成功")
        print(f"   SMART_ORCHESTRATOR_AVAILABLE: {SMART_ORCHESTRATOR_AVAILABLE}")

        # 获取编排器实例
        orchestrator = get_orchestrator()
        print("✅ 编排器实例获取成功")

        # 测试_get_smart_executor方法
        print("\n🔍 测试_get_smart_executor方法...")

        test_stages = ["think", "plan", "build", "review", "qa", "browse"]
        for stage in test_stages:
            try:
                executor = orchestrator._get_smart_executor(
                    stage=stage,
                    domain="engineering",
                    description=f"测试{stage}阶段任务",
                    resources={"memory_mb": 512},
                    budget_status="NORMAL",
                )
                print(f"✅ {stage} -> {executor}")
            except Exception as e:
                print(f"❌ {stage}阶段路由失败: {e}")

        # 测试创建任务（集成测试）
        print("\n🔍 测试完整任务创建流程...")
        try:
            success, task_id, metadata = orchestrator.create_task(
                domain="engineering", stage="build", description="集成测试任务", priority="medium"
            )

            if success:
                print(f"✅ 任务创建成功: task_id={task_id}")
                print(f"   元数据: {metadata}")

                # 检查是否使用了智能路由
                executor = metadata.get("executor", "unknown")
                print(f"   执行器: {executor}")

                if "athena_" in executor or "claude_code" in executor or "opencode" in executor:
                    print("🎯 智能路由激活（检测到标准执行器名称）")
                else:
                    print("⚠️  执行器名称非标准: {executor}")
            else:
                print(f"❌ 任务创建失败")

        except Exception as e:
            print(f"❌ 任务创建测试失败: {e}")
            import traceback

            traceback.print_exc()

    except ImportError as e:
        print(f"❌ AthenaOrchestrator导入失败: {e}")
    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        import traceback

        traceback.print_exc()


def main():
    print("🚀 SmartOrchestrator集成测试")
    print("=" * 60)

    # 测试1: SmartOrchestrator导入和基本功能
    orchestrator = test_smart_orchestrator_import()

    # 测试2: 智能路由决策
    test_route_task(orchestrator)

    # 测试3: AthenaOrchestrator集成
    test_athena_orchestrator_integration()

    print("\n" + "=" * 60)
    print("📊 测试完成总结")
    print("💡 建议:")
    print("   1. 检查执行器映射是否与athena_orchestrator.py中的一致")
    print("   2. 验证智能路由决策是否考虑了系统负载和预算状态")
    print("   3. 确保_create_task方法正确调用_get_smart_executor")
    print("   4. 监控实际任务执行中的执行器选择情况")

    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⏹️ 用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
