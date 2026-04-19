#!/usr/bin/env python3
"""
Manifest重复条目清理工具
使用DataQualityContract清理实际manifest文件中的重复条目
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, "/Volumes/1TB-M2/openclaw")

from contracts.data_quality import DataQualityContract, deduplicate_manifest


def cleanup_priority_execution_manifest():
    """清理优先执行队列manifest"""
    input_path = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_priority_execution_20260414.json"
    output_path = input_path.replace(".json", "_deduplicated.json")

    print("🧹 清理优先执行队列manifest重复条目")
    print("=" * 60)
    print(f"输入文件: {input_path}")
    print(f"输出文件: {output_path}")

    # 检查文件是否存在
    if not os.path.exists(input_path):
        print(f"❌ 文件不存在: {input_path}")
        return False

    # 运行去重
    success = deduplicate_manifest(input_path, output_path, strategy="keep_first")

    if success:
        # 验证去重结果
        with open(input_path, "r", encoding="utf-8") as f:
            original_data = json.load(f)
        original_items = original_data.get("items", [])

        with open(output_path, "r", encoding="utf-8") as f:
            deduped_data = json.load(f)
        deduped_items = deduped_data.get("items", [])

        print(f"\n📊 去重结果:")
        print(f"   原始条目数: {len(original_items)}")
        print(f"   去重后条目数: {len(deduped_items)}")
        print(f"   移除重复数: {len(original_items) - len(deduped_items)}")

        # 验证ID唯一性
        deduped_ids = [item.get("id") for item in deduped_items if isinstance(item, dict)]
        unique_ids = len(set(deduped_ids))
        if len(deduped_ids) == unique_ids:
            print(f"   ✅ 所有ID唯一，去重成功")
        else:
            print(f"   ⚠️  仍有重复ID: {len(deduped_ids)} ID中{unique_ids}个唯一")

        # 生成去重报告文件路径
        report_path = output_path.replace(".json", "_deduplication_report.json")
        if os.path.exists(report_path):
            with open(report_path, "r", encoding="utf-8") as f:
                report = json.load(f)
            print(f"\n📋 去重报告:")
            print(f"   策略: {report.get('strategy', 'unknown')}")
            print(f"   移除重复: {report.get('duplicates_removed', 0)}")
            print(f"   保留条目: {report.get('total_after', 0)}")

        return True
    else:
        print(f"❌ 去重失败")
        return False


def cleanup_gene_management_manifest():
    """清理基因管理队列manifest"""
    input_path = "/Volumes/1TB-M2/openclaw/scripts/gene_management_queue_manifest.json"
    output_path = input_path.replace(".json", "_deduplicated.json")

    print("\n🧹 清理基因管理队列manifest重复条目")
    print("=" * 60)
    print(f"输入文件: {input_path}")
    print(f"输出文件: {output_path}")

    # 检查文件是否存在
    if not os.path.exists(input_path):
        print(f"⚠️  文件不存在: {input_path}")
        print(f"   跳过基因管理队列清理")
        return True  # 不视为失败

    # 运行去重
    success = deduplicate_manifest(input_path, output_path, strategy="keep_first")

    if success:
        # 检查输出文件是否存在（可能没有重复，所以没有创建）
        if os.path.exists(output_path):
            # 验证去重结果
            with open(input_path, "r", encoding="utf-8") as f:
                original_data = json.load(f)

            # 处理不同的文件格式
            if isinstance(original_data, dict) and "items" in original_data:
                original_items = original_data.get("items", [])
            elif isinstance(original_data, list):
                original_items = original_data
            else:
                print(f"⚠️  无法解析输入文件格式，跳过验证")
                return True

            with open(output_path, "r", encoding="utf-8") as f:
                deduped_data = json.load(f)

            deduped_items = deduped_data.get("items", [])

            print(f"\n📊 去重结果:")
            print(f"   原始条目数: {len(original_items)}")
            print(f"   去重后条目数: {len(deduped_items)}")
            print(f"   移除重复数: {len(original_items) - len(deduped_items)}")
        else:
            print(f"ℹ️  没有重复条目，输出文件未创建")
            print(f"   原始文件已经是最佳状态")

        return True
    else:
        print(f"❌ 去重失败")
        return False


def backup_original_files():
    """备份原始文件"""
    print("\n💾 备份原始文件")
    print("=" * 60)

    files_to_backup = [
        "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_priority_execution_20260414.json",
        "/Volumes/1TB-M2/openclaw/scripts/gene_management_queue_manifest.json",
    ]

    for file_path in files_to_backup:
        if os.path.exists(file_path):
            backup_path = file_path + ".backup"
            import shutil

            shutil.copy2(file_path, backup_path)
            print(f"   ✅ 备份: {file_path} → {backup_path}")
        else:
            print(f"   ⚠️  文件不存在，跳过备份: {file_path}")

    return True


def generate_summary_report():
    """生成清理总结报告"""
    print("\n📋 清理总结报告")
    print("=" * 60)

    # 检查输出文件
    output_files = [
        (
            "优先执行队列",
            "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_priority_execution_20260414_deduplicated.json",
        ),
        (
            "基因管理队列",
            "/Volumes/1TB-M2/openclaw/scripts/gene_management_queue_manifest_deduplicated.json",
        ),
    ]

    for name, path in output_files:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            item_count = len(data.get("items", []))
            print(f"   {name}: {item_count}个条目")
        else:
            print(f"   {name}: 文件未生成")

    print("\n✅ 清理完成！")
    print(f"   建议: 使用清理后的文件替换原始文件")
    print(f"   注意: 原始文件已备份为.backup文件")

    return True


def main():
    """主清理函数"""
    print("🧹 Manifest重复条目清理工具")
    print("=" * 60)
    print("目标: 清理24%重复条目，解决Manifest数据质量缺陷")
    print("=" * 60)

    # 1. 备份原始文件
    backup_original_files()

    # 2. 清理优先执行队列
    success1 = cleanup_priority_execution_manifest()

    # 3. 清理基因管理队列
    success2 = cleanup_gene_management_manifest()

    # 4. 生成总结报告
    generate_summary_report()

    # 5. 总体结果
    overall_success = success1 and success2

    print("\n" + "=" * 60)
    if overall_success:
        print("✅ 清理任务完成")
        print("🔧 已解决: Manifest数据质量缺陷（24%重复条目）")
        print("📈 质量改进: 数据一致性提升，重复率降低")
    else:
        print("⚠️  清理任务部分完成")
        print("🔧 部分解决了Manifest数据质量缺陷")

    return 0 if overall_success else 1


if __name__ == "__main__":
    sys.exit(main())
