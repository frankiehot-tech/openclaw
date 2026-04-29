#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py health 或 governance_cli.py queue protect
"""
队列监控脚本 - 每2分钟检查队列状态并拉起失败任务
"""

import json
import os
import sys
from datetime import datetime, timedelta


def check_queue_status():
    """检查队列状态"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 检查队列状态...")

    # 导入队列运行器模块
    sys.path.insert(0, "scripts")
    try:
        from athena_ai_plan_runner import (
            compute_route_counts_and_status,
            materialize_route_items,
        )

        # 加载路由配置
        config_file = ".athena-auto-queue.json"
        if not os.path.exists(config_file):
            print(f"    ⚠️  配置文件不存在: {config_file}")
            return

        with open(config_file, encoding="utf-8") as f:
            config = json.load(f)

        routes = config.get("routes", [])

        for route in routes:
            route_id = route.get("route_id")
            queue_id = route.get("queue_id")
            route.get("manifest_path")

            print(f"  路由: {route_id}, 队列: {queue_id}")

            # 加载状态文件
            state_file = f".openclaw/plan_queue/{queue_id}.json"
            try:
                with open(state_file, encoding="utf-8") as f:
                    state_data = json.load(f)
            except Exception as e:
                print(f"    ⚠️  无法加载状态文件 {state_file}: {e}")
                continue

            # materialize任务 - 使用route对象
            try:
                materialized = materialize_route_items(route, state_data)
            except Exception as e:
                print(f"    ❌ materialize失败: {e}")
                continue

            # 计算状态 - 使用route对象
            try:
                counts, queue_status = compute_route_counts_and_status(route, state_data)
            except Exception as e:
                print(f"    ❌ 计算状态失败: {e}")
                continue

            print(f"    状态: {queue_status}, 统计: {json.dumps(counts, ensure_ascii=False)}")

            # 检查失败任务
            failed_tasks = []
            for task in materialized:
                if task.get("status") == "failed":
                    task_id = task.get("id", "未知")
                    # 从状态文件获取实际的错误信息
                    error = ""
                    if task_id in state_data.get("items", {}):
                        error = state_data["items"][task_id].get("error", "")
                    failed_tasks.append(
                        {"id": task_id, "title": task.get("title", "未知"), "error": error}
                    )

            if failed_tasks:
                print(f"    ⚠️  发现 {len(failed_tasks)} 个失败任务:")
                for task in failed_tasks[:5]:  # 只显示前5个
                    print(f"      - {task['title'][:50]}...")

                # 尝试拉起失败任务（简单重试）
                retry_count = 0
                for task in failed_tasks:
                    task_id = task["id"]
                    # 检查是否应该重试（错误信息包含"等待后续重试"）
                    if "等待后续重试" in task["error"]:
                        print(f"    🔄 尝试拉起任务: {task_id[:40]}...")
                        retry_count += 1

                        # 这里可以添加具体的重试逻辑
                        # 目前先标记为pending
                        if task_id in state_data.get("items", {}):
                            state_data["items"][task_id]["status"] = "pending"
                            state_data["items"][task_id]["error"] = ""
                            state_data["items"][task_id]["finished_at"] = ""
                            state_data["items"][task_id]["started_at"] = ""
                            state_data["updated_at"] = datetime.now().isoformat()

                if retry_count > 0:
                    # 重新计算counts和queue_status（使用与update_queue_status.py相同的逻辑）
                    try:
                        # 直接根据items重新计算counts，避免compute_route_counts_and_status可能的不准确
                        items = state_data.get("items", {})
                        new_counts = {
                            "pending": 0,
                            "running": 0,
                            "completed": 0,
                            "failed": 0,
                            "manual_hold": 0,
                        }
                        for task_id, task in items.items():
                            status = task.get("status", "pending")
                            if status in new_counts:
                                new_counts[status] += 1
                            else:
                                new_counts["pending"] += 1

                        state_data["counts"] = new_counts

                        # 简单的queue_status逻辑
                        pending_items = [
                            task
                            for task_id, task in items.items()
                            if task.get("status") == "pending"
                        ]
                        running_items = [
                            task
                            for task_id, task in items.items()
                            if task.get("status") == "running"
                        ]
                        manual_hold_items = [
                            task
                            for task_id, task in items.items()
                            if task.get("status") == "manual_hold"
                        ]

                        if not pending_items and not running_items:
                            if manual_hold_items:
                                new_queue_status = "manual_hold"
                                state_data["pause_reason"] = "manual_hold"
                            else:
                                new_queue_status = "empty"
                                state_data["pause_reason"] = "empty"
                        elif running_items:
                            new_queue_status = "running"
                            state_data["pause_reason"] = ""
                        else:
                            # 只有pending任务，没有running任务
                            new_queue_status = "running"
                            state_data["pause_reason"] = ""

                        state_data["queue_status"] = new_queue_status
                    except Exception as e:
                        print(f"    ⚠️  重新计算counts失败: {e}")
                        import traceback

                        traceback.print_exc()

                    # 保存更新后的状态文件
                    state_file = f".openclaw/plan_queue/{queue_id}.json"
                    backup = (
                        state_file + f".monitor_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    )

                    # 创建备份
                    import shutil

                    shutil.copy2(state_file, backup)

                    # 保存更新
                    with open(state_file, "w", encoding="utf-8") as f:
                        json.dump(state_data, f, ensure_ascii=False, indent=2)

                    print(f"    ✅ 已重置 {retry_count} 个失败任务为pending")
                    print(
                        f"    📊 新counts: {json.dumps(state_data.get('counts', {}), ensure_ascii=False)}"
                    )

            # 检查长时间运行的任务
            long_running_tasks = []
            for task in materialized:
                if task.get("status") == "running":
                    task_id = task.get("id", "未知")
                    # 从状态文件获取实际的started_at
                    started_at = ""
                    if task_id in state_data.get("items", {}):
                        started_at = state_data["items"][task_id].get("started_at", "")
                    if started_at:
                        try:
                            started_time = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                            if datetime.now(started_time.tzinfo) - started_time > timedelta(
                                hours=2
                            ):
                                long_running_tasks.append(
                                    {
                                        "id": task_id,
                                        "title": task.get("title", "未知"),
                                        "started_at": started_at,
                                    }
                                )
                        except Exception:
                            pass

            if long_running_tasks:
                print(f"    ⚠️  发现 {len(long_running_tasks)} 个长时间运行任务（>2小时）")

            # 记录到日志文件
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "route_id": route_id,
                "queue_status": queue_status,
                "counts": counts,
                "failed_count": len(failed_tasks),
                "long_running_count": len(long_running_tasks),
            }

            log_file = ".openclaw/monitor_log.json"
            logs = []
            if os.path.exists(log_file):
                try:
                    with open(log_file, encoding="utf-8") as f:
                        logs = json.load(f)
                except Exception:
                    logs = []

            logs.append(log_entry)

            # 只保留最近100条记录
            if len(logs) > 100:
                logs = logs[-100:]

            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)

            print("    📊 已记录监控日志")

    except Exception as e:
        print(f"    ❌ 监控失败: {e}")
        import traceback

        traceback.print_exc()


def main():
    """主函数"""
    print("=" * 60)
    print("队列监控脚本启动")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    check_queue_status()

    print("=" * 60)
    print("监控完成")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
