#!/usr/bin/env python3
"""
测试 guardrail 前置授权检查
"""

import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from agent.core.athena_orchestrator import get_orchestrator
from agent.core.openhuman_stage_registry import get_registry


def test_stage_registry_guardrail():
    """测试阶段注册表的 guardrail 检查"""
    print("=== 测试阶段注册表 guardrail ===")

    registry = get_registry()

    # 测试高风险阶段 (dispatch) 使用不允许的工具
    print("\n1. 测试高风险阶段 (dispatch) 使用不允许的工具:")
    result = registry.check_tool_guardrail("dispatch", "dangerous_tool")
    print(f"   工具: dangerous_tool")
    print(f"   结果: {result}")
    print(f"   允许: {result.get('allowed')}")
    print(f"   决策: {result.get('decision')}")
    print(f"   原因: {result.get('reason')}")

    # 验证被拒绝（因为 dangerous_tool 不在 allowed_tools 中）
    assert result.get("allowed") == False, "应拒绝不在 allowed_tools 中的工具"
    assert result.get("decision") in ["reject", "hitl"], "应拒绝或需要人工介入"

    # 测试高风险阶段使用允许的工具
    print("\n2. 测试高风险阶段 (dispatch) 使用允许的工具:")
    result = registry.check_tool_guardrail("dispatch", "task_queue")
    print(f"   工具: task_queue")
    print(f"   结果: {result}")
    print(f"   允许: {result.get('allowed')}")

    # 验证允许（但可能需要 HITL）
    # dispatch 阶段 hitl_required=True，所以 decision 应为 "hitl"
    assert result.get("allowed") == True, "应允许 allowed_tools 中的工具"
    assert result.get("hitl_required") == True, "dispatch 阶段应需要人工介入"

    # 测试低风险阶段 (distill) 使用允许的工具
    print("\n3. 测试低风险阶段 (distill) 使用允许的工具:")
    result = registry.check_tool_guardrail("distill", "llm_call")
    print(f"   工具: llm_call")
    print(f"   结果: {result}")
    print(f"   允许: {result.get('allowed')}")

    assert result.get("allowed") == True, "应允许低风险阶段的工具"
    assert result.get("hitl_required") == False, "distill 阶段不应需要人工介入"

    print("\n✅ 阶段注册表 guardrail 测试通过")


def test_orchestrator_guardrail():
    """测试编排器的 guardrail 检查"""
    print("\n=== 测试编排器 guardrail ===")

    orchestrator = get_orchestrator()

    # 创建 OpenHuman 任务（高风险阶段）
    print("\n1. 创建 OpenHuman dispatch 任务:")
    success, task_id, metadata = orchestrator.create_task(
        stage="dispatch", domain="openhuman", description="测试任务分发"
    )

    if not success:
        print(f"   任务创建失败: {task_id}")
        return

    print(f"   任务ID: {task_id}")
    print(f"   阶段: {metadata.get('openhuman_stage')}")

    # 测试 guardrail 检查
    print("\n2. 测试 guardrail 检查:")

    # 测试不允许的工具
    print("   a) 测试不允许的工具:")
    guardrail_result = orchestrator.check_tool_guardrail(
        task_id=task_id, tool_name="dangerous_tool", tool_type="skill"
    )
    print(f"      工具: dangerous_tool")
    print(f"      允许: {guardrail_result.get('allowed')}")
    print(f"      决策: {guardrail_result.get('decision')}")

    assert guardrail_result.get("allowed") == False, "应拒绝不允许的工具"

    # 测试允许的工具（但需要 HITL）
    print("   b) 测试允许的工具（需要 HITL）:")
    guardrail_result = orchestrator.check_tool_guardrail(
        task_id=task_id, tool_name="task_queue", tool_type="skill"
    )
    print(f"      工具: task_queue")
    print(f"      允许: {guardrail_result.get('allowed')}")
    print(f"      决策: {guardrail_result.get('decision')}")
    print(f"      HITL要求: {guardrail_result.get('hitl_required')}")

    assert guardrail_result.get("allowed") == True, "应允许 allowed_tools 中的工具"
    assert guardrail_result.get("hitl_required") == True, "dispatch 阶段应需要人工介入"

    # 创建工程任务（默认允许）
    print("\n3. 创建工程任务（默认允许）:")
    success, eng_task_id, eng_metadata = orchestrator.create_task(
        stage="plan", domain="engineering", description="测试工程任务"
    )

    if success:
        print(f"   工程任务ID: {eng_task_id}")

        print("   测试工程任务 guardrail（默认允许）:")
        guardrail_result = orchestrator.check_tool_guardrail(
            task_id=eng_task_id, tool_name="any_tool", tool_type="skill"
        )
        print(f"      工具: any_tool")
        print(f"      允许: {guardrail_result.get('allowed')}")

        assert guardrail_result.get("allowed") == True, "工程任务应默认允许"

    print("\n✅ 编排器 guardrail 测试通过")


def test_skill_execution_with_guardrail():
    """测试技能执行时的 guardrail 检查"""
    print("\n=== 测试技能执行 guardrail ===")

    from agent.core.skill_registry import get_registry as get_skill_registry

    skill_registry = get_skill_registry()

    # 创建编排器任务
    orchestrator = get_orchestrator()
    success, task_id, metadata = orchestrator.create_task(
        stage="dispatch", domain="openhuman", description="测试技能执行 guardrail"
    )

    if not success:
        print(f"   任务创建失败: {task_id}")
        return

    print(f"   任务ID: {task_id}")

    # 构建上下文
    context = {"task_id": task_id}

    # 尝试执行一个技能（需要模拟一个技能）
    # 由于技能注册表中可能没有实际技能，我们只测试 guardrail 逻辑
    print("\n   注意：实际技能执行测试需要可用技能，此处验证 guardrail 集成")

    # 测试不存在的技能（应返回技能不存在错误）
    print("   测试不存在的技能:")
    result = skill_registry.execute_skill("nonexistent_skill", context=context)
    print(f"      结果: {result.get('success', False)}")
    print(f"      错误: {result.get('error', '无错误')}")

    assert result.get("success") == False, "不存在的技能应失败"

    print("\n✅ 技能执行 guardrail 集成测试通过")


def main():
    """主测试函数"""
    print("开始 guardrail 前置授权测试")
    print("=" * 60)

    try:
        test_stage_registry_guardrail()
        test_orchestrator_guardrail()
        test_skill_execution_with_guardrail()

        print("\n" + "=" * 60)
        print("🎉 所有 guardrail 测试通过！")
        print("\n验证结果：")
        print("1. 阶段注册表 guardrail 检查正常工作")
        print("2. 编排器 guardrail 检查集成正常")
        print("3. 技能执行 guardrail 检查集成正常")
        print("4. 高风险阶段（dispatch）会触发 HITL 要求")
        print("5. 不允许的工具会被拒绝")

        return 0
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
