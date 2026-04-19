#!/usr/bin/env python3
"""
批准文件夹扫描脚本 - P0紧急修复任务
功能：扫描批准文件夹，将pending_review状态的提案转换为队列任务
"""

import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set

import yaml

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from config.paths import get_queue_file

    queue_file_path = get_queue_file("build_priority")
    if queue_file_path:
        QUEUE_FILE = queue_file_path
        print(f"✅ 使用config.paths模块获取队列文件: {QUEUE_FILE}")
    else:
        raise ImportError("无法获取队列文件路径")
except ImportError as e:
    print(f"⚠️  警告: 无法导入路径配置模块: {e}")
    print("   使用回退的硬编码路径...")
    QUEUE_FILE = Path(
        "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"
    )

# 配置路径 - 批准文件夹是用户特定的，保持硬编码
APPROVAL_DIR = Path(
    "/Users/frankie/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/批准"
)
BACKUP_SUFFIX = ".backup_scan_" + datetime.now().strftime("%Y%m%d_%H%M%S")


def load_yaml_frontmatter(file_path: Path) -> Dict[str, Any]:
    """从Markdown文件中加载YAML frontmatter"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.startswith("---"):
            return {}

        parts = content.split("---", 2)
        if len(parts) < 2:
            return {}

        frontmatter = parts[1].strip()
        data = yaml.safe_load(frontmatter)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"⚠️  读取YAML frontmatter失败 {file_path}: {e}")
        return {}


def extract_proposal_info(file_path: Path) -> Dict[str, Any]:
    """从提案文件中提取信息"""
    data = load_yaml_frontmatter(file_path)
    if not data:
        return {}

    # 读取文件内容用于生成任务描述
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 提取标题（第一行非frontmatter的markdown标题）
    lines = content.split("\n")
    title = ""
    for line in lines:
        if line.startswith("# ") and not line.startswith("# 基于「---」的实施提案"):
            title = line[2:].strip()
            break

    if not title and "proposal_id" in data:
        title = str(data["proposal_id"])

    return {
        "proposal_id": data.get("proposal_id", ""),
        "status": data.get("status", "pending_review"),
        "source": data.get("source", ""),
        "created": data.get("created", ""),
        "file_path": str(file_path),
        "title": title,
        "content": content,
    }


def load_queue() -> Dict[str, Any]:
    """加载队列文件"""
    try:
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 加载队列文件失败: {e}")
        return {}


def save_queue(queue_data: Dict[str, Any]) -> bool:
    """保存队列文件（先备份）"""
    try:
        # 创建备份
        backup_path = QUEUE_FILE.with_suffix(QUEUE_FILE.suffix + BACKUP_SUFFIX)
        import shutil

        shutil.copy2(QUEUE_FILE, backup_path)
        print(f"📂 已创建备份: {backup_path}")

        # 自定义JSON编码器处理datetime对象
        def datetime_handler(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

        # 保存新文件
        with open(QUEUE_FILE, "w", encoding="utf-8") as f:
            json.dump(queue_data, f, indent=2, ensure_ascii=False, default=datetime_handler)
        return True
    except Exception as e:
        print(f"❌ 保存队列文件失败: {e}")
        return False


def proposal_to_task_id(proposal_id: str) -> str:
    """将提案ID转换为任务ID格式"""
    # 移除可能的后缀
    task_id = proposal_id
    if "-proposal-" in task_id:
        task_id = task_id.replace("-proposal-", "-task-")
    elif task_id.endswith("-proposal"):
        task_id = task_id[:-9] + "-task"

    # 如果还没有-task后缀，添加一个
    if "-task-" not in task_id:
        # 使用时间戳生成唯一ID
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        task_id = f"{task_id}-task-{timestamp}"

    return task_id


def create_queue_task(proposal_info: Dict[str, Any]) -> Dict[str, Any]:
    """根据提案信息创建队列任务"""
    proposal_id = proposal_info["proposal_id"]
    task_id = proposal_to_task_id(proposal_id)

    # 基础任务结构
    task = {
        "status": "pending",
        "stage": "build",
        "progress_percent": 0,
        "updated_at": datetime.now().isoformat(),
        "instruction_path": proposal_info["file_path"],
        "metadata": {
            "proposal_id": proposal_id,
            "source": proposal_info.get("source", ""),
            "created": proposal_info.get("created", ""),
            "scan_time": datetime.now().isoformat(),
        },
    }

    # 如果有标题，添加title字段
    if proposal_info.get("title"):
        task["title"] = proposal_info["title"]

    return task_id, task


def update_proposal_status(file_path: Path, new_status: str = "queued") -> bool:
    """更新提案文件中的状态"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.startswith("---"):
            print(f"⚠️  文件 {file_path} 没有YAML frontmatter，无法更新状态")
            return False

        parts = content.split("---", 2)
        if len(parts) < 2:
            return False

        frontmatter = parts[1].strip()
        data = yaml.safe_load(frontmatter)
        if not isinstance(data, dict):
            return False

        # 更新状态
        data["status"] = new_status
        data["queued_at"] = datetime.now().isoformat()

        # 重新构建内容
        new_frontmatter = yaml.dump(data, allow_unicode=True, default_flow_style=False)
        new_content = f"---\n{new_frontmatter}---{parts[2]}"

        # 备份原文件
        backup_path = file_path.with_suffix(file_path.suffix + ".backup")
        import shutil

        shutil.copy2(file_path, backup_path)

        # 写入新内容
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return True
    except Exception as e:
        print(f"❌ 更新提案状态失败 {file_path}: {e}")
        return False


