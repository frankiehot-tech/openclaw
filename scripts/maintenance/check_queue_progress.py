#!/usr/bin/env python3
"""
队列进度检查脚本 - 检查完成度，如果达到90%以上则准备分析报告，否则记录当前进度
"""

import json
import os
import sys
from datetime import datetime


def check_queue_progress():
    """检查队列进度并生成报告"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 检查队列进度...")

    # 导入队列运行器模块
    sys.path.insert(0, "scripts")
    try:
        from athena_ai_plan_runner import (
            compute_route_counts_and_status,
            materialize_route_items,
        )
    except ImportError as e:
        print(f"❌ 无法导入模块: {e}")
        return

    # 加载路由配置
    config_file = ".athena-auto-queue.json"
    if not os.path.exists(config_file):
        print(f"⚠️ 配置文件不存在: {config_file}")
        return

    with open(config_file, encoding="utf-8") as f:
        config = json.load(f)

    routes = config.get("routes", [])

    report_data = []
    all_queues_above_90 = True

    for route in routes:
        route_id = route.get("route_id")
        queue_id = route.get("queue_id")
        route_name = route.get("name", route_id)

        print(f"  检查队列: {route_name} ({route_id})")

        # 加载状态文件
        state_file = f".openclaw/plan_queue/{queue_id}.json"
        try:
            with open(state_file, encoding="utf-8") as f:
                state_data = json.load(f)
        except Exception as e:
            print(f"    ⚠️ 无法加载状态文件 {state_file}: {e}")
            continue

        # materialize任务
        try:
            materialized = materialize_route_items(route, state_data)
        except Exception as e:
            print(f"    ❌ materialize失败: {e}")
            continue

        # 计算状态
        try:
            counts, queue_status = compute_route_counts_and_status(route, state_data)
        except Exception as e:
            print(f"    ❌ 计算状态失败: {e}")
            continue

        # 计算完成度
        total = sum(counts.values())
        completed = counts.get("completed", 0)
        failed = counts.get("failed", 0)

        if total > 0:
            completion_rate = (completed / total) * 100
        else:
            completion_rate = 0.0

        # 收集失败任务信息
        failed_tasks = []
        for task in materialized:
            if task.get("status") == "failed":
                task_id = task.get("id", "未知")
                error = ""
                if task_id in state_data.get("items", {}):
                    error = state_data["items"][task_id].get("error", "")
                failed_tasks.append(
                    {
                        "id": task_id,
                        "title": task.get("title", "未知"),
                        "error": error[:100],  # 截断错误信息
                    }
                )

        queue_info = {
            "route_id": route_id,
            "queue_id": queue_id,
            "name": route_name,
            "status": queue_status,
            "counts": counts,
            "total_tasks": total,
            "completed": completed,
            "failed": failed,
            "completion_rate": round(completion_rate, 2),
            "failed_tasks": failed_tasks,
            "above_90": completion_rate >= 90.0,
        }

        report_data.append(queue_info)

        print(f"    完成度: {completion_rate:.2f}% (已完成 {completed}/{total})")

        if completion_rate >= 90.0:
            print("    ✅ 完成度超过90%，准备分析报告")
        else:
            print("    📊 完成度未达90%，记录当前进度")
            all_queues_above_90 = False

    # 生成报告
    generate_report(report_data, all_queues_above_90)

    # 记录进度
    log_progress(report_data)

    return report_data


def generate_report(report_data, all_above_90):
    """生成分析报告"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"logs/queue_analysis_report_{timestamp}.md"

    # 确保logs目录存在
    os.makedirs("logs", exist_ok=True)

    with open(report_file, "w", encoding="utf-8") as f:
        f.write("# 队列分析报告\n\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # 总体统计
        total_queues = len(report_data)
        above_90_count = sum(1 for q in report_data if q["above_90"])
        total_tasks = sum(q["total_tasks"] for q in report_data)
        total_completed = sum(q["completed"] for q in report_data)
        total_failed = sum(q["failed"] for q in report_data)

        overall_rate = (total_completed / total_tasks * 100) if total_tasks > 0 else 0

        f.write("## 总体概览\n\n")
        f.write(f"- **队列数量**: {total_queues}\n")
        f.write(f"- **完成度≥90%的队列**: {above_90_count}/{total_queues}\n")
        f.write(f"- **总任务数**: {total_tasks}\n")
        f.write(f"- **已完成任务**: {total_completed}\n")
        f.write(f"- **失败任务**: {total_failed}\n")
        f.write(f"- **总体完成度**: {overall_rate:.2f}%\n")
        f.write(
            f"- **总体状态**: {'所有队列完成度均≥90%' if all_above_90 else '有队列未达90%完成度'}\n\n"
        )

        # 各队列详情
        f.write("## 队列详情\n\n")
        for queue in report_data:
            f.write(f"### {queue['name']} ({queue['route_id']})\n\n")
            f.write(f"- **队列ID**: {queue['queue_id']}\n")
            f.write(f"- **状态**: {queue['status']}\n")
            f.write(
                f"- **完成度**: {queue['completion_rate']}% ({queue['completed']}/{queue['total_tasks']})\n"
            )
            f.write(f"- **任务统计**: {json.dumps(queue['counts'], ensure_ascii=False)}\n")

            if queue["failed_tasks"]:
                f.write(f"- **失败任务**: {len(queue['failed_tasks'])}个\n")
                for i, task in enumerate(queue["failed_tasks"][:5], 1):  # 最多显示5个
                    f.write(f"  {i}. {task['title'][:80]}...\n")
                    if task["error"]:
                        f.write(f"     错误: {task['error']}\n")
            else:
                f.write("- **失败任务**: 无\n")

            f.write("\n")

        # 建议
        f.write("## 建议\n\n")
        if all_above_90:
            f.write("1. ✅ 所有队列完成度均超过90%，可以考虑进行最终验证和归档。\n")
            f.write("2. 📊 分析失败任务原因，考虑是否需要进行重试或忽略。\n")
            f.write("3. 🗂️  将已完成队列移动到归档目录。\n")
        else:
            f.write("1. ⚠️  有队列未达到90%完成度，需要继续监控或人工干预。\n")
            f.write("2. 🔄 重点关注失败任务，分析失败原因。\n")
            f.write("3. 📈 监控队列进度，确保任务正常推进。\n")

    print(f"📄 分析报告已生成: {report_file}")
    return report_file


def log_progress(report_data):
    """记录进度日志"""
    timestamp = datetime.now().isoformat()
    log_file = "logs/queue_progress_log.jsonl"

    # 确保logs目录存在
    os.makedirs("logs", exist_ok=True)

    log_entry = {"timestamp": timestamp, "queues": []}

    for queue in report_data:
        queue_log = {
            "route_id": queue["route_id"],
            "completion_rate": queue["completion_rate"],
            "total_tasks": queue["total_tasks"],
            "completed": queue["completed"],
            "failed": queue["failed"],
            "above_90": queue["above_90"],
        }
        log_entry["queues"].append(queue_log)

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    print(f"📝 进度已记录到: {log_file}")


def main():
    """主函数"""
    print("=" * 60)
    print("队列进度检查脚本启动")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    check_queue_progress()

    print("=" * 60)
    print("进度检查完成")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
