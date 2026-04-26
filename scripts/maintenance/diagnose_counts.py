#!/usr/bin/env python3
"""
诊断counts计算差异
"""

import json
import os
import sys


def main():
    state_file = ".openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"

    print(f"加载状态文件: {state_file}")
    with open(state_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items", {})

    print(f"总任务数: {len(items)}")

    # 方法1: update_queue_status.py直接计数
    counts1 = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "manual_hold": 0}
    status_distribution = {}
    for task_id, task in items.items():
        status = task.get("status", "pending")
        if status in counts1:
            counts1[status] += 1
        else:
            counts1["pending"] += 1
        status_distribution[status] = status_distribution.get(status, 0) + 1

    print("\n=== 方法1: 直接计数 ===")
    print(f"counts: {json.dumps(counts1, ensure_ascii=False)}")
    print(f"状态分布: {json.dumps(status_distribution, ensure_ascii=False)}")

    # 方法2: 使用compute_route_counts_and_status
    sys.path.insert(0, "scripts")
    try:
        from athena_ai_plan_runner import (
            compute_route_counts_and_status,
            materialize_route_items,
        )

        # 加载路由配置
        config_file = ".athena-auto-queue.json"
        if not os.path.exists(config_file):
            print(f"配置文件不存在: {config_file}")
            return

        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        routes = config.get("routes", [])

        for route in routes:
            route_id = route.get("route_id")
            queue_id = route.get("queue_id")

            if queue_id == "openhuman_aiplan_build_priority_20260328":
                print(f"\n=== 方法2: compute_route_counts_and_status ===")
                print(f"路由: {route_id}, 队列: {queue_id}")

                try:
                    materialized = materialize_route_items(route, data)
                    print(f"materialized任务数: {len(materialized)}")

                    counts2, queue_status2 = compute_route_counts_and_status(route, data)
                    print(f"counts: {json.dumps(counts2, ensure_ascii=False)}")
                    print(f"queue_status: {queue_status2}")

                    # 比较差异
                    print(f"\n=== 比较 ===")
                    total1 = sum(counts1.values())
                    total2 = sum(counts2.values())
                    print(f"方法1总计: {total1}")
                    print(f"方法2总计: {total2}")

                    for key in counts1:
                        diff = counts2.get(key, 0) - counts1.get(key, 0)
                        if diff != 0:
                            print(
                                f"{key}: 方法1={counts1[key]}, 方法2={counts2.get(key, 0)}, 差异={diff}"
                            )

                    # 检查materialized中的状态
                    materialized_status_dist = {}
                    for item in materialized:
                        status = item.get("status", "pending")
                        materialized_status_dist[status] = (
                            materialized_status_dist.get(status, 0) + 1
                        )

                    print(
                        f"\nmaterialized状态分布: {json.dumps(materialized_status_dist, ensure_ascii=False)}"
                    )

                    # 检查哪些任务的status不在标准值中
                    non_standard_status = [
                        status for status in status_distribution if status not in counts1
                    ]
                    if non_standard_status:
                        print(f"\n非标准状态值: {non_standard_status}")
                        for status in non_standard_status:
                            print(f"  {status}: {status_distribution[status]}个任务")

                except Exception as e:
                    print(f"计算失败: {e}")
                    import traceback

                    traceback.print_exc()

    except Exception as e:
        print(f"导入失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    sys.exit(main())
