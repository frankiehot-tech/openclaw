#!/usr/bin/env python3
"""
SubAgent Registry 发现与解析测试

验证 registry 能够正确加载、解析角色定义，并能进行工具边界检查和产出契约验证。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mini_agent.agent.core.subagent_registry import get_registry


def test_registry_discovery():
    """测试 registry 发现功能"""
    print("=== SubAgent Registry 发现测试 ===")

    # 获取 registry 实例
    registry = get_registry()

    # 1. 检查角色数量
    roles = registry.list_roles()
    print(f"1. 角色数量: {len(roles)}")
    assert len(roles) >= 5, f"至少需要5个角色，实际: {len(roles)}"

    # 2. 验证必需角色存在
    required_roles = {"planner", "researcher", "build_worker", "reviewer", "validator"}
    role_ids = {role.id for role in roles}
    missing = required_roles - role_ids
    print(f"2. 必需角色检查: {required_roles}")
    print(f"   现有角色: {role_ids}")
    if missing:
        print(f"   ❌ 缺失角色: {missing}")
        return False
    print("   ✅ 所有必需角色存在")

    # 3. 检查每个角色的定义完整性
    for role in roles:
        print(f"3. 角色定义检查: {role.id}")
        assert role.id, "角色ID不能为空"
        assert role.label, "角色标签不能为空"
        assert role.description, "角色描述不能为空"
        # allowed_tools 可以为空（表示允许所有），但必须为列表
        assert isinstance(role.allowed_tools, list), "allowed_tools 必须为列表"
        assert isinstance(role.denied_tools, list), "denied_tools 必须为列表"
        assert isinstance(role.required_output_fields, list), "required_output_fields 必须为列表"
        print(f"   ✅ {role.id}: 定义完整")

    # 4. 测试角色获取
    for role_id in required_roles:
        role_def = registry.get_role(role_id)
        assert role_def is not None, f"角色 {role_id} 未找到"
        print(f"4. 角色获取: {role_id} -> {role_def.label}")

    # 5. 测试工具边界检查（正向）
    print("5. 工具边界检查（正向）")
    test_cases = [
        ("planner", "webfetch", True),  # planner 允许 webfetch
        ("build_worker", "bash", True),  # build_worker 允许 bash
        ("reviewer", "read", True),  # reviewer 允许 read
    ]
    for role_id, tool_name, expected_allowed in test_cases:
        result = registry.check_tool_guardrail(role_id, tool_name)
        allowed = result.get("allowed", False)
        if allowed == expected_allowed:
            print(f"   ✅ {role_id}.{tool_name}: 允许={allowed} (符合预期)")
        else:
            print(f"   ❌ {role_id}.{tool_name}: 允许={allowed} (预期 {expected_allowed})")
            return False

    # 6. 测试产出契约验证（正向）
    print("6. 产出契约验证（正向）")
    test_outputs = [
        ("planner", {"plan": "测试方案", "tasks": ["任务1", "任务2"]}),
        ("build_worker", {"component": "test", "build_status": "success"}),
        ("reviewer", {"review_target": "目标", "review_status": "completed"}),
    ]
    for role_id, output in test_outputs:
        valid, errors = registry.validate_output_schema(role_id, output)
        if valid:
            print(f"   ✅ {role_id}: 产出验证通过")
        else:
            print(f"   ❌ {role_id}: 产出验证失败: {errors}")
            return False

    # 7. 获取角色摘要
    summary = registry.get_role_summary()
    assert summary["total_roles"] == len(roles), "角色总数不匹配"
    assert summary["tool_boundary_enabled"], "工具边界未启用"
    assert summary["output_schema_enabled"], "产出契约未启用"
    print(
        f"7. 角色摘要: {summary['total_roles']} 个角色，工具边界: {summary['tool_boundary_enabled']}, 产出契约: {summary['output_schema_enabled']}"
    )

    print("\n✅ 所有测试通过")
    return True


if __name__ == "__main__":
    success = test_registry_discovery()
    sys.exit(0 if success else 1)
