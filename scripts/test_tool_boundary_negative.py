#!/usr/bin/env python3
"""
工具边界负路径测试

验证高风险工具被正确禁止，以及角色权限边界生效。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mini_agent.agent.core.subagent_registry import get_registry


def test_tool_boundary_negative():
    """测试工具边界负路径"""
    print("=== 工具边界负路径测试 ===")

    registry = get_registry()

    # 1. 测试 planner 不能使用高风险工具
    print("1. 测试 planner 不能使用高风险工具")
    negative_cases = [
        ("planner", "bash", False, "planner 不能执行 bash 命令"),
        ("planner", "edit", False, "planner 不能编辑文件"),
        ("planner", "write", False, "planner 不能写入文件"),
    ]

    all_passed = True
    for role_id, tool_name, expected_allowed, description in negative_cases:
        result = registry.check_tool_guardrail(role_id, tool_name)
        allowed = result.get("allowed", True)
        if allowed == expected_allowed:
            print(f"   ✅ {role_id}.{tool_name}: {description} (符合预期)")
        else:
            print(f"   ❌ {role_id}.{tool_name}: 预期禁止但允许={allowed}")
            print(f"      原因: {result.get('reason', '未知')}")
            all_passed = False

    # 2. 测试 reviewer 不能使用修改类工具
    print("\n2. 测试 reviewer 不能使用修改类工具")
    negative_cases = [
        ("reviewer", "bash", False, "reviewer 不能执行 bash 命令"),
        ("reviewer", "edit", False, "reviewer 不能编辑文件"),
        ("reviewer", "write", False, "reviewer 不能写入文件"),
    ]

    for role_id, tool_name, expected_allowed, description in negative_cases:
        result = registry.check_tool_guardrail(role_id, tool_name)
        allowed = result.get("allowed", True)
        if allowed == expected_allowed:
            print(f"   ✅ {role_id}.{tool_name}: {description} (符合预期)")
        else:
            print(f"   ❌ {role_id}.{tool_name}: 预期禁止但允许={allowed}")
            print(f"      原因: {result.get('reason', '未知')}")
            all_passed = False

    # 3. 测试 validator 不能使用写入类工具
    print("\n3. 测试 validator 不能使用写入类工具")
    negative_cases = [
        ("validator", "edit", False, "validator 不能编辑文件"),
        ("validator", "write", False, "validator 不能写入文件"),
    ]

    for role_id, tool_name, expected_allowed, description in negative_cases:
        result = registry.check_tool_guardrail(role_id, tool_name)
        allowed = result.get("allowed", True)
        if allowed == expected_allowed:
            print(f"   ✅ {role_id}.{tool_name}: {description} (符合预期)")
        else:
            print(f"   ❌ {role_id}.{tool_name}: 预期禁止但允许={allowed}")
            print(f"      原因: {result.get('reason', '未知')}")
            all_passed = False

    # 4. 测试 researcher 不能使用高风险工具
    print("\n4. 测试 researcher 不能使用高风险工具")
    negative_cases = [
        ("researcher", "bash", False, "researcher 不能执行 bash 命令"),
        ("researcher", "edit", False, "researcher 不能编辑文件"),
        ("researcher", "write", False, "researcher 不能写入文件"),
    ]

    for role_id, tool_name, expected_allowed, description in negative_cases:
        result = registry.check_tool_guardrail(role_id, tool_name)
        allowed = result.get("allowed", True)
        if allowed == expected_allowed:
            print(f"   ✅ {role_id}.{tool_name}: {description} (符合预期)")
        else:
            print(f"   ❌ {role_id}.{tool_name}: 预期禁止但允许={allowed}")
            print(f"      原因: {result.get('reason', '未知')}")
            all_passed = False

    # 5. 测试不存在的角色
    print("\n5. 测试不存在的角色")
    result = registry.check_tool_guardrail("nonexistent_role", "read")
    if not result.get("allowed", True):
        print(f"   ✅ 不存在的角色被正确拒绝: {result.get('reason', '未知')}")
    else:
        print(f"   ❌ 不存在的角色未被拒绝")
        all_passed = False

    # 6. 测试策略违反信息完整性
    print("\n6. 测试策略违反信息完整性")
    result = registry.check_tool_guardrail("planner", "bash")
    if "policy_violations" in result:
        violations = result["policy_violations"]
        if violations:
            print(f"   ✅ 策略违反信息存在: {violations}")
        else:
            print(f"   ❌ 策略违反信息为空")
            all_passed = False
    else:
        print(f"   ❌ 缺少 policy_violations 字段")
        all_passed = False

    # 7. 测试角色配置信息返回
    print("\n7. 测试角色配置信息返回")
    result = registry.check_tool_guardrail("planner", "webfetch")
    if "role_config" in result:
        config = result["role_config"]
        if "allowed_tools" in config and "denied_tools" in config:
            print(f"   ✅ 角色配置信息完整: {list(config.keys())}")
        else:
            print(f"   ❌ 角色配置信息缺失字段")
            all_passed = False
    else:
        print(f"   ❌ 缺少 role_config 字段")
        all_passed = False

    if all_passed:
        print("\n✅ 所有负路径测试通过")
    else:
        print("\n❌ 部分测试失败")

    return all_passed


if __name__ == "__main__":
    success = test_tool_boundary_negative()
    sys.exit(0 if success else 1)
