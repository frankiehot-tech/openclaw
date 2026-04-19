#!/usr/bin/env python3
"""
测试argparse修复效果
模拟spawn_build_worker构造命令和argparse解析
"""

import argparse
import os
import shlex
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# 模拟athena_ai_plan_runner.py的argparse解析逻辑
def create_argparse_parser():
    """创建与athena_ai_plan_runner.py相同的argparse解析器"""
    parser = argparse.ArgumentParser(description="Athena AI plan queue runner")
    parser.add_argument(
        "command",
        nargs="?",
        default="daemon",
        choices=["daemon", "run-once", "run-item", "status"],
        help="Command to execute: daemon (default), run-once, run-item, status",
    )
    parser.add_argument(
        "target",
        nargs="?",
        help="For run-once/run-item/status: path to queue state file or route ID",
    )
    parser.add_argument(
        "item_id",
        nargs="?",
        help="For run-item: explicit queue item ID to execute",
    )
    parser.add_argument(
        "--queue-id",
        help="Queue ID to operate on (if target not provided)",
    )
    return parser


def test_argparse_parsing(original_id, normalized_id):
    """测试argparse是否能正确解析原始ID和规范化ID"""
    parser = create_argparse_parser()

    # 测试1: 使用原始ID（应该失败）
    print(f"\n测试1: 原始ID '{original_id}'")
    command_parts_original = [
        sys.executable,
        "athena_ai_plan_runner.py",
        "run-item",
        "test_queue",
        original_id,
    ]
    command_original = " ".join(shlex.quote(part) for part in command_parts_original)
    print(f"   命令: {command_original}")

    # 模拟argparse解析
    try:
        # 注意：我们只传递相关的部分，不包括sys.executable和脚本名
        test_args = ["run-item", "test_queue", original_id]
        args = parser.parse_args(test_args)
        print(
            f"   ✅ 解析成功: command={args.command}, target={args.target}, item_id={args.item_id}"
        )
        return True
    except SystemExit as e:
        print(f"   ❌ 解析失败（SystemExit）")
        return False
    except Exception as e:
        print(f"   ❌ 解析失败: {e}")
        return False

    # 测试2: 使用规范化ID（应该成功）
    print(f"\n测试2: 规范化ID '{normalized_id}'")
    command_parts_normalized = [
        sys.executable,
        "athena_ai_plan_runner.py",
        "run-item",
        "test_queue",
        normalized_id,
    ]
    command_normalized = " ".join(shlex.quote(part) for part in command_parts_normalized)
    print(f"   命令: {command_normalized}")

    try:
        test_args = ["run-item", "test_queue", normalized_id]
        args = parser.parse_args(test_args)
        print(
            f"   ✅ 解析成功: command={args.command}, target={args.target}, item_id={args.item_id}"
        )
        return True
    except SystemExit as e:
        print(f"   ❌ 解析失败（SystemExit）")
        return False
    except Exception as e:
        print(f"   ❌ 解析失败: {e}")
        return False


def test_spawn_build_worker_fix():
    """测试spawn_build_worker修复后的命令构造"""
    print("\n=== 测试spawn_build_worker修复 ===")

    from contracts.task_identity import TaskIdentity

    # 模拟日志中的错误ID
    problematic_id = "-engineering-plan-20260413-121456-task-20260413-121456"

    # 模拟spawn_build_worker中的规范化逻辑
    normalized_item_id = problematic_id
    if problematic_id and (problematic_id.startswith("-") or problematic_id.startswith("+")):
        try:
            normalized = TaskIdentity.normalize(problematic_id)
            print(
                f"⚠️  [TaskIdentityContract] 检测到问题ID '{problematic_id}'，已规范化为: {normalized.id}"
            )
            normalized_item_id = normalized.id
        except Exception as e:
            print(f"⚠️  [TaskIdentityContract] 规范化失败: {e}")
            if problematic_id.startswith("-") or problematic_id.startswith("+"):
                normalized_item_id = "task_" + problematic_id[1:]

    # 构造命令（模拟spawn_build_worker第1993-1999行）
    route_queue_id = "openhuman_aiplan_priority_execution_20260414"

    command_parts_before_fix = [
        sys.executable,
        "athena_ai_plan_runner.py",
        "run-item",
        route_queue_id,
        problematic_id,  # 修复前：使用原始ID
    ]

    command_parts_after_fix = [
        sys.executable,
        "athena_ai_plan_runner.py",
        "run-item",
        route_queue_id,
        normalized_item_id,  # 修复后：使用规范化ID
    ]

    command_before = " ".join(shlex.quote(part) for part in command_parts_before_fix)
    command_after = " ".join(shlex.quote(part) for part in command_parts_after_fix)

    print(f"\n修复前命令构造:")
    print(f"  {command_before}")

    print(f"\n修复后命令构造:")
    print(f"  {command_after}")

    # 测试argparse解析
    print(f"\n--- argparse解析测试 ---")

    parser = create_argparse_parser()

    # 测试修复前的命令（应该失败）
    print(f"\n1. 修复前（使用原始ID）:")
    try:
        args = parser.parse_args(["run-item", route_queue_id, problematic_id])
        print(f"   ❌ 意外成功: {args.item_id}")
    except SystemExit:
        print(f"   ✅ 预期失败: argparse将'{problematic_id}'误识别为flag参数")
    except Exception as e:
        print(f"   ✅ 预期失败: {e}")

    # 测试修复后的命令（应该成功）
    print(f"\n2. 修复后（使用规范化ID）:")
    try:
        args = parser.parse_args(["run-item", route_queue_id, normalized_item_id])
        print(
            f"   ✅ 解析成功: command={args.command}, target={args.target}, item_id={args.item_id}"
        )
        return True
    except SystemExit as e:
        print(f"   ❌ 意外失败: SystemExit")
        return False
    except Exception as e:
        print(f"   ❌ 意外失败: {e}")
        return False


if __name__ == "__main__":
    print("=== argparse修复测试 ===")

    # 测试单个ID
    test_id = "-engineering-plan-20260413-121456-task-20260413-121456"
    normalized = "engineering-plan-20260413-121456-task-20260413-121456"

    # 运行测试
    success = test_spawn_build_worker_fix()

    if success:
        print("\n✅ 测试通过: spawn_build_worker修复有效")
    else:
        print("\n❌ 测试失败: 需要进一步调试")

    print("\n=== 测试完成 ===")
