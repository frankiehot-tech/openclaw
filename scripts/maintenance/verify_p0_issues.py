#!/usr/bin/env python3
"""
验证P0优先级问题修复状态

基于深度审计报告，验证以下P0问题的当前状态：
1. 任务ID规范化问题（13个以'-'开头的ID）
2. Manifest数据质量问题（51个重复条目）
3. 进程可靠性问题（120秒启动宽限期）
4. 活跃占位检测延迟（5分钟死进程检测）
"""

import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

BASE_DIR = Path("/Volumes/1TB-M2/openclaw")
QUEUE_DIR = BASE_DIR / ".openclaw" / "plan_queue"
MANIFEST_PATH = QUEUE_DIR / "openhuman_aiplan_priority_execution_20260414.json"
RUNNER_PATH = BASE_DIR / "scripts" / "athena_ai_plan_runner.py"
LIVENESS_PROBE_PATH = BASE_DIR / "scripts" / "queue_liveness_probe.py"


def check_task_identity():
    """检查任务ID规范化问题"""
    print("🔍 检查任务ID规范化问题...")

    problematic_ids = []
    total_ids = 0

    for queue_file in QUEUE_DIR.glob("*.json"):
        if queue_file.name.endswith("_deduplicated.json") or queue_file.name.endswith(
            "_deduplication_report.json"
        ):
            continue

        try:
            with open(queue_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 检查items结构
            items = data.get("items", {})

            if isinstance(items, dict):
                # 字典格式：键是任务ID
                for item_id in items.keys():
                    total_ids += 1
                    if isinstance(item_id, str) and item_id.startswith("-"):
                        problematic_ids.append(
                            {"file": queue_file.name, "id": item_id, "type": "dict_key"}
                        )

            elif isinstance(items, list):
                # 数组格式：items是对象列表，id字段在其中
                for item in items:
                    item_id = item.get("id")
                    if item_id:
                        total_ids += 1
                        if isinstance(item_id, str) and item_id.startswith("-"):
                            problematic_ids.append(
                                {"file": queue_file.name, "id": item_id, "type": "list_item"}
                            )

        except Exception as e:
            print(f"  警告: 无法分析 {queue_file.name}: {e}")

    print(f"   总任务ID数: {total_ids}")
    print(f"   问题ID数: {len(problematic_ids)}")

    if problematic_ids:
        print(f"   问题ID示例 (最多显示10个):")
        for pid in problematic_ids[:10]:
            print(f"     - {pid['file']}: {pid['id'][:80]}...")

    return len(problematic_ids) == 0, len(problematic_ids), total_ids


def check_manifest_quality():
    """检查Manifest数据质量问题"""
    print("\n🔍 检查Manifest数据质量问题...")

    if not MANIFEST_PATH.exists():
        print(f"   ⚠️  Manifest文件不存在: {MANIFEST_PATH}")
        return False, 0, 0

    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        items = data.get("items", [])
        total_items = len(items)

        # 分析重复条目
        id_counter = Counter()
        for item in items:
            item_id = item.get("id", "")
            if item_id:
                id_counter[item_id] += 1

        duplicate_ids = [id for id, count in id_counter.items() if count > 1]
        duplicate_count = sum(count - 1 for count in id_counter.values() if count > 1)

        print(f"   总条目数: {total_items}")
        print(f"   重复ID数: {len(duplicate_ids)}")
        print(f"   重复条目总数: {duplicate_count}")

        if duplicate_ids:
            print(f"   重复ID示例 (最多显示10个):")
            for dup_id in duplicate_ids[:10]:
                print(f"     - {dup_id}: {id_counter[dup_id]} 次出现")

        return len(duplicate_ids) == 0, duplicate_count, total_items

    except Exception as e:
        print(f"  错误: {e}")
        return False, 0, 0


def check_startup_grace_period():
    """检查启动宽限期"""
    print("\n🔍 检查进程启动宽限期...")

    if not RUNNER_PATH.exists():
        print(f"   ⚠️  Runner文件不存在: {RUNNER_PATH}")
        return False, 0

    try:
        with open(RUNNER_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        # 查找STARTUP_GRACE_PERIOD_SECONDS定义
        pattern = r"STARTUP_GRACE_PERIOD_SECONDS\s*=\s*(\d+)"
        match = re.search(pattern, content)

        if match:
            grace_seconds = int(match.group(1))
            print(f"   当前启动宽限期: {grace_seconds} 秒")

            # 检查是否在合理的范围内（建议<=30秒）
            if grace_seconds > 30:
                print(f"   ⚠️  启动宽限期过长: {grace_seconds}秒 > 30秒 (推荐值)")
                return False, grace_seconds
            else:
                print(f"   ✅ 启动宽限期在合理范围内")
                return True, grace_seconds
        else:
            print(f"   ⚠️  未找到STARTUP_GRACE_PERIOD_SECONDS定义")
            return False, 0

    except Exception as e:
        print(f"  错误: {e}")
        return False, 0


def check_heartbeat_threshold():
    """检查心跳阈值"""
    print("\n🔍 检查死进程检测延迟...")

    if not LIVENESS_PROBE_PATH.exists():
        print(f"   ⚠️  活性探针文件不存在: {LIVENESS_PROBE_PATH}")
        return False, 0

    try:
        with open(LIVENESS_PROBE_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        # 查找HEARTBEAT_THRESHOLD_MINUTES定义
        pattern = r"HEARTBEAT_THRESHOLD_MINUTES\s*=\s*(\d+)"
        match = re.search(pattern, content)

        if match:
            threshold_minutes = int(match.group(1))
            threshold_seconds = threshold_minutes * 60
            print(f"   当前心跳阈值: {threshold_minutes} 分钟 ({threshold_seconds} 秒)")

            # 检查是否在合理的范围内（建议<=60秒）
            if threshold_seconds > 60:
                print(f"   ⚠️  检测延迟过长: {threshold_seconds}秒 > 60秒 (推荐值)")
                return False, threshold_seconds
            else:
                print(f"   ✅ 检测延迟在合理范围内")
                return True, threshold_seconds
        else:
            print(f"   ⚠️  未找到HEARTBEAT_THRESHOLD_MINUTES定义")
            return False, 0

    except Exception as e:
        print(f"  错误: {e}")
        return False, 0


def main():
    """主函数"""
    print("=" * 70)
    print("🔧 P0优先级问题验证工具")
    print("=" * 70)

    results = {
        "task_identity": {},
        "manifest_quality": {},
        "startup_grace": {},
        "heartbeat_threshold": {},
    }

    # 1. 检查任务ID规范化
    task_id_ok, problem_count, total_ids = check_task_identity()
    results["task_identity"] = {
        "ok": task_id_ok,
        "problem_count": problem_count,
        "total_ids": total_ids,
    }

    # 2. 检查Manifest数据质量
    manifest_ok, duplicate_count, total_items = check_manifest_quality()
    results["manifest_quality"] = {
        "ok": manifest_ok,
        "duplicate_count": duplicate_count,
        "total_items": total_items,
    }

    # 3. 检查启动宽限期
    grace_ok, grace_seconds = check_startup_grace_period()
    results["startup_grace"] = {"ok": grace_ok, "grace_seconds": grace_seconds}

    # 4. 检查心跳阈值
    heartbeat_ok, threshold_seconds = check_heartbeat_threshold()
    results["heartbeat_threshold"] = {"ok": heartbeat_ok, "threshold_seconds": threshold_seconds}

    # 生成总结报告
    print("\n" + "=" * 70)
    print("📋 验证总结")
    print("=" * 70)

    all_ok = True
    for category, data in results.items():
        category_name = {
            "task_identity": "任务ID规范化",
            "manifest_quality": "Manifest数据质量",
            "startup_grace": "启动宽限期",
            "heartbeat_threshold": "心跳检测延迟",
        }.get(category, category)

        status = "✅ 通过" if data.get("ok", False) else "❌ 未通过"

        # 添加详细信息
        details = []
        if category == "task_identity":
            details.append(f"问题ID: {data['problem_count']}/{data['total_ids']}")
        elif category == "manifest_quality":
            details.append(f"重复条目: {data['duplicate_count']}/{data['total_items']}")
        elif category == "startup_grace":
            details.append(f"当前值: {data['grace_seconds']}秒")
        elif category == "heartbeat_threshold":
            details.append(f"当前值: {data['threshold_seconds']}秒")

        detail_str = f" ({', '.join(details)})" if details else ""
        print(f"{status} {category_name}{detail_str}")

        if not data.get("ok", False):
            all_ok = False

    print("\n" + "=" * 70)
    if all_ok:
        print("🎉 所有P0问题均已修复")
    else:
        print("⚠️  发现未修复的P0问题，需要进一步处理")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
