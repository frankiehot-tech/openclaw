#!/usr/bin/env python3
"""
分析队列依赖关系，识别阻塞原因
"""

import json
import re
import sys
from collections import defaultdict, deque


def load_queue_file(filepath):
    """加载队列文件"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_dependencies_from_summary(summary):
    """从summary字段提取依赖任务ID"""
    if not summary:
        return []

    # 匹配模式：被依赖项阻塞：task_id(pending)
    pattern = r"被依赖项阻塞：([^(]+)\(pending\)"
    matches = re.findall(pattern, summary)
    return [match.strip() for match in matches]


def analyze_dependencies(queue_data):
    """分析队列中的依赖关系"""
    items = queue_data.get("items", {})

    # 收集所有任务状态
    task_states = {}
    dependencies = defaultdict(list)  # task -> [depends_on]
    reverse_deps = defaultdict(list)  # depends_on -> [task]

    for task_id, task_data in items.items():
        status = task_data.get("status", "unknown")
        task_states[task_id] = status

        # 从summary提取依赖
        summary = task_data.get("summary", "")
        deps = extract_dependencies_from_summary(summary)

        # 从metadata提取依赖（如果存在）
        metadata = task_data.get("metadata", {})
        if "depends_on" in metadata:
            deps.extend(metadata["depends_on"])

        if deps:
            dependencies[task_id] = deps
            for dep in deps:
                reverse_deps[dep].append(task_id)

    return task_states, dict(dependencies), dict(reverse_deps)


def find_blocks(task_states, dependencies, reverse_deps):
    """找出阻塞任务"""
    blocks = []

    for task_id, deps in dependencies.items():
        if task_states.get(task_id) != "pending":
            continue

        blocked_by = []
        for dep in deps:
            dep_state = task_states.get(dep, "unknown")
            if dep_state != "completed":
                blocked_by.append((dep, dep_state))

        if blocked_by:
            blocks.append(
                {
                    "task_id": task_id,
                    "blocked_by": blocked_by,
                    "dependency_count": len(deps),
                    "blocked_count": len(blocked_by),
                }
            )

    return blocks


def find_missing_dependencies(task_states, dependencies):
    """查找不存在的依赖任务"""
    missing = []
    all_task_ids = set(task_states.keys())

    for task_id, deps in dependencies.items():
        for dep in deps:
            if dep not in all_task_ids:
                missing.append(
                    {
                        "task_id": task_id,
                        "missing_dep": dep,
                        "task_state": task_states.get(task_id, "unknown"),
                    }
                )

    return missing


def find_cyclic_dependencies(dependencies):
    """使用DFS检测循环依赖"""
    visited = set()
    recursion_stack = set()
    cycles = []

    def dfs(node, path):
        if node in recursion_stack:
            # 找到循环
            cycle_start = path.index(node)
            cycle = path[cycle_start:]
            if cycle not in cycles:
                cycles.append(cycle)
            return

        if node in visited:
            return

        visited.add(node)
        recursion_stack.add(node)

        for neighbor in dependencies.get(node, []):
            dfs(neighbor, path + [node])

        recursion_stack.remove(node)

    for node in dependencies:
        if node not in visited:
            dfs(node, [])

    return cycles


def main():
    if len(sys.argv) < 2:
        print("用法: python analyze_queue_dependencies.py <队列文件路径>")
        sys.exit(1)

    filepath = sys.argv[1]
    print(f"分析队列文件: {filepath}")

    try:
        queue_data = load_queue_file(filepath)
    except Exception as e:
        print(f"加载文件失败: {e}")
        sys.exit(1)

    # 基本统计
    items = queue_data.get("items", {})
    counts = queue_data.get("counts", {})
    print(f"任务总数: {len(items)}")
    print(f"计数统计: {json.dumps(counts, ensure_ascii=False, indent=2)}")

    # 分析依赖关系
    task_states, dependencies, reverse_deps = analyze_dependencies(queue_data)

    # 按状态分组
    status_groups = defaultdict(list)
    for task_id, status in task_states.items():
        status_groups[status].append(task_id)

    print(f"\n状态分布:")
    for status, tasks in status_groups.items():
        print(f"  {status}: {len(tasks)}个任务")

    # 分析pending任务
    pending_tasks = status_groups.get("pending", [])
    if pending_tasks:
        print(f"\n待处理任务 ({len(pending_tasks)}个):")
        for i, task_id in enumerate(pending_tasks[:10], 1):
            print(f"  {i}. {task_id}")
            if task_id in dependencies:
                print(f"     依赖: {', '.join(dependencies[task_id])}")

        if len(pending_tasks) > 10:
            print(f"  ... 以及另外{len(pending_tasks)-10}个任务")

    # 查找阻塞
    blocks = find_blocks(task_states, dependencies, reverse_deps)
    if blocks:
        print(f"\n阻塞任务 ({len(blocks)}个):")
        for block in blocks[:10]:
            print(f"  任务: {block['task_id']}")
            for dep, dep_state in block["blocked_by"]:
                print(f"    被阻塞于: {dep} ({dep_state})")

    # 查找缺失依赖
    missing = find_missing_dependencies(task_states, dependencies)
    if missing:
        print(f"\n缺失依赖 ({len(missing)}个):")
        for m in missing[:10]:
            print(f"  任务 {m['task_id']} 依赖不存在的任务: {m['missing_dep']}")

    # 查找循环依赖
    cycles = find_cyclic_dependencies(dependencies)
    if cycles:
        print(f"\n循环依赖 ({len(cycles)}个):")
        for i, cycle in enumerate(cycles, 1):
            print(f"  循环{i}: {' -> '.join(cycle)} -> {cycle[0]}")

    # 失败的依赖分析
    failed_tasks = status_groups.get("failed", [])
    if failed_tasks:
        print(f"\n失败任务 ({len(failed_tasks)}个):")
        for i, task_id in enumerate(failed_tasks[:10], 1):
            print(f"  {i}. {task_id}")
            # 检查是否有任务依赖此失败任务
            if task_id in reverse_deps:
                print(f"     阻塞以下任务: {', '.join(reverse_deps[task_id])}")

    # 建议
    print(f"\n建议:")
    if blocks:
        print("  1. 解决被阻塞任务的依赖问题")
    if missing:
        print("  2. 修复缺失的依赖任务引用")
    if cycles:
        print("  3. 打破循环依赖")
    if failed_tasks:
        print("  4. 重试或清理失败任务，因为它们可能阻塞其他任务")

    if not blocks and not missing and not cycles:
        print("  没有检测到明显的依赖问题，可能需要检查其他阻塞原因")


if __name__ == "__main__":
    main()
