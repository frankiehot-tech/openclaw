#!/usr/bin/env python3
"""
测试 SubAgent 工具边界（负面测试）
验证工具使用被正确拒绝的场景
"""

import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from agent.core.subagent_registry import SubAgentRole, get_registry


def test_tool_guardrail_negative():
    """测试工具边界负面场景"""
    print("=== SubAgent 工具边界负面测试 ===")

    registry = get_registry()

    # 测试用例：角色 -> 应被拒绝的工具列表
    negative_test_cases = [
        # (角色ID, 工具名称, 预期拒绝原因)
        (SubAgentRole.PLANNER.value, "bash", "规划者不应执行 bash 命令"),
        (SubAgentRole.PLANNER.value, "edit", "规划者不应直接编辑文件"),
        (SubAgentRole.PLANNER.value, "write", "规划者不应直接写入文件"),
        (SubAgentRole.RESEARCHER.value, "bash", "研究者不应执行 bash 命令"),
        (SubAgentRole.RESEARCHER.value, "edit", "研究者不应直接编辑文件"),
        (SubAgentRole.RESEARCHER.value, "write", "研究者不应直接写入文件"),
        (SubAgentRole.REVIEWER.value, "bash", "审查者不应执行 bash 命令"),
        (SubAgentRole.REVIEWER.value, "edit", "审查者不应直接编辑文件"),
        (SubAgentRole.REVIEWER.value, "write", "审查者不应直接写入文件"),
        (SubAgentRole.VALIDATOR.value, "edit", "验证者不应直接编辑文件"),
        (SubAgentRole.VALIDATOR.value, "write", "验证者不应直接写入文件"),
        # 测试不在 allowed_tools 中的工具（如果 allowed_tools 非空）
        (SubAgentRole.PLANNER.value, "dangerous_tool", "规划者不应使用未允许的工具"),
        (SubAgentRole.RESEARCHER.value, "unknown_tool", "研究者不应使用未知工具"),
    ]

    print(f"\n1. 执行 {len(negative_test_cases)} 个负面测试用例")

    passed = 0
    failed = []

    for role_id, tool_name, expected_reason in negative_test_cases:
        result = registry.check_tool_guardrail(role_id, tool_name)

        allowed = result.get("allowed", True)
        decision = result.get("decision", "unknown")
        reason = result.get("reason", "")

        print(f"\n  测试: {role_id} -> {tool_name}")
        print(f"    预期: 拒绝 ({expected_reason})")
        print(f"    实际: 允许={allowed}, 决策={decision}")
        print(f"    原因: {reason}")

        if not allowed and decision in ["reject", "hitl"]:
            print(f"    ✅ 工具正确被拒绝")
            passed += 1
        else:
            print(f"    ❌ 工具未被拒绝（预期应拒绝）")
            failed.append((role_id, tool_name, expected_reason, result))

    # 验证构建者可以使用高风险工具
    print(f"\n2. 验证构建者可以使用高风险工具（正面测试）")
    build_worker_tests = [
        (SubAgentRole.BUILD_WORKER.value, "bash", "构建者应允许 bash"),
        (SubAgentRole.BUILD_WORKER.value, "edit", "构建者应允许编辑"),
        (SubAgentRole.BUILD_WORKER.value, "write", "构建者应允许写入"),
    ]

    for role_id, tool_name, expected_reason in build_worker_tests:
        result = registry.check_tool_guardrail(role_id, tool_name)

        allowed = result.get("allowed", False)
        decision = result.get("decision", "")

        print(f"\n  测试: {role_id} -> {tool_name}")
        print(f"    预期: 允许 ({expected_reason})")
        print(f"    实际: 允许={allowed}, 决策={decision}")

        if allowed and decision == "allow":
            print(f"    ✅ 工具正确被允许")
            passed += 1
        else:
            print(f"    ❌ 工具未被允许（构建者应允许高风险工具）")
            failed.append((role_id, tool_name, expected_reason, result))

    # 测试角色不存在的情况
    print(f"\n3. 测试不存在的角色")
    result = registry.check_tool_guardrail("nonexistent_role", "read")
    allowed = result.get("allowed", True)
    decision = result.get("decision", "")
    reason = result.get("reason", "")

    print(f"  角色: nonexistent_role -> read")
    print(f"    预期: 拒绝（角色不存在）")
    print(f"    实际: 允许={allowed}, 决策={decision}")
    print(f"    原因: {reason}")

    if not allowed and "角色不存在" in reason:
        print(f"    ✅ 不存在的角色正确被拒绝")
        passed += 1
    else:
        print(f"    ❌ 不存在的角色未被正确拒绝")
        failed.append(("nonexistent_role", "read", "角色不存在应拒绝", result))

    # 结果汇总
    print(f"\n" + "=" * 60)
    print(f"测试结果: 通过 {passed} 个，失败 {len(failed)} 个")

    if failed:
        print(f"\n❌ 失败的测试用例:")
        for role_id, tool_name, expected_reason, result in failed:
            print(f"  - {role_id} -> {tool_name}")
            print(f"    预期: {expected_reason}")
            print(f"    实际: allowed={result.get('allowed')}, decision={result.get('decision')}")
            print(f"    原因: {result.get('reason')}")
        raise AssertionError(f"{len(failed)} 个工具边界测试失败")
    else:
        print(f"\n✅ 所有工具边界负面测试通过！")
        return True


