#!/usr/bin/env python3
"""
pending任务分析脚本 - P0紧急修复任务
功能：分析build队列中的pending任务，找出根本原因
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from config.paths import get_queue_file

    queue_file_path = get_queue_file("build_priority")
    if queue_file_path:
        BUILD_QUEUE = queue_file_path
        print(f"✅ 使用config.paths模块获取队列文件: {BUILD_QUEUE}")
    else:
        raise ImportError("无法获取队列文件路径")
except ImportError as e:
    print(f"⚠️  警告: 无法导入路径配置模块: {e}")
    print("   使用回退的硬编码路径...")
    BUILD_QUEUE = Path(
        "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"
    )


def load_queue():
    """加载队列数据"""
    try:
        with open(BUILD_QUEUE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 加载队列文件失败: {e}")
        return None


def analyze_pending_tasks(queue_data):
    """分析pending任务"""
    print("🔍 Pending任务深度分析")
    print("=" * 60)

    if not queue_data or "items" not in queue_data:
        print("❌ 队列数据无效")
        return

    items = queue_data.get("items", {})
    total_tasks = len(items)

    # 统计状态
    status_counts = defaultdict(int)
    for task_id, task in items.items():
        status = task.get("status", "unknown")
        status_counts[status] += 1

    print(f"📊 队列总体统计:")
    print(f"  总任务数: {total_tasks}")
    for status, count in sorted(status_counts.items()):
        percentage = (count / total_tasks) * 100
        print(f"  {status}: {count} ({percentage:.1f}%)")

    # 提取pending任务
    pending_tasks = []
    for task_id, task in items.items():
        if task.get("status") == "pending":
            task_info = {
                "id": task_id,
                "task": task,
                "metadata": task.get("metadata", {}),
                "title": task.get("title", ""),
                "stage": task.get("stage", ""),
                "progress": task.get("progress_percent", 0),
                "updated": task.get("updated_at", ""),
                "instruction_path": task.get("instruction_path", ""),
            }
            pending_tasks.append(task_info)

    pending_count = len(pending_tasks)
    print(f"\n🎯 Pending任务分析 ({pending_count} 个):")
    print("=" * 40)

    if pending_count == 0:
        print("✅ 没有pending任务")
        return

    # 分析pending任务的特征
    print(f"\n📈 Pending任务特征分析:")

    # 1. 按stage分组
    stage_groups = defaultdict(list)
    for task in pending_tasks:
        stage = task["stage"] or "unknown"
        stage_groups[stage].append(task)

    print(f"  按stage分组:")
    for stage, tasks in stage_groups.items():
        print(f"    {stage}: {len(tasks)} 个")

    # 2. 按progress分组
    progress_groups = defaultdict(list)
    for task in pending_tasks:
        progress = task["progress"]
        if progress == 0:
            group = "0% (未开始)"
        elif progress < 50:
            group = "1-49% (进行中)"
        elif progress < 100:
            group = "50-99% (接近完成)"
        else:
            group = "100% (已完成但状态未更新)"
        progress_groups[group].append(task)

    print(f"  按进度分组:")
    for group, tasks in progress_groups.items():
        print(f"    {group}: {len(tasks)} 个")

    # 3. 分析metadata中的proposal_id模式
    proposal_sources = defaultdict(list)
    for task in pending_tasks:
        metadata = task["metadata"]
        proposal_id = metadata.get("proposal_id", "unknown")
        source = metadata.get("source", "unknown")
        key = (
            f"{source}::{proposal_id[:20]}..."
            if len(proposal_id) > 20
            else f"{source}::{proposal_id}"
        )
        proposal_sources[key].append(task)

    print(f"\n📋 按来源和提案ID分组 (前10组):")
    for i, (key, tasks) in enumerate(list(proposal_sources.items())[:10]):
        print(f"  {i+1}. {key}: {len(tasks)} 个pending任务")

    # 4. 分析创建时间（如果metadata中有）
    time_groups = defaultdict(list)
    for task in pending_tasks:
        metadata = task["metadata"]
        created = metadata.get("created", "")
        scan_time = metadata.get("scan_time", "")

        if created:
            # 尝试解析时间
            try:
                created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                date_str = created_dt.strftime("%Y-%m-%d")
                time_groups[date_str].append(task)
            except:
                time_groups["unknown"].append(task)
        else:
            time_groups["no_date"].append(task)

    print(f"\n📅 按创建日期分组:")
    for date_str, tasks in sorted(time_groups.items()):
        print(f"  {date_str}: {len(tasks)} 个")

    # 5. 检查指令路径
    instruction_paths = defaultdict(list)
    for task in pending_tasks:
        path = task["instruction_path"]
        if not path:
            instruction_paths["no_path"].append(task)
        else:
            # 提取目录信息
            path_obj = Path(path)
            if path_obj.exists():
                instruction_paths["exists"].append(task)
            else:
                instruction_paths["missing"].append(task)

    print(f"\n📁 指令文件状态:")
    for status, tasks in instruction_paths.items():
        print(f"  {status}: {len(tasks)} 个")

    # 6. 检查任务标题模式
    title_patterns = defaultdict(list)
    for task in pending_tasks:
        title = task["title"]
        if not title:
            title_patterns["no_title"].append(task)
        elif "bug" in title.lower() or "fix" in title.lower():
            title_patterns["bug_fix"].append(task)
        elif "feature" in title.lower() or "add" in title.lower():
            title_patterns["feature"].append(task)
        elif "refactor" in title.lower() or "optimize" in title.lower():
            title_patterns["refactor"].append(task)
        else:
            title_patterns["other"].append(task)

    print(f"\n📝 标题内容分析:")
    for pattern, tasks in title_patterns.items():
        print(f"  {pattern}: {len(tasks)} 个")

    # 7. 识别可能的阻塞模式
    print(f"\n🔍 可能的问题识别:")

    # 检查是否有依赖问题
    dependency_issues = []
    for task in pending_tasks:
        metadata = task["metadata"]
        # 检查是否有依赖相关的字段
        if any(key in str(metadata).lower() for key in ["depend", "block", "wait", "require"]):
            dependency_issues.append(task)

    if dependency_issues:
        print(f"  ⚠️  可能的依赖问题: {len(dependency_issues)} 个任务")

    # 检查是否有资源问题
    resource_issues = []
    for task in pending_tasks:
        title = task["title"] or ""
        metadata = task["metadata"]
        if any(key in title.lower() for key in ["memory", "cpu", "gpu", "resource", "limit"]):
            resource_issues.append(task)
        elif any(key in str(metadata).lower() for key in ["memory", "cpu", "gpu"]):
            resource_issues.append(task)

    if resource_issues:
        print(f"  ⚠️  可能的资源问题: {len(resource_issues)} 个任务")

    # 检查长时间pending的任务
    long_pending = []
    now = datetime.now()
    for task in pending_tasks:
        metadata = task["metadata"]
        created = metadata.get("created", "")
        if created:
            try:
                created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                days_pending = (now - created_dt).days
                if days_pending > 7:
                    long_pending.append((task, days_pending))
            except:
                pass

    if long_pending:
        print(f"  ⚠️  长时间pending (>7天): {len(long_pending)} 个任务")
        for task, days in long_pending[:5]:
            print(f"    - {task['id'][:30]}...: {days} 天")

    # 生成建议
    print(f"\n🎯 修复建议:")
    print("=" * 40)

    if pending_count > total_tasks * 0.3:
        print(f"  1. ⚠️  Pending比例过高 ({pending_count/total_tasks*100:.1f}%)，目标应<30%")

    if instruction_paths.get("missing"):
        print(f"  2. 🔧 {instruction_paths['missing']} 个任务缺少指令文件，需要检查路径")

    if dependency_issues:
        print(f"  3. 🔗 {len(dependency_issues)} 个任务可能有依赖问题，需要检查依赖关系")

    if resource_issues:
        print(f"  4. 💻 {len(resource_issues)} 个任务可能有资源限制，需要调整资源配置")

    if long_pending:
        print(f"  5. 🕐 {len(long_pending)} 个任务长时间pending，需要优先处理或取消")

    if progress_groups.get("100% (已完成但状态未更新)"):
        print(
            f"  6. ✅ {len(progress_groups['100% (已完成但状态未更新)'])} 个任务进度100%但状态未更新，需要状态同步"
        )

    # 具体行动项
    print(f"\n📋 具体行动项:")
    print(f"  1. 检查指令文件: 验证{instruction_paths.get('missing', 0)}个缺失文件的路径")
    print(f"  2. 分析依赖关系: 审查{dependency_issues}个可能有依赖问题的任务")
    print(f"  3. 优先处理长时间pending任务: {len(long_pending)}个任务超过7天")
    print(f"  4. 同步任务状态: 检查进度100%但状态pending的任务")
    print(f"  5. 重新评估资源需求: {len(resource_issues)}个任务可能受资源限制")

    # 输出示例任务供进一步分析
    print(f"\n🔎 示例任务分析 (前5个):")
    for i, task in enumerate(pending_tasks[:5]):
        print(f"\n  {i+1}. {task['id'][:50]}...")
        print(f"     标题: {task['title'][:50] if task['title'] else '无标题'}")
        print(f"     阶段: {task['stage']}")
        print(f"     进度: {task['progress']}%")
        print(f"     提案ID: {task['metadata'].get('proposal_id', '无')}")
        print(
            f"     指令文件: {task['instruction_path'][:50] if task['instruction_path'] else '无路径'}"
        )


def main():
    """主函数"""
    print("🔍 OpenClaw Pending任务分析脚本 - P0紧急修复")
    print("=" * 60)

    # 检查文件
    if not BUILD_QUEUE.exists():
        print(f"❌ 队列文件不存在: {BUILD_QUEUE}")
        return

    # 加载队列
    queue_data = load_queue()
    if not queue_data:
        return

    # 分析pending任务
    analyze_pending_tasks(queue_data)

    print(f"\n🏁 分析完成")
    print(f"下一步建议:")
    print(f"  1. 根据分析结果制定具体的修复计划")
    print(f"  2. 优先处理长时间pending和关键阻塞任务")
    print(f"  3. 建立任务健康度监控")
    print(f"  4. 优化队列调度策略")


if __name__ == "__main__":
    main()
