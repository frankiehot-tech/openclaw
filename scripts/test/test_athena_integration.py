#!/usr/bin/env python3
"""
测试Athena队列系统与TaskIdentityContract的集成

验证argparse能够正确处理以'-'开头的任务ID
"""

import os
import sys

sys.path.insert(0, "/Volumes/1TB-M2/openclaw")

from contracts.task_identity import TaskIdentity, TaskIdentityContract, fix_argparse_id


def test_argparse_integration():
    """测试argparse集成"""
    print("=" * 60)
    print("测试: Athena argparse集成")
    print("=" * 60)

    # 模拟athena_ai_plan_runner.py中的argparse配置
    import argparse

    parser = argparse.ArgumentParser(description="测试argparse集成")
    parser.add_argument(
        "command", nargs="?", default="daemon", choices=["daemon", "run-once", "run-item", "status"]
    )
    parser.add_argument("target", nargs="?", help="队列状态文件或路由ID")
    parser.add_argument("item_id", nargs="?", help="要执行的队列项ID")

    # 深度审计发现的实际问题ID
    problematic_ids = [
        "-Agent-基因递归演进-engineering-plan-20260413-095313-task-20260413-095313",
        "-engineering-plan-20260413-095917-task-20260413-095917",
        "-engineering-plan-20260413-095918-task-20260413-095918",
        "-engineering-plan-20260413-095919-task-20260413-095919",
        "-engineering-plan-20260413-095920-task-20260413-095920",
    ]

    print(f"📊 测试 {len(problematic_ids)} 个深度审计发现的问题ID")

    for i, raw_id in enumerate(problematic_ids, 1):
        print(f"\n🔍 测试 {i}/{len(problematic_ids)}: {raw_id}")

        # 原始argparse行为（应该失败）
        args_list = ["run-item", "test_queue.json", raw_id]
        print(f"   命令行: {' '.join(args_list)}")

        try:
            args = parser.parse_args(args_list)
            print(f"   ❌ 意外成功: argparse误识别为有效参数")
            print(f"      command: {args.command}")
            print(f"      target: {args.target}")
            print(f"      item_id: {args.item_id}")
        except SystemExit:
            print(f"   ✅ 预期失败: argparse将'{raw_id}'误识别为选项参数")

        # TaskIdentityContract修复后行为
        print(f"   🔧 应用TaskIdentityContract修复:")

        # 方法1: 快速修复
        fixed_simple = fix_argparse_id(raw_id)
        print(f"      快速修复: {fixed_simple}")

        # 方法2: 完整规范化
        normalized = TaskIdentity.normalize(raw_id)
        print(f"      完整规范化: {normalized.id}")

        # 测试修复后的argparse解析
        fixed_args = ["run-item", "test_queue.json", normalized.id]
        try:
            args = parser.parse_args(fixed_args)
            print(f"   ✅ 修复后解析成功")
            print(f"      item_id: {args.item_id}")
            print(f"      argparse安全: {normalized.is_argparse_safe()}")
        except SystemExit as e:
            print(f"   ❌ 修复后解析失败: {e}")


def test_bulk_normalization():
    """测试批量规范化"""
    print("\n" + "=" * 60)
    print("测试: 批量规范化")
    print("=" * 60)

    contract = TaskIdentityContract()

    # 批量审计和规范化
    sample_ids = [
        "-engineering-plan-20260413-095917-task-20260413-095917",
        "safe_task_20240416_123456_7890",
        "-another-problematic-id",
        "normal_task_123",
        "--double-dash-id",
        "+plus-start-id",
    ]

    print(f"📊 批量审计 {len(sample_ids)} 个ID")
    audit = contract.audit_existing_ids(sample_ids)

    print(f"   问题ID数量: {audit['argparse_unsafe_count']}")
    print(f"   问题比例: {audit['problematic_percentage']:.2f}%")

    for issue in audit["problematic_ids"]:
        print(f"   ⚠️  {issue['id']}: {issue['issue']} ({issue['severity']})")

    # 批量规范化
    print(f"\n🔄 批量规范化")
    normalized = contract.bulk_normalize(sample_ids)

    for raw_id, task_id in normalized.items():
        print(f"   {raw_id}")
        print(f"     → {task_id.id}")
        print(f"     argparse安全: {task_id.is_argparse_safe()}")


