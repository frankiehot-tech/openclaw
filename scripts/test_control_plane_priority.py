#!/usr/bin/env python3
"""
控制面配置优先级测试脚本

验证配置优先级顺序：session > local > project > managed
以及合并策略的正确性。

使用方法：
  python3 scripts/test_control_plane_priority.py
"""

import os
import sys
from pathlib import Path

import yaml

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


def load_control_plane_config():
    """加载控制面配置"""
    config_path = project_root / "mini-agent" / "config" / "control_plane.yaml"
    if not config_path.exists():
        print(f"❌ 控制面配置文件不存在: {config_path}")
        return None

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        print(f"✅ 控制面配置加载成功 (版本: {config.get('version', 'unknown')})")
        return config
    except Exception as e:
        print(f"❌ 加载控制面配置失败: {e}")
        return None


def test_priority_order(config):
    """测试优先级顺序配置"""
    print("\n=== 测试优先级顺序 ===")

    priority_section = config.get("configuration_priority", {})
    priority_order = priority_section.get("priority_order", [])

    expected_order = ["session", "local", "project", "managed"]

    if priority_order == expected_order:
        print(f"✅ 优先级顺序正确: {priority_order}")
        return True
    else:
        print(f"❌ 优先级顺序错误:")
        print(f"   期望: {expected_order}")
        print(f"   实际: {priority_order}")
        return False


def test_merge_strategy(config):
    """测试合并策略配置"""
    print("\n=== 测试合并策略 ===")

    priority_section = config.get("configuration_priority", {})
    merge_strategy = priority_section.get("merge_strategy", "")

    if merge_strategy:
        print(f"✅ 合并策略: {merge_strategy}")

        merge_behavior = priority_section.get("merge_behavior", {})
        expected_scopes = ["session", "local", "project", "managed"]

        for scope in expected_scopes:
            behavior = merge_behavior.get(scope, {})
            if behavior:
                action = behavior.get("action", "未知")
                persistence = behavior.get("persistence", "未知")
                print(f"   {scope}: action={action}, persistence={persistence}")
            else:
                print(f"   ⚠️  {scope}: 未定义合并行为")

        return True
    else:
        print("❌ 合并策略未定义")
        return False


def test_resolution_examples(config):
    """测试配置解析示例"""
    print("\n=== 测试配置解析示例 ===")

    examples = config.get("configuration_priority", {}).get("resolution_examples", {})

    if not examples:
        print("⚠️  无配置解析示例")
        return True  # 非致命

    for key, example in examples.items():
        print(f"\n   {key}:")
        for scope in ["managed", "project", "local", "session"]:
            value = example.get(scope, "")
            print(f"     {scope}: {value}")
        final = example.get("final", "")
        print(f"     final: {final} (session最高优先级)")

    print("\n✅ 配置解析示例展示完成")
    return True


def test_local_first_policy(config):
    """测试本地优先策略边界"""
    print("\n=== 测试本地优先策略边界 ===")

    policy = config.get("local_first_policy", {})
    if not policy:
        print("❌ local_first_policy 未定义")
        return False

    never_leaves = policy.get("never_leaves_local", [])
    allowed_remote = policy.get("allowed_remote_access", [])
    explicit_rules = policy.get("explicit_rules", {})

    print(f"✅ never_leaves_local: {len(never_leaves)} 条规则")
    print(f"✅ allowed_remote_access: {len(allowed_remote)} 条规则")
    print(f"✅ explicit_rules: {len(explicit_rules)} 个规则集")

    # 检查关键规则
    if "memory/目录下的所有文件" in str(never_leaves):
        print("✅ 保护 memory/ 目录规则存在")
    else:
        print("⚠️  未明确保护 memory/ 目录")

    if "模型API调用" in str(allowed_remote_access):
        print("✅ 允许模型API调用规则存在")

    return True


def test_compatibility_bridge(config):
    """测试兼容桥映射"""
    print("\n=== 测试兼容桥映射 ===")

    bridge = config.get("compatibility_bridge", {})
    if not bridge:
        print("❌ compatibility_bridge 未定义")
        return False

    mapping = bridge.get("existing_config_mapping", {})
    env_mapping = bridge.get("env_var_mapping", {})

    print(f"✅ 现有配置文件映射: {len(mapping)} 个")
    print(f"✅ 环境变量映射: {len(env_mapping)} 个")

    # 检查关键映射
    required_mappings = [
        "athena_providers.yaml",
        "chat_runtime.json",
        ".athena-auto-queue.json",
        "AGENTS.md",
        "SOUL.md",
        "USER.md",
    ]

    missing = []
    for required in required_mappings:
        if required not in mapping:
            missing.append(required)

    if missing:
        print(f"❌ 缺少关键配置文件映射: {missing}")
        return False
    else:
        print("✅ 所有关键配置文件映射存在")

    return True


def run_all_tests():
    """运行所有测试"""
    print("🔍 控制面配置优先级测试")
    print("=" * 50)

    config = load_control_plane_config()
    if config is None:
        return False

    tests = [
        ("优先级顺序", test_priority_order),
        ("合并策略", test_merge_strategy),
        ("配置解析示例", test_resolution_examples),
        ("本地优先策略", test_local_first_policy),
        ("兼容桥映射", test_compatibility_bridge),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            success = test_func(config)
            if success:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ 测试 '{name}' 异常: {e}")
            failed += 1

    print("\n" + "=" * 50)
    print(f"📊 测试结果: {passed} 通过, {failed} 失败")

    if failed == 0:
        print("🎉 所有测试通过！控制面配置优先级验证成功。")
        return True
    else:
        print("❌ 部分测试失败，请检查控制面配置。")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
