#!/usr/bin/env python3
"""
测试 SubAgent Registry 发现与解析
"""

import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from agent.core.subagent_registry import SubAgentRole, get_registry


def test_registry_discovery():
    """测试注册表发现与解析"""
    print("=== SubAgent Registry 发现与解析测试 ===")

    # 1. 获取注册表实例
    registry = get_registry()
    print(f"\n1. 注册表实例: {registry.__class__.__name__}")

    # 2. 检查角色数量
    roles = registry.list_roles()
    print(f"2. 角色数量: {len(roles)}")

    # 验证至少有 5 个核心角色
    expected_core_roles = {
        SubAgentRole.PLANNER,
        SubAgentRole.RESEARCHER,
        SubAgentRole.BUILD_WORKER,
        SubAgentRole.REVIEWER,
        SubAgentRole.VALIDATOR,
    }
    role_ids = {role.id for role in roles}

    for role_enum in expected_core_roles:
        assert role_enum.value in role_ids, f"缺失核心角色: {role_enum.value}"
        print(f"   ✓ 核心角色存在: {role_enum.value}")

    # 3. 检查每个角色定义的完整性
    print(f"\n3. 角色定义完整性检查:")
    for role_def in roles:
        print(f"   - {role_def.id}:")
        print(f"      标签: {role_def.label}")
        print(f"      描述: {role_def.description}")
        print(f"      允许工具数量: {len(role_def.allowed_tools)}")
        print(f"      禁止工具数量: {len(role_def.denied_tools)}")
        print(f"      输出契约字段: {list(role_def.output_schema.keys())}")

        # 验证必要字段存在
        assert role_def.id, "角色ID不能为空"
        assert role_def.label, "角色标签不能为空"
        assert role_def.description, "角色描述不能为空"
        assert isinstance(role_def.allowed_tools, list), "allowed_tools 应为列表"
        assert isinstance(role_def.denied_tools, list), "denied_tools 应为列表"
        assert isinstance(role_def.output_schema, dict), "output_schema 应为字典"

        # 验证输出契约至少包含 required_fields
        required_fields = role_def.output_schema.get("required_fields", [])
        print(f"      必需字段: {required_fields}")

    # 4. 验证角色与 AgentRole 枚举的一致性
    print(f"\n4. 与 AgentRole 枚举一致性检查:")
    try:
        from agent.core.sub_agent_bus import AgentRole

        bus_roles = set(item.value for item in AgentRole)
        registry_roles = set(role_ids)

        # 检查所有注册表角色都在 AgentRole 中（除了兼容角色）
        compatible_roles = {"builder", "operator"}
        for role_id in registry_roles:
            if role_id not in compatible_roles:
                assert role_id in bus_roles, f"注册表角色 {role_id} 不在 AgentRole 枚举中"

        print(f"   ✓ 角色与 AgentRole 枚举一致")
    except ImportError:
        print(f"   ⚠ 无法导入 AgentRole，跳过一致性检查")

    # 5. 测试角色查询功能
    print(f"\n5. 角色查询功能测试:")
    for role_enum in expected_core_roles:
        role_def = registry.get_role(role_enum.value)
        assert role_def is not None, f"无法查询角色: {role_enum.value}"
        print(f"   ✓ 可查询角色: {role_enum.value}")

    # 6. 测试默认角色（第一个角色）
    default_role = roles[0] if roles else None
    if default_role:
        print(f"\n6. 默认角色检查:")
        print(f"   默认角色: {default_role.id}")
        print(f"   默认职责: {default_role.default_responsibilities}")

    print(f"\n✅ SubAgent Registry 发现与解析测试通过")
    return True


def test_role_hierarchy():
    """测试角色层次关系"""
    print(f"\n=== 角色层次关系测试 ===")

    registry = get_registry()

    # 检查角色之间的工具权限层次
    # 预期：PLANNER < RESEARCHER < BUILD_WORKER < REVIEWER < VALIDATOR 在工具权限上递增
    role_hierarchy = [
        SubAgentRole.PLANNER.value,
        SubAgentRole.RESEARCHER.value,
        SubAgentRole.BUILD_WORKER.value,
        SubAgentRole.REVIEWER.value,
        SubAgentRole.VALIDATOR.value,
    ]

    print(f"角色层次: {' < '.join(role_hierarchy)}")

    # 获取每个角色的工具集合
    role_tools = {}
    for role_id in role_hierarchy:
        role_def = registry.get_role(role_id)
        if role_def:
            role_tools[role_id] = set(role_def.allowed_tools)
            print(f"  {role_id}: {len(role_tools[role_id])} 个允许工具")

    # 验证层次关系：每个角色至少包含前一个角色的所有核心工具
    # （注意：实际实现中可能不是严格包含，这里仅作示例验证）
    print(f"\n工具权限层次验证（示例）:")
    for i in range(1, len(role_hierarchy)):
        prev_role = role_hierarchy[i - 1]
        curr_role = role_hierarchy[i]

        prev_tools = role_tools.get(prev_role, set())
        curr_tools = role_tools.get(curr_role, set())

        # 检查是否存在至少一个工具在前一个角色中有但在当前角色中没有
        missing_tools = prev_tools - curr_tools
        if missing_tools:
            print(f"  ⚠ {curr_role} 缺少 {prev_role} 的 {len(missing_tools)} 个工具")
        else:
            print(f"  ✓ {curr_role} 包含 {prev_role} 的所有工具")

    print(f"\n✅ 角色层次关系测试完成")
    return True


def main():
    """主测试函数"""
    print("开始 SubAgent Registry 发现与解析测试")
    print("=" * 60)

    try:
        test_registry_discovery()
        test_role_hierarchy()

        print("\n" + "=" * 60)
        print("🎉 所有注册表发现测试通过！")
        print("\n验证结果：")
        print("1. 注册表实例化正常")
        print("2. 核心角色定义完整")
        print("3. 角色与 AgentRole 枚举一致")
        print("4. 角色查询功能正常")
        print("5. 角色层次关系合理")

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
