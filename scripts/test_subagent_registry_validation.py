#!/usr/bin/env python3
"""
SubAgent Registry 验证测试

验证要求：
1. registry 发现或解析测试
2. tool boundary 负路径测试
3. handoff 结构化结果验证
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 添加 mini-agent 目录到路径
mini_agent_dir = project_root / "mini-agent"
sys.path.insert(0, str(mini_agent_dir))

try:
    from agent.core.subagent_registry import get_registry
except ImportError as e:
    print(f"❌ 导入 subagent registry 失败: {e}")
    sys.exit(1)


def test_registry_discovery():
    """测试 registry 发现或解析"""
    print("🧪 测试 registry 发现或解析...")

    registry = get_registry()

    # 1. 验证 registry 实例存在
    assert registry is not None, "Registry 实例应为非空"

    # 2. 验证角色数量
    roles = registry.list_roles()
    assert len(roles) >= 5, f"至少需要5个角色，实际找到 {len(roles)}"

    # 3. 验证必需角色存在
    required_role_ids = {
        "planner",
        "researcher",
        "build_worker",
        "reviewer",
        "validator",
    }
    role_ids = {role.id for role in roles}
    missing_roles = required_role_ids - role_ids
    assert not missing_roles, f"缺少必需角色: {missing_roles}"

    # 4. 验证角色定义完整性
    for role in roles:
        assert role.id, f"角色 {role} ID 不能为空"
        assert role.label, f"角色 {role.id} 标签不能为空"
        assert role.description, f"角色 {role.id} 描述不能为空"
        assert isinstance(role.allowed_tools, list), f"角色 {role.id} allowed_tools 应为列表"
        assert isinstance(role.denied_tools, list), f"角色 {role.id} denied_tools 应为列表"
        assert isinstance(
            role.required_output_fields, list
        ), f"角色 {role.id} required_output_fields 应为列表"

    print("  ✅ registry 发现测试通过")
    return True


def test_tool_boundary_negative_path():
    """测试 tool boundary 负路径测试（拒绝不允许的工具）"""
    print("🧪 测试 tool boundary 负路径...")

    registry = get_registry()

    # 测试用例：角色 + 应被拒绝的工具
    test_cases = [
        ("planner", "bash"),  # planner 禁止 bash
        ("planner", "edit"),  # planner 禁止 edit
        ("planner", "write"),  # planner 禁止 write
        ("reviewer", "bash"),  # reviewer 禁止 bash
        ("reviewer", "edit"),  # reviewer 禁止 edit
        ("reviewer", "write"),  # reviewer 禁止 write
        ("validator", "write"),  # validator 禁止 write
    ]

    all_passed = True
    for role_id, tool_name in test_cases:
        result = registry.check_tool_guardrail(role_id, tool_name)

        if result.get("allowed"):
            print(f"  ❌ {role_id}.{tool_name}: 应被拒绝，但实际允许")
            all_passed = False
        else:
            print(f"  ✅ {role_id}.{tool_name}: 正确拒绝 ({result.get('reason', '无原因')})")

    # 额外测试：不存在的角色
    result = registry.check_tool_guardrail("nonexistent_role", "read")
    assert not result.get("allowed"), "不存在的角色应拒绝工具使用"
    assert "角色不存在" in result.get(
        "reason", ""
    ), f"期望'角色不存在'，实际原因: {result.get('reason')}"
    print(f"  ✅ 不存在的角色: 正确拒绝 ({result.get('reason', '无原因')})")

    if all_passed:
        print("  ✅ tool boundary 负路径测试通过")
    else:
        print("  ❌ tool boundary 负路径测试失败")

    return all_passed


def test_handoff_structured_output_validation():
    """测试 handoff 结构化结果验证"""
    print("🧪 测试 handoff 结构化结果验证...")

    registry = get_registry()

    # 测试用例：有效和无效的输出
    test_cases = [
        # (角色ID, 输出数据, 期望有效)
        (
            "planner",
            {
                "plan": "测试方案",
                "tasks": ["任务1", "任务2"],
                "dependencies": ["任务1"],
                "acceptance_criteria": ["标准1"],
            },
            True,
        ),
        (
            "planner",
            {"tasks": ["任务1"]},  # 缺少 plan 等必需字段
            False,
        ),
        (
            "build_worker",
            {
                "component": "test_component",
                "build_status": "success",
                "artifacts": ["artifact1.py"],
                "tests_passed": True,
            },
            True,
        ),
        (
            "build_worker",
            {"component": "test"},  # 缺少必需字段
            False,
        ),
        (
            "reviewer",
            {
                "review_target": "代码审查",
                "review_status": "completed",
                "findings": ["代码质量良好"],
                "issues_found": 0,
            },
            True,
        ),
        (
            "researcher",
            {
                "research_topic": "AI研究",
                "findings": ["发现1", "发现2"],
                "sources": ["来源1"],
                "recommendations": ["建议1"],
            },
            True,
        ),
        (
            "validator",
            {
                "validation_target": "测试验证",
                "validation_status": "passed",
                "metrics": {"accuracy": 0.95},
                "passed": True,
            },
            True,
        ),
    ]

    all_passed = True
    for role_id, output_data, expected_valid in test_cases:
        valid, errors = registry.validate_output_schema(role_id, output_data)

        if valid == expected_valid:
            status = "✅" if valid else "✅ (预期无效)"
            print(f"  {status} {role_id}: 验证结果符合预期")
            if errors and not valid:
                print(f"     错误: {errors}")
        else:
            print(
                f"  ❌ {role_id}: 期望 {'有效' if expected_valid else '无效'}，实际 {'有效' if valid else '无效'}"
            )
            if errors:
                print(f"     错误: {errors}")
            all_passed = False

    # 测试不存在的角色
    valid, errors = registry.validate_output_schema("nonexistent_role", {})
    assert not valid, "不存在的角色应验证失败"
    assert "角色不存在" in errors[0], f"期望'角色不存在'，实际错误: {errors}"
    print(f"  ✅ 不存在的角色: 正确验证失败 ({errors[0]})")

    if all_passed:
        print("  ✅ handoff 结构化结果验证测试通过")
    else:
        print("  ❌ handoff 结构化结果验证测试失败")

    return all_passed


def test_engineering_stage_mapping():
    """测试 engineering stage 到 subagent role 的映射"""
    print("🧪 测试 engineering stage 映射...")

    # 定义简单的映射（可根据需要扩展）
    stage_to_role = {
        "plan": "planner",
        "build": "build_worker",
        "review": "reviewer",
        "think": "researcher",  # think 可能对应 researcher
        "qa": "validator",  # qa 可能对应 validator
        "browse": "researcher",  # browse 可能对应 researcher
    }

    registry = get_registry()

    # 验证所有映射的角色都存在
    missing_roles = []
    for stage, role_id in stage_to_role.items():
        role = registry.get_role(role_id)
        if not role:
            missing_roles.append((stage, role_id))

    if missing_roles:
        print(f"  ❌ 映射角色不存在: {missing_roles}")
        return False

    print(f"  ✅ engineering stage 映射验证通过: {stage_to_role}")
    return True


def main():
    """主测试函数"""
    print("=" * 60)
    print("SubAgent Registry 验证测试")
    print("=" * 60)

    tests = [
        ("Registry 发现", test_registry_discovery),
        ("Tool Boundary 负路径", test_tool_boundary_negative_path),
        ("Handoff 结构化结果", test_handoff_structured_output_validation),
        ("Engineering Stage 映射", test_engineering_stage_mapping),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"  ❌ 测试异常: {e}")
            import traceback

            traceback.print_exc()
            results.append((test_name, False))

    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总:")
    print("=" * 60)

    all_passed = True
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{status}: {test_name}")
        if not success:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有 SubAgent Registry 验证测试通过！")
        print("\n验证结果：")
        print("1. ✅ Registry 发现与解析功能正常")
        print("2. ✅ Tool boundary 负路径检查正常")
        print("3. ✅ Handoff 结构化结果验证正常")
        print("4. ✅ Engineering stage 映射定义完整")
        return 0
    else:
        print("❌ 部分测试失败，请检查上述问题")
        return 1


if __name__ == "__main__":
    sys.exit(main())
