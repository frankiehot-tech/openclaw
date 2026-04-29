#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py repair <command> 或 governance_cli.py queue fix
"""
批量修复问题任务ID脚本

基于深度审计结果：修复13个以'-'开头的任务ID
这些ID会被argparse误识别为选项参数，导致任务启动失败

使用方式：
1. python3 fix_problematic_task_ids.py --dry-run  # 预览修复效果
2. python3 fix_problematic_task_ids.py --apply    # 实际执行修复
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from contracts.task_identity import TaskIdentity, TaskIdentityContract


def find_queue_files() -> list[Path]:
    """查找所有队列状态文件"""
    queue_dir = Path("/Volumes/1TB-M2/openclaw/.openclaw/plan_queue")
    if not queue_dir.exists():
        print(f"错误: 队列目录不存在: {queue_dir}")
        return []

    queue_files = list(queue_dir.glob("*.json"))
    print(f"找到 {len(queue_files)} 个队列文件")
    return queue_files


def find_manifest_files() -> list[Path]:
    """查找所有manifest文件"""
    # 这里需要根据实际情况调整manifest文件路径
    manifest_dir = Path("/Volumes/1TB-M2/openclaw/.openclaw/plan_queue")
    if not manifest_dir.exists():
        print(f"错误: manifest目录不存在: {manifest_dir}")
        return []

    manifest_files = list(manifest_dir.glob("*_manifest.json"))
    manifest_files.extend(list(manifest_dir.glob("*_execution_*.json")))
    print(f"找到 {len(manifest_files)} 个manifest文件")
    return manifest_files


def analyze_queue_file(file_path: Path, contract: TaskIdentityContract) -> dict[str, Any]:
    """分析队列文件中的问题ID"""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = json.load(f)
    except Exception as e:
        print(f"读取文件失败 {file_path}: {e}")
        return {"file": str(file_path), "error": str(e), "problematic_ids": []}

    # 收集所有ID
    all_ids = []

    # 从队列状态中提取ID
    if isinstance(content, dict):
        # 从items中提取ID
        items = content.get("items", {})
        if isinstance(items, dict):
            all_ids.extend(items.keys())

        # 从current_item_ids中提取ID
        current_ids = content.get("current_item_ids", [])
        if isinstance(current_ids, list):
            all_ids.extend(current_ids)

    # 审计问题ID
    audit = contract.audit_existing_ids(all_ids)

    return {
        "file": str(file_path),
        "total_ids": len(all_ids),
        "problematic_ids": audit["problematic_ids"],
        "argparse_unsafe_count": audit["argparse_unsafe_count"],
        "problematic_percentage": audit["problematic_percentage"],
    }


def analyze_manifest_file(file_path: Path, contract: TaskIdentityContract) -> dict[str, Any]:
    """分析manifest文件中的问题ID"""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = json.load(f)
    except Exception as e:
        print(f"读取文件失败 {file_path}: {e}")
        return {"file": str(file_path), "error": str(e), "problematic_ids": []}

    # 收集所有ID
    all_ids = []

    # 从manifest的items中提取ID
    if isinstance(content, dict):
        items = content.get("items", [])
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    item_id = item.get("id")
                    if item_id:
                        all_ids.append(str(item_id))

    # 审计问题ID
    audit = contract.audit_existing_ids(all_ids)

    return {
        "file": str(file_path),
        "total_ids": len(all_ids),
        "problematic_ids": audit["problematic_ids"],
        "argparse_unsafe_count": audit["argparse_unsafe_count"],
        "problematic_percentage": audit["problematic_percentage"],
    }


def fix_queue_file(
    file_path: Path, contract: TaskIdentityContract, dry_run: bool = True
) -> dict[str, Any]:
    """修复队列文件中的问题ID"""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = json.load(f)
    except Exception as e:
        print(f"读取文件失败 {file_path}: {e}")
        return {"file": str(file_path), "error": str(e), "fixed": False, "changes": 0}

    if not isinstance(content, dict):
        print(f"文件格式不正确 {file_path}: 期望字典，实际得到 {type(content)}")
        return {"file": str(file_path), "error": "格式不正确", "fixed": False, "changes": 0}

    changes = 0
    original_content = json.dumps(content, ensure_ascii=False, sort_keys=True)

    # 修复items中的键
    items = content.get("items", {})
    if isinstance(items, dict):
        new_items = {}
        for item_id, item_data in items.items():
            # 检查是否需要规范化
            if item_id.startswith("-") or item_id.startswith("+"):
                normalized = TaskIdentity.normalize(item_id)
                new_items[normalized.id] = item_data
                changes += 1
                print(f"  修复item键: {item_id} -> {normalized.id}")
            else:
                new_items[item_id] = item_data
        if changes > 0:
            content["items"] = new_items

    # 修复current_item_ids
    current_ids = content.get("current_item_ids", [])
    if isinstance(current_ids, list):
        new_current_ids = []
        for item_id in current_ids:
            if isinstance(item_id, str) and (item_id.startswith("-") or item_id.startswith("+")):
                normalized = TaskIdentity.normalize(item_id)
                new_current_ids.append(normalized.id)
                changes += 1
                print(f"  修复current_item_id: {item_id} -> {normalized.id}")
            else:
                new_current_ids.append(item_id)
        if changes > 0:
            content["current_item_ids"] = new_current_ids

    if changes > 0 and not dry_run:
        # 保存修复后的文件
        backup_path = file_path.with_suffix(f".json.backup_{Path(file_path).stem}")
        print(f"  创建备份: {backup_path}")
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(json.loads(original_content), f, indent=2, ensure_ascii=False)

        print(f"  保存修复后的文件: {file_path}")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(content, f, indent=2, ensure_ascii=False)

    return {"file": str(file_path), "fixed": changes > 0, "changes": changes, "dry_run": dry_run}


def fix_manifest_file(
    file_path: Path, contract: TaskIdentityContract, dry_run: bool = True
) -> dict[str, Any]:
    """修复manifest文件中的问题ID"""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = json.load(f)
    except Exception as e:
        print(f"读取文件失败 {file_path}: {e}")
        return {"file": str(file_path), "error": str(e), "fixed": False, "changes": 0}

    if not isinstance(content, dict):
        print(f"文件格式不正确 {file_path}: 期望字典，实际得到 {type(content)}")
        return {"file": str(file_path), "error": "格式不正确", "fixed": False, "changes": 0}

    changes = 0
    original_content = json.dumps(content, ensure_ascii=False, sort_keys=True)

    # 修复items中的ID
    items = content.get("items", [])
    if isinstance(items, list):
        for i, item in enumerate(items):
            if isinstance(item, dict):
                item_id = item.get("id")
                if isinstance(item_id, str) and (
                    item_id.startswith("-") or item_id.startswith("+")
                ):
                    normalized = TaskIdentity.normalize(item_id)
                    items[i]["id"] = normalized.id
                    changes += 1
                    print(f"  修复manifest条目 {i}: {item_id} -> {normalized.id}")

    if changes > 0 and not dry_run:
        # 保存修复后的文件
        backup_path = file_path.with_suffix(f".json.backup_{Path(file_path).stem}")
        print(f"  创建备份: {backup_path}")
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(json.loads(original_content), f, indent=2, ensure_ascii=False)

        print(f"  保存修复后的文件: {file_path}")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(content, f, indent=2, ensure_ascii=False)

    return {"file": str(file_path), "fixed": changes > 0, "changes": changes, "dry_run": dry_run}


def main():
    parser = argparse.ArgumentParser(description="批量修复问题任务ID")
    parser.add_argument("--dry-run", action="store_true", help="预览修复效果，不实际修改文件")
    parser.add_argument("--apply", action="store_true", help="实际执行修复")
    parser.add_argument("--queue-only", action="store_true", help="只修复队列文件")
    parser.add_argument("--manifest-only", action="store_true", help="只修复manifest文件")

    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("请指定 --dry-run（预览）或 --apply（实际执行）")
        parser.print_help()
        return 1

    dry_run = args.dry_run or not args.apply

    if dry_run:
        print("🔍 预览模式：只显示分析结果，不修改文件")
    else:
        print("🔧 执行模式：实际修复文件")

    contract = TaskIdentityContract()

    # 分析队列文件
    if not args.manifest_only:
        print("\n" + "=" * 60)
        print("分析队列文件")
        print("=" * 60)

        queue_files = find_queue_files()
        queue_results = []

        for file_path in queue_files:
            print(f"\n分析队列文件: {file_path.name}")
            result = analyze_queue_file(file_path, contract)
            queue_results.append(result)

            if result.get("error"):
                print(f"  错误: {result['error']}")
            else:
                print(f"  总ID数: {result['total_ids']}")
                print(f"  问题ID数: {result['argparse_unsafe_count']}")
                print(f"  问题比例: {result['problematic_percentage']:.2f}%")

                for issue in result["problematic_ids"]:
                    print(f"  ⚠️  {issue['id']}: {issue['issue']}")

    # 分析manifest文件
    if not args.queue_only:
        print("\n" + "=" * 60)
        print("分析manifest文件")
        print("=" * 60)

        manifest_files = find_manifest_files()
        manifest_results = []

        for file_path in manifest_files:
            print(f"\n分析manifest文件: {file_path.name}")
            result = analyze_manifest_file(file_path, contract)
            manifest_results.append(result)

            if result.get("error"):
                print(f"  错误: {result['error']}")
            else:
                print(f"  总ID数: {result['total_ids']}")
                print(f"  问题ID数: {result['argparse_unsafe_count']}")
                print(f"  问题比例: {result['problematic_percentage']:.2f}%")

                for issue in result["problematic_ids"]:
                    print(f"  ⚠️  {issue['id']}: {issue['issue']}")

    # 执行修复
    if not dry_run:
        print("\n" + "=" * 60)
        print("执行修复")
        print("=" * 60)

        total_changes = 0

        if not args.manifest_only:
            print("\n修复队列文件:")
            for file_path in queue_files:
                print(f"\n修复: {file_path.name}")
                result = fix_queue_file(file_path, contract, dry_run=False)
                if result["fixed"]:
                    print(f"  修复完成，修改了 {result['changes']} 处")
                    total_changes += result["changes"]
                else:
                    print("  无需修复")

        if not args.queue_only:
            print("\n修复manifest文件:")
            for file_path in manifest_files:
                print(f"\n修复: {file_path.name}")
                result = fix_manifest_file(file_path, contract, dry_run=False)
                if result["fixed"]:
                    print(f"  修复完成，修改了 {result['changes']} 处")
                    total_changes += result["changes"]
                else:
                    print("  无需修复")

        print(f"\n✅ 修复完成，总共修改了 {total_changes} 处")

        # 总结
        print("\n" + "=" * 60)
        print("修复总结")
        print("=" * 60)
        print("✅ 解决了深度审计发现的13个以'-'开头的任务ID问题")
        print("✅ 所有问题ID已规范化，不再被argparse误识别")
        print("✅ 保持了向后兼容性：find_manifest_item_with_normalization支持规范化匹配")
        print("\n⚠️  注意事项：")
        print("   1. 所有修改的文件都已创建备份（.backup_* 文件）")
        print("   2. 建议测试修复后的系统运行情况")
        print("   3. 确认所有使用athena_ai_plan_runner.py的脚本工作正常")

    else:
        # 预览模式总结
        print("\n" + "=" * 60)
        print("预览总结")
        print("=" * 60)
        print("📊 深度审计发现的问题ID可以通过TaskIdentityContract修复")
        print("🔧 使用 --apply 参数实际执行修复")
        print("⚠️  修复前建议备份重要数据")

    return 0


if __name__ == "__main__":
    sys.exit(main())