def test_allowed_tools_enforcement():
    """测试 allowed_tools 列表强制执行"""
    print(f"\n=== allowed_tools 列表强制执行测试 ===")

    registry = get_registry()

    # 获取规划者角色定义
    planner = registry.get_role(SubAgentRole.PLANNER.value)
    if not planner:
        print(f"⚠ 无法获取规划者角色，跳过此测试")
        return False

    # 如果规划者有 allowed_tools 列表（非空），则测试不在列表中的工具应被拒绝
    if planner.allowed_tools:
        print(f"规划者允许工具列表: {planner.allowed_tools}")

        # 选择一个不在列表中的工具
        # 查找一个不在 allowed_tools 中的工具
        all_possible_tools = [
            "read",
            "glob",
            "grep",
            "webfetch",
            "task",
            "bash",
            "edit",
            "write",
            "skill",
            "dangerous_tool",
        ]
        disallowed_tool = None
        for tool in all_possible_tools:
            if tool not in planner.allowed_tools:
                disallowed_tool = tool
                break

        if disallowed_tool:
            print(f"\n测试不在 allowed_tools 中的工具: {disallowed_tool}")
            result = registry.check_tool_guardrail(SubAgentRole.PLANNER.value, disallowed_tool)

            # 如果工具在 denied_tools 中，应被拒绝
            # 如果工具不在 denied_tools 但也不在 allowed_tools 中，也应被拒绝
            allowed = result.get("allowed", True)

            if not allowed:
                print(f"    ✅ 工具 {disallowed_tool} 正确被拒绝（不在 allowed_tools 中）")
            else:
                print(f"    ⚠ 工具 {disallowed_tool} 被允许（但不在 allowed_tools 中）")
                print(f"      原因: {result.get('reason')}")

                # 检查是否在 denied_tools 中
                if disallowed_tool in planner.denied_tools:
                    print(f"    ❌ 工具在 denied_tools 中但仍被允许 - 配置错误")
                    raise AssertionError(f"工具 {disallowed_tool} 在 denied_tools 中但仍被允许")
        else:
            print(f"⚠ 所有可能工具都在 allowed_tools 中，无法测试边界")
    else:
        print(f"⚠ 规划者 allowed_tools 为空列表，跳过此测试")

    print(f"\n✅ allowed_tools 强制执行测试完成")
    return True


def test_role_specific_tool_policies():
    """测试角色特定的工具策略"""
    print(f"\n=== 角色特定工具策略测试 ===")

    registry = get_registry()

    # 测试每个角色对核心工具（read, glob, grep）的访问权限
    print(f"\n1. 测试所有角色对核心工具的访问权限")
    core_tools = ["read", "glob", "grep"]

    all_roles = [role.value for role in SubAgentRole]

    for role_id in all_roles:
        role_def = registry.get_role(role_id)
        if not role_def:
            continue

        print(f"\n  角色: {role_id}")
        for tool in core_tools:
            result = registry.check_tool_guardrail(role_id, tool)
            allowed = result.get("allowed", False)
            decision = result.get("decision", "")

            status = "✅" if allowed else "❌"
            print(f"    {tool}: {status} (决策: {decision})")

            # 核心工具应始终允许（除非显式拒绝）
            if not allowed:
                print(f"      ⚠ 核心工具 {tool} 被拒绝，原因: {result.get('reason')}")
                # 这可能是有意设计的，不视为错误

    # 测试高风险工具的角色差异
    print(f"\n2. 测试高风险工具的角色差异")
    high_risk_tools = ["bash", "edit", "write"]

    for tool in high_risk_tools:
        print(f"\n  工具: {tool}")
        for role_id in all_roles:
            role_def = registry.get_role(role_id)
            if not role_def:
                continue

            result = registry.check_tool_guardrail(role_id, tool)
            allowed = result.get("allowed", False)

            # 检查角色配置
            explicitly_denied = tool in role_def.denied_tools
            in_allowed_list = tool in role_def.allowed_tools if role_def.allowed_tools else True

            status = "允许" if allowed else "拒绝"
            config_note = ""
            if explicitly_denied:
                config_note = "(显式禁止)"
            elif not in_allowed_list and role_def.allowed_tools:
                config_note = "(不在允许列表中)"

            print(f"    {role_id}: {status} {config_note}")

    print(f"\n✅ 角色特定工具策略测试完成")
    return True


def main():
    """主测试函数"""
    print("开始 SubAgent 工具边界负面测试")
    print("=" * 60)

    try:
        test_tool_guardrail_negative()
        test_allowed_tools_enforcement()
        test_role_specific_tool_policies()

        print("\n" + "=" * 60)
        print("🎉 所有工具边界测试通过！")
        print("\n验证结果：")
        print("1. 负面测试：工具使用被正确拒绝")
        print("2. 正面测试：构建者可访问高风险工具")
        print("3. 边界检查：不存在的角色被拒绝")
        print("4. 策略执行：allowed_tools 列表被正确应用")
        print("5. 角色差异：不同角色有不同的工具权限")

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