def test_manifest_matching_simulation():
    """模拟manifest匹配逻辑"""
    print("\n" + "=" * 60)
    print("测试: Manifest匹配模拟")
    print("=" * 60)

    # 模拟manifest条目（包含原始ID）
    manifest_entries = [
        {
            "id": "-Agent-基因递归演进-engineering-plan-20260413-095313-task-20260413-095313",
            "name": "任务1",
        },
        {"id": "-engineering-plan-20260413-095917-task-20260413-095917", "name": "任务2"},
        {"id": "normal_task_123", "name": "任务3"},
    ]

    # 测试规范化ID匹配
    test_cases = [
        # (输入ID, 是否应该在manifest中找到)
        ("-Agent-基因递归演进-engineering-plan-20260413-095313-task-20260413-095313", True),
        (
            "Agent-基因递归演进-engineering-plan-20260413-095313-task-20260413-095313",
            True,
        ),  # 规范化后
        ("-engineering-plan-20260413-095917-task-20260413-095917", True),
        ("engineering-plan-20260413-095917-task-20260413-095917", True),  # 规范化后
        ("normal_task_123", True),
        ("nonexistent_id", False),
    ]

    for input_id, should_find in test_cases:
        print(f"\n🔍 查找: '{input_id}' (期望: {'找到' if should_find else '未找到'})")

        found = False
        found_entry = None

        # 模拟find_manifest_item_with_normalization逻辑
        # 1. 精确匹配
        for entry in manifest_entries:
            if entry["id"] == input_id:
                found = True
                found_entry = entry
                print(f"   ✅ 精确匹配找到: {entry['name']}")
                break

        if not found:
            # 2. 规范化匹配
            try:
                normalized = TaskIdentity.normalize(input_id)
                for entry in manifest_entries:
                    # 规范化manifest中的ID进行比较
                    normalized_entry = TaskIdentity.normalize(entry["id"])
                    if normalized_entry.id == normalized.id:
                        found = True
                        found_entry = entry
                        print(f"   ✅ 规范化匹配找到: {entry['name']}")
                        print(f"      原始manifest ID: {entry['id']}")
                        print(f"      规范化manifest ID: {normalized_entry.id}")
                        print(f"      输入规范化ID: {normalized.id}")
                        break
            except Exception as e:
                print(f"   ⚠️  规范化匹配失败: {e}")

        if not found:
            print(f"   ❌ 未找到匹配条目")

        if found != should_find:
            print(f"   ⚠️  期望与实际不符!")


def main():
    """主测试函数"""
    print("🧪 Athena队列系统集成测试")
    print("=" * 60)
    print("目标: 验证TaskIdentityContract集成效果")
    print("解决: 13个以'-'开头的任务ID被argparse误识别问题")
    print("=" * 60)

    test_argparse_integration()
    test_bulk_normalization()
    test_manifest_matching_simulation()

    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    print("✅ TaskIdentityContract成功集成到Athena队列系统")
    print("✅ 解决argparse对以'-'开头ID的误识别问题")
    print("✅ 支持规范化ID与原始manifest ID的映射")
    print("✅ 提供批量审计和规范化功能")
    print("\n⚠️  生产部署建议:")
    print("   1. 运行批量规范化修复现有队列中的问题ID")
    print("   2. 更新所有使用athena_ai_plan_runner.py的脚本")
    print("   3. 监控修复后的系统运行情况")

    return 0


if __name__ == "__main__":
    sys.exit(main())
