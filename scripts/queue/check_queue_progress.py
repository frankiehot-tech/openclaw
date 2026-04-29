#!/usr/bin/env python3
"""
检查队列进度，如果完成度达到90%以上，开始准备分析报告；否则记录当前进度
"""

import json
import os
import sys
from datetime import datetime


def load_json(filepath):
    """加载JSON文件"""
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def main():
    print("检查队列进度...")
    print("=" * 60)

    # 加载manifest
    manifest_path = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_priority_execution_20260414.json"
    if not os.path.exists(manifest_path):
        print(f"Manifest文件不存在: {manifest_path}")
        return

    manifest = load_json(manifest_path)
    items = manifest.get("items", [])

    # 加载队列状态
    queue_state_path = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"
    if not os.path.exists(queue_state_path):
        print(f"队列状态文件不存在: {queue_state_path}")
        return

    queue_state = load_json(queue_state_path)
    queue_items = queue_state.get("items", {})

    print(f"Manifest总任务数: {len(items)}")
    print(f"队列状态中的任务数: {len(queue_items)}")

    # 创建任务ID到状态的映射，优先使用队列状态
    task_status = {}
    for task_id, task_data in queue_items.items():
        task_status[task_id] = task_data.get("status", "unknown")

    # 对于manifest中但不在队列状态中的任务，使用manifest状态
    for item in items:
        task_id = item.get("id")
        if task_id not in task_status:
            task_status[task_id] = item.get("status", "unknown")

    # 统计状态
    status_counts = {}
    for status in task_status.values():
        status_counts[status] = status_counts.get(status, 0) + 1

    # 计算完成度
    total_tasks = len(items)
    completed_tasks = status_counts.get("completed", 0)
    failed_tasks = status_counts.get("failed", 0)
    finished_tasks = completed_tasks + failed_tasks

    if total_tasks == 0:
        print("错误: 总任务数为0")
        return

    completion_rate = (finished_tasks / total_tasks) * 100

    print("\n任务状态统计:")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")

    print("\n完成度统计:")
    print(f"  总任务数: {total_tasks}")
    print(f"  已完成: {completed_tasks}")
    print(f"  已失败: {failed_tasks}")
    print(f"  已完成+失败: {finished_tasks}")
    print(f"  完成度: {completion_rate:.2f}%")

    # 检查完成度阈值
    if completion_rate >= 90:
        print(f"\n✅ 完成度已达到 {completion_rate:.2f}% (超过90%)")
        print("开始准备分析报告...")

        # 准备分析报告
        report = prepare_analysis_report(items, task_status, status_counts, completion_rate)

        # 保存报告
        report_path = save_report(report, completion_rate)

        print(f"\n📊 分析报告已保存至: {report_path}")
        return True
    else:
        print(f"\n📈 当前完成度: {completion_rate:.2f}% (未达到90%)")
        print("记录当前进度...")

        # 记录进度
        log_progress(status_counts, completion_rate)
        return False


def prepare_analysis_report(items, task_status, status_counts, completion_rate):
    """准备分析报告"""
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("队列完成度分析报告")
    report_lines.append("=" * 80)
    report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"总任务数: {len(items)}")
    report_lines.append(f"完成度: {completion_rate:.2f}%")
    report_lines.append("")

    # 状态统计
    report_lines.append("任务状态统计:")
    for status, count in sorted(status_counts.items()):
        report_lines.append(f"  - {status}: {count}")
    report_lines.append("")

    # 未完成的任务
    unfinished_tasks = []
    for item in items:
        task_id = item.get("id")
        status = task_status.get(task_id, "unknown")
        if status not in ["completed", "failed"]:
            unfinished_tasks.append((task_id, status))

    if unfinished_tasks:
        report_lines.append(f"未完成任务 ({len(unfinished_tasks)}个):")
        for task_id, status in unfinished_tasks[:20]:  # 最多显示20个
            report_lines.append(f"  - {task_id}: {status}")

        if len(unfinished_tasks) > 20:
            report_lines.append(f"  ... 以及另外 {len(unfinished_tasks) - 20} 个任务")
        report_lines.append("")

    # 关键任务状态
    critical_tasks = [
        "aiplan_queue_runner_persistence",
        "aiplan_queue_runner_closeout",
        "phase1_runtime_closeout",
        "athena_p0_schema_hitl_dispatch",
        "athena_validation_moat_build",
    ]

    report_lines.append("关键任务状态:")
    for task_id in critical_tasks:
        status = task_status.get(task_id, "not_found")
        # 查找依赖关系
        depends_on = []
        for item in items:
            if item.get("id") == task_id:
                depends_on = item.get("metadata", {}).get("depends_on", [])
                break
        report_lines.append(f"  - {task_id}: {status}, 依赖项: {depends_on}")
    report_lines.append("")

    # 建议
    report_lines.append("建议:")
    if completion_rate >= 90:
        report_lines.append("  ✅ 队列完成度良好，可考虑:")
        report_lines.append("    1. 验证剩余任务的重要性")
        report_lines.append("    2. 检查是否有阻塞的依赖关系")
        report_lines.append("    3. 准备最终收尾工作")
    else:
        report_lines.append("  ⚠️ 队列完成度不足，建议:")
        report_lines.append("    1. 优先处理关键路径任务")
        report_lines.append("    2. 检查并解决依赖阻塞")
        report_lines.append("    3. 监控队列处理器状态")

    report_lines.append("=" * 80)

    return "\n".join(report_lines)


def save_report(report, completion_rate):
    """保存报告到文件"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    rate_str = f"{completion_rate:.1f}".replace(".", "_")
    report_dir = "/Volumes/1TB-M2/openclaw/.openclaw/reports"

    # 确保报告目录存在
    os.makedirs(report_dir, exist_ok=True)

    report_path = os.path.join(
        report_dir, f"queue_completion_analysis_{rate_str}percent_{timestamp}.md"
    )

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    return report_path


def log_progress(status_counts, completion_rate):
    """记录当前进度到日志文件"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_dir = "/Volumes/1TB-M2/openclaw/.openclaw/logs"

    # 确保日志目录存在
    os.makedirs(log_dir, exist_ok=True)

    log_path = os.path.join(log_dir, "queue_progress.log")

    log_entry = f"{timestamp} - 完成度: {completion_rate:.2f}% - 状态统计: {dict(status_counts)}\n"

    # 追加到日志文件
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(log_entry)

    print(f"进度已记录到: {log_path}")


if __name__ == "__main__":
    try:
        success = main()
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        print(f"检查队列进度时出错: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
