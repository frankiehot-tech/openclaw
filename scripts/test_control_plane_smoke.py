#!/usr/bin/env python3
"""
控制面配置优先级与本地优先策略冒烟测试。

验证要求：
1. 配置优先级测试 - 验证 control_plane.yaml 中的优先级顺序
2. local-first 默认边界验证 - 验证本地优先策略规则
"""

import os
import sys
from pathlib import Path

import yaml

RUNTIME_ROOT = Path(os.getenv("ATHENA_RUNTIME_ROOT", "/Volumes/1TB-M2/openclaw"))
CONTROL_PLANE_PATH = RUNTIME_ROOT / "mini-agent" / "config" / "control_plane.yaml"


def load_control_plane():
    """加载控制面配置"""
    if not CONTROL_PLANE_PATH.exists():
        print(f"❌ 控制面配置文件不存在: {CONTROL_PLANE_PATH}")
        return None

    try:
        with open(CONTROL_PLANE_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"❌ 加载控制面配置失败: {e}")
        return None


def test_configuration_priority(config):
    """测试配置优先级顺序"""
    print("🧪 测试配置优先级顺序...")

    priority_section = config.get("configuration_priority", {})
    priority_order = priority_section.get("priority_order", [])

    # 期望的优先级顺序
    expected_order = ["session", "local", "project", "managed"]

    if not priority_order:
        print("❌ 未找到 priority_order 配置")
        return False

    if priority_order != expected_order:
        print(f"❌ 优先级顺序不匹配: {priority_order} != {expected_order}")
        return False

    print(f"✅ 配置优先级顺序正确: {' > '.join(priority_order)}")
    return True


def test_local_first_policy(config):
    """测试本地优先策略边界"""
    print("🧪 测试本地优先策略边界...")

    local_first = config.get("local_first_policy", {})
    if not local_first:
        print("❌ 未找到 local_first_policy 配置")
        return False

    # 检查 never_leaves_local 规则
    never_leaves = local_first.get("never_leaves_local", [])
    if not isinstance(never_leaves, list) or len(never_leaves) == 0:
        print("❌ never_leaves_local 规则未定义或为空")
        return False

    # 检查 allowed_remote_access 规则
    allowed_remote = local_first.get("allowed_remote_access", [])
    if not isinstance(allowed_remote, list) or len(allowed_remote) == 0:
        print("❌ allowed_remote_access 规则未定义或为空")
        return False

    # 检查 explicit_rules 是否存在
    explicit_rules = local_first.get("explicit_rules", {})
    if not explicit_rules:
        print("⚠️  explicit_rules 未定义（可选）")
    else:
        network_access = explicit_rules.get("network_access", {})
        if network_access:
            deny_rules = network_access.get("deny", [])
            allow_rules = network_access.get("allow", [])
            print(f"  网络访问规则: deny={len(deny_rules)}条, allow={len(allow_rules)}条")

    print(
        f"✅ 本地优先策略定义完整: never_leaves_local={len(never_leaves)}条, allowed_remote_access={len(allowed_remote)}条"
    )
    return True


def test_scope_definitions(config):
    """测试作用域定义"""
    print("🧪 测试作用域定义...")

    required_scopes = ["managed", "project", "local", "session"]
    missing_scopes = []

    for scope in required_scopes:
        if scope not in config:
            missing_scopes.append(scope)

    if missing_scopes:
        print(f"❌ 缺少必要的作用域定义: {missing_scopes}")
        return False

    # 检查每个作用域是否有内容
    for scope in required_scopes:
        scope_content = config.get(scope, {})
        if not scope_content:
            print(f"⚠️  作用域 '{scope}' 内容为空")
        else:
            print(f"  作用域 '{scope}': 已定义 ({len(scope_content.keys())}个字段)")

    print("✅ 所有必要作用域均已定义")
    return True


def test_compatibility_bridge(config):
    """测试兼容桥映射"""
    print("🧪 测试兼容桥映射...")

    bridge = config.get("compatibility_bridge", {})
    if not bridge:
        print("⚠️  兼容桥未定义（可选）")
        return True  # 可选

    existing_mapping = bridge.get("existing_config_mapping", {})
    env_var_mapping = bridge.get("env_var_mapping", {})

    if not existing_mapping and not env_var_mapping:
        print("⚠️  兼容桥映射为空")
    else:
        print(f"  现有配置映射: {len(existing_mapping)}项")
        print(f"  环境变量映射: {len(env_var_mapping)}项")

    print("✅ 兼容桥检查完成")
    return True


def main():
    print("🚀 开始控制面配置冒烟测试")
    print(f"配置文件: {CONTROL_PLANE_PATH}")

    config = load_control_plane()
    if config is None:
        return 1

    print(f"版本: {config.get('version', 'unknown')}")

    # 运行所有测试
    tests = [
        test_scope_definitions,
        test_configuration_priority,
        test_local_first_policy,
        test_compatibility_bridge,
    ]

    results = []
    for test_func in tests:
        try:
            result = test_func(config)
            results.append((test_func.__name__, result))
        except Exception as e:
            print(f"❌ 测试 {test_func.__name__} 异常: {e}")
            results.append((test_func.__name__, False))

    # 汇总结果
    print("\n📊 测试结果汇总:")
    passed = 0
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name}: {status}")
        if result:
            passed += 1

    total = len(results)
    print(f"\n🎯 通过率: {passed}/{total}")

    if passed == total:
        print("🌟 所有测试通过！控制面配置有效。")
        return 0
    else:
        print("⚠️  部分测试失败，请检查控制面配置。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
