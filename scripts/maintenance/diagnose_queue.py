#!/usr/bin/env python3
"""
诊断队列状态问题
"""

import json
import sys

sys.path.insert(0, "scripts")

try:
    from athena_ai_plan_runner import (
        compute_route_counts_and_status,
        materialize_route_items,
    )
except ImportError as e:
    print(f"导入失败: {e}")
    sys.exit(1)


def main():
    # 加载路由配置
    with open(".athena-auto-queue.json", encoding="utf-8") as f:
        config = json.load(f)

    routes = config.get("routes", [])
    print(f"找到 {len(routes)} 个路由")

    for route in routes:
        if route.get("queue_id") == "openhuman_aiplan_build_priority_20260328":
            print(f"\n🔍 分析路由: {route.get('name')}")
            print(f"  route_id: {route.get('route_id')}")
            print(f"  queue_id: {route.get('queue_id')}")
            print(f"  manifest_path: {route.get('manifest_path')}")

            # 加载状态文件
            state_file = ".openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"
            try:
                with open(state_file, encoding="utf-8") as f:
                    route_state = json.load(f)
            except Exception as e:
                print(f"❌ 加载状态文件失败: {e}")
                continue

            print("\n📊 状态文件内容:")
            print(f"  queue_status: {route_state.get('queue_status')}")
            print(f"  pause_reason: {route_state.get('pause_reason')}")
            print(
                f"  counts: {json.dumps(route_state.get('counts', {}), ensure_ascii=False, indent=4)}"
            )

            # 检查items数量
            items = route_state.get("items", {})
            print(f"  items数量: {len(items)}")

            # 统计状态
            status_counts = {}
            for _task_id, task in items.items():
                status = task.get("status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1
            print(f"  任务状态分布: {status_counts}")

            # 查找特定任务
            target_id = "-Agent-基因递归演进-engineering-plan-20260413-095313-task-20260413-095313"
            if target_id in items:
                print(f"\n🎯 目标任务 {target_id}:")
                task = items[target_id]
                print(f"  状态: {task.get('status')}")
                print(f"  错误: {task.get('error', '空')}")
                print(f"  依赖: {task.get('depends_on', [])}")
                print(f"  started_at: {task.get('started_at', '空')}")
                print(f"  finished_at: {task.get('finished_at', '空')}")

            # 调用materialize_route_items
            print("\n📋 materialize_route_items 输出:")
            try:
                materialized = materialize_route_items(route, route_state)
                print(f"  返回 {len(materialized)} 个任务")

                # 检查materialized中目标任务的状态
                for item in materialized:
                    if item.get("id") == target_id:
                        print("  目标任务在materialized中:")
                        print(f"    状态: {item.get('status')}")
                        print(f"    depends_on: {item.get('depends_on', [])}")
                        break
                else:
                    print("  ❌ 目标任务不在materialized中!")

                # 调用compute_route_counts_and_status
                counts, status = compute_route_counts_and_status(route, route_state)
                print("\n📈 compute_route_counts_and_status 结果:")
                print(f"  状态: {status}")
                print(f"  counts: {json.dumps(counts, ensure_ascii=False, indent=4)}")

                # 分析为什么状态是manual_hold
                if status == "manual_hold":
                    print("\n🔎 状态为manual_hold的原因分析:")
                    pending_items = [
                        item for item in materialized if item.get("status") == "pending"
                    ]
                    running_items = [
                        item for item in materialized if item.get("status") == "running"
                    ]
                    manual_hold_items = [
                        item for item in materialized if item.get("status") == "manual_hold"
                    ]

                    print(f"  pending_items: {len(pending_items)}")
                    print(f"  running_items: {len(running_items)}")
                    print(f"  manual_hold_items: {len(manual_hold_items)}")

                    if not pending_items and not running_items:
                        print("  → 没有pending或running任务")
                    if manual_hold_items:
                        print(f"  → 有{len(manual_hold_items)}个manual_hold任务")

                    # 检查目标任务状态
                    for item in materialized:
                        if item.get("id") == target_id:
                            print(f"  目标任务实际状态: {item.get('status')}")
                            if item.get("status") != "pending":
                                print(f"  ⚠️  目标任务状态不是'pending'，而是'{item.get('status')}'")

            except Exception as e:
                print(f"❌ 调用函数失败: {e}")
                import traceback

                traceback.print_exc()

    return 0


if __name__ == "__main__":
    sys.exit(main())
