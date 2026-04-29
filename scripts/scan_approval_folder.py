#!/usr/bin/env python3
"""
批准文件夹扫描器 - 将pending_review提案转换为队列任务
P0紧急修复：清理当前49个提案积压
"""

import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

# 配置
APPROVAL_DIR = Path(
    "/Volumes/1TB-M2/openclaw/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan/批准"
)
QUEUE_FILE = Path(
    "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"
)
BACKUP_DIR = Path("/Volumes/1TB-M2/openclaw/.openclaw/backups")


def ensure_backup_dir():
    """确保备份目录存在"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def backup_queue_file():
    """备份队列文件"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"queue_backup_{timestamp}.json"

    try:
        import shutil

        shutil.copy2(QUEUE_FILE, backup_path)
        print(f"✅ 队列文件已备份: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"❌ 备份失败: {e}")
        return None


def parse_proposal_file(file_path: Path) -> dict[str, Any] | None:
    """解析提案文件，提取任务信息"""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # 解析YAML frontmatter
        if not content.startswith("---"):
            print(f"⚠️  文件 {file_path.name} 没有YAML frontmatter")
            return None

        parts = content.split("---", 2)
        if len(parts) < 2:
            print(f"⚠️  文件 {file_path.name} YAML格式不完整")
            return None

        frontmatter = parts[1].strip()
        try:
            data = yaml.safe_load(frontmatter)
        except yaml.YAMLError as e:
            print(f"❌ 文件 {file_path.name} YAML解析错误: {e}")
            return None

        if not isinstance(data, dict):
            print(f"⚠️  文件 {file_path.name} frontmatter不是字典")
            return None

        # 检查状态
        status = data.get("status")
        if status != "pending_review":
            print(f"⚠️  文件 {file_path.name} 状态不是pending_review: {status}")
            return None

        # 提取基本信息
        proposal_id = data.get("proposal_id", file_path.stem)
        source = data.get("source", "")
        created = data.get("created", datetime.now().isoformat())

        # 生成任务配置
        task_id = f"approved_proposal_{uuid.uuid4().hex[:8]}"

        # 从文件名推断任务类型
        filename = file_path.name.lower()
        if "gene" in filename or "基因" in filename:
            category = "gene_management"
            lane = "build_auto"
        elif "audit" in filename or "审计" in filename:
            category = "audit"
            lane = "review_auto"
        elif "test" in filename or "测试" in filename:
            category = "test"
            lane = "build_auto"
        else:
            category = "implementation"
            lane = "build_auto"

        # 构建任务配置
        task_config = {
            "id": task_id,
            "title": f"已批准提案: {proposal_id}",
            "instruction_path": str(file_path),
            "status": "pending",
            "progress_percent": 0,
            "started_at": "",
            "finished_at": "",
            "runner_pid": "",
            "runner_heartbeat_at": "",
            "metadata": {
                "proposal_id": proposal_id,
                "source_file": source,
                "created": created,
                "category": category,
                "lane": lane,
                "priority": "S1",  # 高优先级，因为是积压清理
                "rationale": "从批准文件夹积压中自动导入",
                "auto_generated": True,
                "original_status": "pending_review",
                "import_time": datetime.now().isoformat(),
            },
        }

        print(f"✅ 解析提案: {proposal_id} -> 任务ID: {task_id}")
        return task_config

    except Exception as e:
        print(f"❌ 解析文件 {file_path} 失败: {e}")
        return None


def load_queue_data() -> dict[str, Any]:
    """加载队列数据"""
    try:
        with open(QUEUE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 加载队列文件失败: {e}")
        return {
            "items": {},
            "counts": {"pending": 0, "running": 0, "completed": 0, "failed": 0, "manual_hold": 0},
        }


def save_queue_data(queue_data: dict[str, Any]):
    """保存队列数据"""
    try:
        # 更新元数据
        queue_data["updated_at"] = datetime.now().isoformat()
        queue_data["description"] = (
            f"包含批准文件夹导入任务，更新于{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        with open(QUEUE_FILE, "w", encoding="utf-8") as f:
            json.dump(queue_data, f, indent=2, ensure_ascii=False)

        print(f"✅ 队列文件已保存: {QUEUE_FILE}")
    except Exception as e:
        print(f"❌ 保存队列文件失败: {e}")
        raise


def update_queue_counts(queue_data: dict[str, Any]):
    """更新队列计数"""
    if "items" not in queue_data:
        queue_data["items"] = {}

    items = queue_data["items"]
    counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "manual_hold": 0}

    for _item_id, item_data in items.items():
        status = item_data.get("status", "pending")
        if status in counts:
            counts[status] += 1
        else:
            counts["pending"] += 1

    if "counts" not in queue_data:
        queue_data["counts"] = counts
    else:
        queue_data["counts"].update(counts)


def process_approval_folder():
    """处理批准文件夹"""
    print("🔍 开始扫描批准文件夹...")
    print(f"📁 目录: {APPROVAL_DIR}")

    if not APPROVAL_DIR.exists():
        print(f"❌ 批准文件夹不存在: {APPROVAL_DIR}")
        return []

    # 查找所有提案文件
    proposal_files = list(APPROVAL_DIR.glob("*.md"))
    print(f"📋 找到 {len(proposal_files)} 个提案文件")

    # 解析提案文件
    tasks = []
    for file_path in proposal_files:
        task_config = parse_proposal_file(file_path)
        if task_config:
            tasks.append(task_config)

    print(f"✅ 成功解析 {len(tasks)} 个提案")
    return tasks


def import_to_queue(tasks: list[dict[str, Any]], dry_run: bool = False):
    """将任务导入队列"""
    print(f"\n📤 准备导入 {len(tasks)} 个任务到队列...")

    # 备份队列文件
    if not dry_run:
        backup_queue_file()

    # 加载队列数据
    queue_data = load_queue_data()

    # 确保items字段存在
    if "items" not in queue_data:
        queue_data["items"] = {}

    # 导入任务
    imported_count = 0
    for task in tasks:
        task_id = task["id"]

        # 检查是否已存在
        if task_id in queue_data["items"]:
            print(f"⚠️  任务 {task_id} 已存在，跳过")
            continue

        # 添加到队列
        queue_data["items"][task_id] = task
        imported_count += 1

        if not dry_run:
            print(f"✅ 导入任务: {task_id}")

    print("\n📊 导入统计:")
    print(f"  - 尝试导入: {len(tasks)} 个任务")
    print(f"  - 实际导入: {imported_count} 个新任务")
    print(f"  - 已存在: {len(tasks) - imported_count} 个任务")

    # 更新计数
    update_queue_counts(queue_data)

    # 保存队列数据
    if not dry_run and imported_count > 0:
        save_queue_data(queue_data)
        print(f"\n🎉 成功导入 {imported_count} 个新任务到队列")
    elif dry_run:
        print(f"\n🔍 模拟运行完成，将导入 {imported_count} 个新任务")
    else:
        print("\nℹ️  没有新任务需要导入")

    return imported_count


def update_proposal_status(file_path: Path, new_status: str = "queued"):
    """更新提案文件状态"""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        if not content.startswith("---"):
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

        # 重新构建文件
        new_frontmatter = yaml.dump(data, allow_unicode=True, default_flow_style=False)
        new_content = f"---\n{new_frontmatter}---\n{parts[2] if len(parts) > 2 else ''}"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        print(f"✅ 更新提案状态: {file_path.name} -> {new_status}")
        return True

    except Exception as e:
        print(f"❌ 更新提案状态失败 {file_path}: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("🧹 AIplan批准文件夹积压清理工具")
    print("=" * 60)

    # 参数解析
    dry_run = "--dry-run" in sys.argv
    skip_status_update = "--skip-status-update" in sys.argv

    if dry_run:
        print("🔍 模拟运行模式 - 不实际修改文件")

    # 确保备份目录
    ensure_backup_dir()

    # 处理批准文件夹
    tasks = process_approval_folder()
    if not tasks:
        print("❌ 没有找到可处理的提案")
        return

    # 导入到队列
    imported_count = import_to_queue(tasks, dry_run=dry_run)

    # 更新提案状态
    if not dry_run and not skip_status_update and imported_count > 0:
        print("\n📝 更新提案文件状态...")
        updated_count = 0
        for file_path in APPROVAL_DIR.glob("*.md"):
            if update_proposal_status(file_path, "queued"):
                updated_count += 1

        print(f"✅ 更新了 {updated_count} 个提案文件状态")

    # 输出总结
    print("\n" + "=" * 60)
    print("🎉 积压清理完成!")
    print("=" * 60)

    print("\n📊 清理结果:")
    print(f"✅ 扫描提案: {len(list(APPROVAL_DIR.glob('*.md')))} 个")
    print(f"✅ 解析成功: {len(tasks)} 个")
    print(f"✅ 导入队列: {imported_count} 个新任务")

    if not dry_run:
        # 重新加载队列显示最新状态
        queue_data = load_queue_data()
        counts = queue_data.get("counts", {})
        print("📈 队列最新状态:")
        print(f"  - 等待中: {counts.get('pending', 0)}")
        print(f"  - 运行中: {counts.get('running', 0)}")
        print(f"  - 已完成: {counts.get('completed', 0)}")
        print(f"  - 总任务: {len(queue_data.get('items', {}))}")

    print("\n🚀 下一步:")
    print("1. 运行队列监控: python3 scripts/queue_monitor.py")
    print("2. 检查导入的任务状态")
    print("3. 验证提案文件状态已更新")
    print("4. 建立定期扫描定时任务")

    print("\n💡 建议:")
    print("- 首次运行后观察队列执行情况")
    print("- 调整任务优先级和依赖关系")
    print("- 建立长期监控防止再次积压")


if __name__ == "__main__":
    main()