def scan_and_convert():
    """主扫描和转换函数"""
    print("🔍 OpenClaw批准文件夹扫描脚本 - P0紧急修复")
    print("=" * 60)

    # 检查路径
    if not APPROVAL_DIR.exists():
        print(f"❌ 批准文件夹不存在: {APPROVAL_DIR}")
        return

    if not QUEUE_FILE.exists():
        print(f"❌ 队列文件不存在: {QUEUE_FILE}")
        return

    print(f"📁 批准文件夹: {APPROVAL_DIR}")
    print(f"📊 队列文件: {QUEUE_FILE}")

    # 加载队列
    queue_data = load_queue()
    if not queue_data:
        print("❌ 无法加载队列数据，退出")
        return

    # 扫描批准文件夹
    proposal_files = list(APPROVAL_DIR.glob("*.md"))
    print(f"\n📋 找到 {len(proposal_files)} 个提案文件")

    # 分析每个提案
    new_tasks = []
    already_queued = []
    failed_conversions = []

    for i, file_path in enumerate(proposal_files, 1):
        print(f"\n[{i}/{len(proposal_files)}] 处理: {file_path.name}")

        # 提取提案信息
        proposal_info = extract_proposal_info(file_path)
        if not proposal_info:
            print(f"  ⚠️  无法提取提案信息，跳过")
            failed_conversions.append(str(file_path))
            continue

        proposal_id = proposal_info["proposal_id"]
        current_status = proposal_info["status"]

        print(f"  📝 提案ID: {proposal_id}")
        print(f"  📊 当前状态: {current_status}")

        # 检查是否已经在队列中
        task_id = proposal_to_task_id(proposal_id)
        if task_id in queue_data.get("items", {}):
            print(f"  ✅ 已在队列中: {task_id}")
            already_queued.append(proposal_id)
            continue

        # 处理pending_review或queued状态的提案（queued但不在队列中需要修复）
        if current_status not in ["pending_review", "queued"]:
            print(f"  ⚠️  状态不是pending_review或queued ({current_status})，跳过")
            continue

        # 创建队列任务
        try:
            task_id, task = create_queue_task(proposal_info)
            queue_data["items"][task_id] = task
            new_tasks.append(task_id)

            # 更新提案状态
            if update_proposal_status(file_path, "queued"):
                print(f"  ✅ 已添加到队列: {task_id}")
                print(f"  ✅ 提案状态更新为: queued")
            else:
                print(f"  ⚠️  添加到队列但更新提案状态失败")
        except Exception as e:
            print(f"  ❌ 转换失败: {e}")
            failed_conversions.append(str(file_path))

    # 更新队列计数
    if new_tasks:
        # 重新计算计数
        counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "manual_hold": 0}
        for task_id, task in queue_data.get("items", {}).items():
            status = task.get("status", "pending")
            if status in counts:
                counts[status] += 1

        queue_data["counts"] = counts
        queue_data["updated_at"] = datetime.now().isoformat()

        # 保存队列
        if save_queue(queue_data):
            print(f"\n✅ 队列文件已更新，添加了 {len(new_tasks)} 个新任务")
        else:
            print(f"\n❌ 保存队列文件失败")
            return

    # 生成报告
    print(f"\n📊 扫描完成报告")
    print(f"=" * 40)
    print(f"📁 扫描文件总数: {len(proposal_files)}")
    print(f"✅ 新添加到队列: {len(new_tasks)}")
    print(f"📋 已在队列中: {len(already_queued)}")
    print(f"❌ 转换失败: {len(failed_conversions)}")

    if new_tasks:
        print(f"\n🎯 新增任务ID (前10个):")
        for i, task_id in enumerate(new_tasks[:10], 1):
            print(f"  {i}. {task_id}")
        if len(new_tasks) > 10:
            print(f"  ... 还有 {len(new_tasks) - 10} 个")

    if failed_conversions:
        print(f"\n⚠️  转换失败的文件 (前5个):")
        for i, file_path in enumerate(failed_conversions[:5], 1):
            print(f"  {i}. {file_path}")

    # 建议下一步
    print(f"\n🎯 下一步建议:")
    print(f"1. 运行队列监控: python monitor_queue.py")
    print(f"2. 检查队列状态: python check_queue_progress.py")
    print(f"3. 设置定时任务: 将此脚本添加到cron/scheduler")
    print(f"4. 验证MAREF自动化: 检查auto_apply_suggestions设置")


def main():
    """主函数"""
    try:
        scan_and_convert()
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 脚本执行失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
