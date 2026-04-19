#!/usr/bin/env python3
"""
修复问题任务ID脚本 - 直接修复openhuman_aiplan_build_priority_20260328.json中的问题ID
基于深度审计发现：13个以'-'开头的任务ID需要规范化
"""

import json
import os
import shutil
import sys
from datetime import datetime


def load_queue_file(file_path):
    """加载队列文件"""
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 加载文件失败: {e}")
        return None


def find_problematic_ids(queue_data):
    """查找以'-'开头的任务ID"""
    items = queue_data.get("items", {})

    problematic_ids = []
    for task_id in items.keys():
        if task_id.startswith("-"):
            problematic_ids.append(task_id)

    return problematic_ids


def fix_argparse_id(raw_id):
    """快速修复函数：将可能被argparse误识别的ID转换为安全格式"""
    if raw_id.startswith("-"):
        # 简单修复：添加'task_'前缀
        return "task_" + raw_id[1:]
    return raw_id


def fix_queue_file(queue_file_path):
    """修复队列文件中的问题ID"""
    print(f"🔧 修复队列文件: {queue_file_path}")

    # 加载队列数据
    queue_data = load_queue_file(queue_file_path)
    if queue_data is None:
        return False

    items = queue_data.get("items", {})

    # 查找问题ID
    problematic_ids = find_problematic_ids(queue_data)

    if not problematic_ids:
        print(f"✅ 没有发现以'-'开头的ID，无需修复")
        return True

    print(f"📊 发现{len(problematic_ids)}个问题ID:")
    for pid in problematic_ids:
        print(f"   - {pid[:80]}...")

    # 创建备份
    backup_path = queue_file_path + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(queue_file_path, backup_path)
    print(f"📁 已创建备份: {backup_path}")

    # 构建ID映射
    id_mapping = {}
    for old_id in problematic_ids:
        # 使用快速修复函数
        new_id = fix_argparse_id(old_id)

        # 检查新ID是否与现有ID冲突
        original_new_id = new_id
        suffix = 1
        while new_id in items and new_id != old_id:
            new_id = f"{original_new_id}_{suffix}"
            suffix += 1

        id_mapping[old_id] = new_id
        print(f"   {old_id[:60]}... → {new_id}")

    # 创建新的items对象
    new_items = {}
    for old_id, task_data in items.items():
        if old_id in id_mapping:
            new_items[id_mapping[old_id]] = task_data
        else:
            new_items[old_id] = task_data

    # 更新queue_data
    queue_data["items"] = new_items
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
    verify_data = load_queue_file(fixed_path)
    if verify_data is None:
        print(f"⚠️  无法验证修复结果")
        return False

    remaining_problems = find_problematic_ids(verify_data)
    if not remaining_problems:
        print(f"✅ 验证通过: 修复后没有以'-'开头的ID")

        # 替换原始文件
        shutil.copy2(fixed_path, queue_file_path)
        print(f"📝 已更新原始队列文件: {queue_file_path}")

        # 保留修复后的文件供参考
        print(f"📁 修复副本保留在: {fixed_path}")
        return True
    else:
        print(f"⚠️  警告: 修复后仍有{len(remaining_problems)}个问题ID")
        for pid in remaining_problems:
            print(f"   - {pid[:80]}...")
        print(f"📁 修复文件保留在: {fixed_path}（需要进一步处理）")
        return False


def main():
    """主函数"""
    print("=" * 70)
    print("🔧 问题任务ID修复脚本")
    print(f"   时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # 直接修复审计报告中提到的文件
    queue_file = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"

    if not os.path.exists(queue_file):
        print(f"❌ 队列文件不存在: {queue_file}")

        # 查找可能的队列文件
        plan_queue_dir = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue"
        if os.path.exists(plan_queue_dir):
            print(f"\n🔍 在目录中查找队列文件: {plan_queue_dir}")
            queue_files = []
            for file in os.listdir(plan_queue_dir):
                if file.endswith(".json") and "priority" in file.lower():
                    queue_files.append(os.path.join(plan_queue_dir, file))

            if queue_files:
                print(f"   找到{len(queue_files)}个可能的队列文件:")
                for qf in queue_files:
                    print(f"   - {os.path.basename(qf)}")

                # 使用第一个文件
                queue_file = queue_files[0]
                print(f"\n📋 将使用文件: {queue_file}")
            else:
                print(f"❌ 没有找到优先级队列文件")
                return 1

    # 检查文件
    print(f"\n📋 目标文件: {queue_file}")

    # 加载并显示问题ID
    queue_data = load_queue_file(queue_file)
    if queue_data is None:
        return 1

    problematic_ids = find_problematic_ids(queue_data)

    if not problematic_ids:
        print(f"✅ 没有发现以'-'开头的ID")
        print(f"\n⚠️  注意: 审计报告显示有13个问题ID，但当前文件中未发现")
        print(f"   可能的原因:")
        print(f"   1. 问题已在审计后被修复")
        print(f"   2. 审计分析的是不同的文件版本")
        print(f"   3. 问题ID在其他文件中")
        return 0

    print(f"\n🔍 发现{len(problematic_ids)}个以'-'开头的ID:")
    for i, pid in enumerate(problematic_ids, 1):
        print(f"   {i:2d}. {pid}")

    # 询问用户是否修复
    response = input(f"\n🔧 是否修复这些{len(problematic_ids)}个问题ID？ (y/N): ").strip().lower()
    if response != "y":
        print(f"⏭️  跳过修复")
        return 0

    # 执行修复
    success = fix_queue_file(queue_file)

    print("\n" + "=" * 70)
    if success:
        print("🎉 任务ID修复完成")
    else:
        print("⚠️  任务ID修复遇到问题")
    print("=" * 70)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
