#!/usr/bin/env python3
"""
任务ID规范化修复脚本

基于深度审计发现：优先执行队列中有13个以'-'开头的任务ID
此脚本使用TaskIdentityContract进行任务ID规范化修复
"""

import json
import os
import sys
from datetime import datetime

# 添加当前目录到Python路径，以便导入contracts
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from contracts.task_identity import TaskIdentityContract, fix_argparse_id


def audit_queue_file(queue_file_path):
    """审计队列文件中的问题ID"""
    print(f"🔍 审计队列文件: {queue_file_path}")

    if not os.path.exists(queue_file_path):
        print(f"❌ 队列文件不存在: {queue_file_path}")
        return None

    try:
        with open(queue_file_path, "r", encoding="utf-8") as f:
            queue_data = json.load(f)
    except Exception as e:
        print(f"❌ 无法加载队列文件: {e}")
        return None

    # 提取任务ID（items对象的键）
    items = queue_data.get("items", {})
    task_ids = list(items.keys())

    print(f"📊 队列统计:")
    print(f"   总任务数: {len(task_ids)}")
    print(f"   items对象类型: {type(items).__name__}")

    # 使用TaskIdentityContract审计
    contract = TaskIdentityContract()
    audit_report = contract.audit_existing_ids(task_ids)

    print(f"\n📋 审计结果:")
    print(f"   问题ID数量: {audit_report['argparse_unsafe_count']}")
    print(f"   问题ID比例: {audit_report['problematic_percentage']:.2f}%")

    if audit_report["argparse_unsafe_count"] > 0:
        print(f"\n🔴 发现的问题ID:")
        for problem in audit_report["problematic_ids"]:
            print(f"   - {problem['id'][:80]}...")

    return queue_data, audit_report


def fix_queue_ids(queue_file_path, backup=True):
    """修复队列文件中的问题ID"""
    print(f"🔧 修复队列文件: {queue_file_path}")

    # 审计当前状态
    result = audit_queue_file(queue_file_path)
    if result is None:
        return False

    queue_data, audit_report = result

    if audit_report["argparse_unsafe_count"] == 0:
        print(f"✅ 没有发现需要修复的问题ID")
        return True

    # 创建备份
    if backup:
        backup_path = queue_file_path + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        import shutil

        shutil.copy2(queue_file_path, backup_path)
        print(f"📁 已创建备份: {backup_path}")

    # 修复问题ID
    items = queue_data.get("items", {})
    problematic_ids = [p["id"] for p in audit_report["problematic_ids"]]

    print(f"\n🔄 开始修复{len(problematic_ids)}个问题ID...")

    # 构建原始ID到修复后ID的映射
    id_mapping = {}
    for raw_id in problematic_ids:
        # 使用快速修复函数
        fixed_id = fix_argparse_id(raw_id)

        # 检查修复后的ID是否与现有ID冲突
        if fixed_id in items and fixed_id != raw_id:
            # 添加后缀避免冲突
            suffix = 1
            while f"{fixed_id}_{suffix}" in items:
                suffix += 1
            fixed_id = f"{fixed_id}_{suffix}"

        id_mapping[raw_id] = fixed_id
        print(f"   {raw_id[:60]}... → {fixed_id}")

    # 更新items对象
    new_items = {}
    for old_id, task_data in items.items():
        if old_id in id_mapping:
            new_id = id_mapping[old_id]
            new_items[new_id] = task_data
        else:
            new_items[old_id] = task_data

    # 更新queue_data
    queue_data["items"] = new_items

    # 更新updated_at时间戳
    queue_data["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")

    # 保存修复后的文件
    fixed_path = queue_file_path.replace(".json", "_fixed.json")
    try:
        with open(fixed_path, "w", encoding="utf-8") as f:
            json.dump(queue_data, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 修复完成: {fixed_path}")
    except Exception as e:
        print(f"❌ 保存修复文件失败: {e}")
        return False

    # 验证修复结果
    print(f"\n🔍 验证修复结果...")
    verify_result = audit_queue_file(fixed_path)
    if verify_result is None:
        print(f"⚠️  无法验证修复结果")
        return False

    _, verify_audit = verify_result

    if verify_audit["argparse_unsafe_count"] == 0:
        print(f"✅ 验证通过: 修复后没有以'-'开头的ID")

        # 替换原始文件
        import shutil

        shutil.copy2(fixed_path, queue_file_path)
        print(f"📝 已更新原始队列文件: {queue_file_path}")

        # 保留修复后的文件供参考
        print(f"📁 修复副本保留在: {fixed_path}")

        return True
    else:
        print(f"⚠️  警告: 修复后仍有{verify_audit['argparse_unsafe_count']}个问题ID")
        print(f"📁 修复文件保留在: {fixed_path}（需要进一步处理）")
        return False


def main():
    """主函数"""
    print("=" * 70)
    print("🔧 任务ID规范化修复工具")
    print(f"   时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # 从.athena-auto-queue.json获取队列文件路径
    config_file = ".athena-auto-queue.json"
    if not os.path.exists(config_file):
        print(f"❌ 配置文件不存在: {config_file}")
        return 1

    with open(config_file, "r", encoding="utf-8") as f:
        config = json.load(f)

    routes = config.get("routes", [])

    for route in routes:
        route_id = route.get("route_id")
        manifest_path = route.get("manifest_path")
        route_name = route.get("name", route_id)

        print(f"\n📋 检查路由: {route_name} ({route_id})")
        print(f"   Manifest路径: {manifest_path}")

        if not os.path.exists(manifest_path):
            print(f"   ⚠️  Manifest文件不存在，跳过")
            continue

        # 根据manifest路径推断队列文件路径
        # 队列文件通常在.openclaw/plan_queue/目录中，名称与队列ID相关
        manifest_dir = os.path.dirname(manifest_path)
        manifest_name = os.path.basename(manifest_path)

        # 查找可能的队列文件
        queue_files = []
        if "openhuman_aiplan_priority_execution" in manifest_name:
            # 优先执行队列
            queue_files.append(
                os.path.join(manifest_dir, "openhuman_aiplan_build_priority_20260328.json")
            )

        # 如果没有找到特定文件，检查同一目录下所有.json文件
        if not queue_files:
            for file in os.listdir(manifest_dir):
                if file.endswith(".json") and not file.endswith("_deduplicated.json"):
                    queue_files.append(os.path.join(manifest_dir, file))

        for queue_file in queue_files:
            if os.path.exists(queue_file):
                print(f"\n   📂 找到队列文件: {os.path.basename(queue_file)}")

                # 审计队列文件
                audit_result = audit_queue_file(queue_file)
                if audit_result is None:
                    continue

                _, audit_report = audit_result

                if audit_report["argparse_unsafe_count"] > 0:
                    print(f"\n   🔴 发现{audit_report['argparse_unsafe_count']}个问题ID，需要修复")

                    # 询问用户是否继续修复
                    response = (
                        input(f"   是否修复{os.path.basename(queue_file)}中的问题ID？ (y/N): ")
                        .strip()
                        .lower()
                    )
                    if response == "y":
                        fix_queue_ids(queue_file)
                    else:
                        print(f"   ⏭️  跳过修复")
                else:
                    print(f"   ✅ 没有发现以'-'开头的ID，无需修复")

    print("\n" + "=" * 70)
    print("🎉 任务ID规范化检查完成")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
