#!/usr/bin/env python3
"""
分析AIplan批准文件夹任务积压问题
比较批准文件夹中的提案文件与队列文件中的任务
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Set

import yaml


def extract_proposal_ids(approval_dir: Path) -> List[str]:
    """从批准文件夹中提取所有提案ID"""
    proposal_ids = []

    for file_path in approval_dir.glob("*.md"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 解析YAML frontmatter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 2:
                    frontmatter = parts[1].strip()
                    try:
                        data = yaml.safe_load(frontmatter)
                        if isinstance(data, dict) and "proposal_id" in data:
                            proposal_ids.append(data["proposal_id"])
                        else:
                            print(f"警告: {file_path} 没有有效的proposal_id")
                    except yaml.YAMLError as e:
                        print(f"警告: {file_path} YAML解析错误: {e}")
        except Exception as e:
            print(f"错误: 读取文件 {file_path} 失败: {e}")

    return proposal_ids


def extract_queue_task_ids(queue_file: Path) -> Set[str]:
    """从队列文件中提取所有任务ID"""
    try:
        with open(queue_file, "r", encoding="utf-8") as f:
            queue_data = json.load(f)

        task_ids = set()
        if "items" in queue_data:
            for task_id, task_data in queue_data["items"].items():
                task_ids.add(task_id)

        return task_ids
    except Exception as e:
        print(f"错误: 读取队列文件 {queue_file} 失败: {e}")
        return set()


def analyze_backlog():
    """分析积压问题"""
    # 路径配置
    approval_dir = Path(
        "/Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/批准"
    )
    queue_file = Path(
        "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"
    )

    print("🔍 AIplan批准文件夹任务积压分析")
    print("=" * 60)

    # 检查路径是否存在
    if not approval_dir.exists():
        print(f"❌ 批准文件夹不存在: {approval_dir}")
        return

    if not queue_file.exists():
        print(f"❌ 队列文件不存在: {queue_file}")
        return

    print(f"📁 批准文件夹: {approval_dir}")
    print(f"📊 队列文件: {queue_file}")

    # 提取提案ID
    proposal_ids = extract_proposal_ids(approval_dir)
    print(f"\n📋 批准文件夹中找到 {len(proposal_ids)} 个提案文件")

    # 提取队列任务ID
    queue_task_ids = extract_queue_task_ids(queue_file)
    print(f"📋 队列文件中找到 {len(queue_task_ids)} 个任务")

    # 分析匹配情况
    matched_ids = []
    unmatched_ids = []

    for proposal_id in proposal_ids:
        # 简化ID匹配：提案ID通常包含"proposal-"前缀，队列任务ID可能不同
        # 尝试多种匹配策略
        matched = False

        # 策略1: 直接匹配
        if proposal_id in queue_task_ids:
            matched = True

        # 策略2: 尝试从proposal_id提取可能的任务ID
        if not matched and "-proposal-" in proposal_id:
            # 尝试移除时间戳和proposal后缀
            base_id = proposal_id.split("-proposal-")[0]
            if base_id in queue_task_ids:
                matched = True

        # 策略3: 包含匹配
        if not matched:
            for task_id in queue_task_ids:
                if proposal_id in task_id or task_id in proposal_id:
                    matched = True
                    break

        if matched:
            matched_ids.append(proposal_id)
        else:
            unmatched_ids.append(proposal_id)

    print(f"\n📊 匹配分析结果:")
    print(f"✅ 已匹配到队列的任务: {len(matched_ids)}")
    print(f"❌ 未匹配到队列的任务: {len(unmatched_ids)}")

    if unmatched_ids:
        print(f"\n📝 未匹配的提案ID (前10个):")
        for i, proposal_id in enumerate(unmatched_ids[:10]):
            print(f"  {i+1}. {proposal_id}")

        if len(unmatched_ids) > 10:
            print(f"  ... 还有 {len(unmatched_ids) - 10} 个")

    # 分析队列状态
    try:
        with open(queue_file, "r", encoding="utf-8") as f:
            queue_data = json.load(f)

        if "counts" in queue_data:
            counts = queue_data["counts"]
            print(f"\n📈 队列状态统计:")
            print(f"  - 等待中 (pending): {counts.get('pending', 0)}")
            print(f"  - 运行中 (running): {counts.get('running', 0)}")
            print(f"  - 已完成 (completed): {counts.get('completed', 0)}")
            print(f"  - 已失败 (failed): {counts.get('failed', 0)}")
            print(f"  - 人工暂停 (manual_hold): {counts.get('manual_hold', 0)}")

        # 分析pending任务
        if "items" in queue_data:
            pending_tasks = []
            for task_id, task_data in queue_data["items"].items():
                if task_data.get("status") == "pending":
                    pending_tasks.append(task_id)

            print(f"\n⏳ 队列中的pending任务 (前10个):")
            for i, task_id in enumerate(pending_tasks[:10]):
                print(f"  {i+1}. {task_id}")

            if len(pending_tasks) > 10:
                print(f"  ... 还有 {len(pending_tasks) - 10} 个")

    except Exception as e:
        print(f"错误: 分析队列状态失败: {e}")

    # 结论和建议
    print(f"\n📋 问题诊断:")
    if len(unmatched_ids) > 0:
        print(f"❌ 发现 {len(unmatched_ids)} 个提案未纳入队列系统")
        print("   原因: MAREF智能工作流未自动处理批准文件夹中的提案")
    else:
        print(f"✅ 所有提案都已纳入队列系统")

    print(f"\n🎯 建议解决方案:")
    print("1. 创建自动扫描批准文件夹的脚本")
    print("2. 将pending_review状态的提案转换为队列任务")
    print("3. 修复MAREF工作流自动化断点")
    print("4. 建立批准->队列的自动化管道")


if __name__ == "__main__":
    analyze_backlog()
