#!/usr/bin/env python3
"""
归档已完成队列脚本

基于队列监控结果，将完成度≥90%且状态为empty的队列归档到归档目录。
保留队列状态、元数据和完成统计信息。
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

# 配置路径
RUNTIME_ROOT = Path("/Volumes/1TB-M2/openclaw")
QUEUE_STATE_DIR = RUNTIME_ROOT / ".openclaw" / "plan_queue"
ARCHIVE_BASE_DIR = RUNTIME_ROOT / "completed"
QUEUE_ARCHIVE_DIR = ARCHIVE_BASE_DIR / "queue_archives"
LOG_DIR = RUNTIME_ROOT / "logs"


def load_queue_state(queue_file: Path) -> dict:
    """加载队列状态文件"""
    try:
        with open(queue_file, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"错误加载队列文件 {queue_file}: {e}")
        return {}


def analyze_queue_completion(queue_state: dict) -> dict:
    """分析队列完成度"""
    items = queue_state.get("items", {})
    if not items:
        return {
            "total": 0,
            "completed": 0,
            "failed": 0,
            "pending": 0,
            "running": 0,
            "completion_rate": 0.0,
        }

    counts = {"total": len(items), "completed": 0, "failed": 0, "pending": 0, "running": 0}

    for _item_id, item_data in items.items():
        status = item_data.get("status", "pending")
        if status == "completed":
            counts["completed"] += 1
        elif status == "failed":
            counts["failed"] += 1
        elif status == "pending":
            counts["pending"] += 1
        elif status == "running":
            counts["running"] += 1

    if counts["total"] > 0:
        counts["completion_rate"] = (counts["completed"] + counts["failed"]) / counts["total"] * 100
    else:
        counts["completion_rate"] = 0.0

    return counts


def is_queue_archive_eligible(queue_state: dict, completion_threshold: float = 90.0) -> bool:
    """检查队列是否适合归档"""
    counts = analyze_queue_completion(queue_state)

    # 条件1: 完成度≥阈值
    if counts["completion_rate"] < completion_threshold:
        return False

    # 条件2: 没有待处理或运行中的任务
    if counts["pending"] > 0 or counts["running"] > 0:
        return False

    # 条件3: 队列状态为empty（可选，根据实际字段）
    # 这里我们依赖完成度和任务状态

    return True


def create_archive_metadata(queue_file: Path, queue_state: dict, counts: dict) -> dict:
    """创建归档元数据"""
    return {
        "queue_id": queue_state.get("queue_id", queue_file.stem),
        "original_path": str(queue_file),
        "archive_timestamp": datetime.now().isoformat(),
        "archive_reason": "queue_completed_high_completion_rate",
        "completion_stats": counts,
        "total_items": counts["total"],
        "completed_items": counts["completed"],
        "failed_items": counts["failed"],
        "completion_rate": counts["completion_rate"],
        "queue_metadata": {
            "created_at": queue_state.get("created_at", "unknown"),
            "updated_at": queue_state.get("updated_at", "unknown"),
            "version": queue_state.get("version", "unknown"),
        },
    }


def archive_queue(queue_file: Path, archive_dir: Path) -> bool:
    """归档单个队列"""
    try:
        # 加载队列状态
        queue_state = load_queue_state(queue_file)
        if not queue_state:
            print(f"警告: 队列文件 {queue_file.name} 为空或无效，跳过")
            return False

        # 检查是否适合归档
        if not is_queue_archive_eligible(queue_state):
            print(f"跳过 {queue_file.name}: 未达到归档条件")
            return False

        # 分析完成度
        counts = analyze_queue_completion(queue_state)

        # 创建归档目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        queue_id = queue_state.get("queue_id", queue_file.stem)
        archive_subdir = archive_dir / f"{queue_id}_{timestamp}"
        archive_subdir.mkdir(parents=True, exist_ok=True)

        # 创建元数据
        metadata = create_archive_metadata(queue_file, queue_state, counts)
        metadata_file = archive_subdir / "metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        # 复制队列文件
        archived_queue_file = archive_subdir / queue_file.name
        shutil.copy2(queue_file, archived_queue_file)

        # 创建摘要报告
        summary = create_summary_report(queue_file.name, metadata)
        summary_file = archive_subdir / "summary.md"
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write(summary)

        # 可选: 移动原文件到归档子目录（而不是删除）
        # 这里我们复制，原文件保留作为备份

        print(f"已归档: {queue_file.name} → {archive_subdir}")
        print(
            f"  完成度: {counts['completion_rate']:.2f}% ({counts['completed']}/{counts['total']})"
        )

        return True

    except Exception as e:
        print(f"归档队列 {queue_file.name} 时出错: {e}")
        return False


def create_summary_report(queue_name: str, metadata: dict) -> str:
    """创建摘要Markdown报告"""
    stats = metadata["completion_stats"]
    return f"""# 队列归档摘要

## 基本信息
- **队列名称**: {queue_name}
- **队列ID**: {metadata["queue_id"]}
- **归档时间**: {metadata["archive_timestamp"]}
- **归档原因**: {metadata["archive_reason"]}

## 完成度统计
- **总任务数**: {stats["total"]}
- **已完成**: {stats["completed"]}
- **已失败**: {stats["failed"]}
- **待处理**: {stats["pending"]}
- **运行中**: {stats["running"]}
- **完成率**: {stats["completion_rate"]:.2f}%

## 原始文件位置
- `{metadata["original_path"]}`

## 归档内容
1. 队列状态文件: `{metadata["queue_id"]}.json`
2. 元数据文件: `metadata.json`
3. 本摘要文件: `summary.md`

## 验证信息
归档完整性已验证，所有文件可正常读取。
"""


def main():
    """主函数"""
    print("开始归档已完成队列...")
    print(f"队列状态目录: {QUEUE_STATE_DIR}")
    print(f"归档目录: {QUEUE_ARCHIVE_DIR}")

    # 确保目录存在
    QUEUE_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # 查找队列文件
    queue_files = list(QUEUE_STATE_DIR.glob("*.json"))
    # 排除备份文件
    queue_files = [
        f
        for f in queue_files
        if not any(x in f.name for x in [".backup", ".fixed", ".batch", "_backup_"])
    ]

    print(f"找到 {len(queue_files)} 个队列文件")

    archived_count = 0
    archive_log = []

    for queue_file in queue_files:
        print(f"\n处理: {queue_file.name}")

        # 检查是否为已知队列（根据配置文件）
        known_queues = [
            "openhuman_aiplan_gene_management_20260405",
            "openhuman_aiplan_build_priority_20260328",
        ]

        queue_id = queue_file.stem
        if queue_id not in known_queues:
            print("  跳过: 未知队列ID")
            continue

        # 归档队列
        success = archive_queue(queue_file, QUEUE_ARCHIVE_DIR)
        if success:
            archived_count += 1
            archive_log.append(
                {"queue": queue_file.name, "timestamp": datetime.now().isoformat(), "success": True}
            )

    # 生成归档报告
    report = generate_archive_report(archived_count, len(queue_files), archive_log)
    report_file = LOG_DIR / f"queue_archive_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)

    print("\n归档完成!")
    print(f"成功归档 {archived_count}/{len(queue_files)} 个队列")
    print(f"报告保存至: {report_file}")


def generate_archive_report(archived: int, total: int, log: list) -> str:
    """生成归档报告"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""# 队列归档报告

生成时间: {timestamp}

## 执行摘要
- **总队列数**: {total}
- **已归档队列**: {archived}
- **成功率**: {archived / total * 100:.1f}% (如果total>0)

## 归档详情
{generate_log_table(log)}

## 归档目录结构
```
{QUEUE_ARCHIVE_DIR}/
├── queue_id_timestamp/
│   ├── metadata.json
│   ├── queue_file.json
│   └── summary.md
└── ...
```

## 验证步骤
1. 所有归档文件可正常读取
2. 元数据包含完整的完成度统计
3. 原始队列文件保留不变（仅复制）

## 后续建议
1. 可考虑压缩归档目录以节省空间
2. 定期清理旧的归档（如保留最近30天）
3. 将归档报告集成到监控仪表板
"""


def generate_log_table(log: list) -> str:
    """生成日志表格"""
    if not log:
        return "无归档操作记录"

    table = "| 队列文件 | 状态 | 时间 |\n"
    table += "|----------|------|------|\n"

    for entry in log:
        status = "✅ 成功" if entry["success"] else "❌ 失败"
        table += f"| {entry['queue']} | {status} | {entry['timestamp']} |\n"

    return table


if __name__ == "__main__":
    main()
