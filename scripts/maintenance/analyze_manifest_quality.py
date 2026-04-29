#!/usr/bin/env python3
"""
Manifest数据质量分析工具
分析深度审计发现的24%重复条目问题
"""

import json
import os
import sys
from collections import Counter
from typing import Any


def analyze_manifest_file(file_path: str) -> dict[str, Any]:
    """分析manifest文件的数据质量"""
    print(f"🔍 分析文件: {file_path}")

    if not os.path.exists(file_path):
        return {"error": f"文件不存在: {file_path}"}

    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return {"error": f"JSON解析错误: {e}"}

    # 提取items列表
    if isinstance(data, dict) and "items" in data:
        items = data["items"]
    elif isinstance(data, list):
        items = data
    else:
        # 可能是队列文件格式
        items = []
        for _key, value in data.items():
            if isinstance(value, dict) and "id" in value:
                items.append(value)
        if not items:
            # 尝试其他结构
            items = list(data.values()) if isinstance(data, dict) else data

    print(f"📊 总条目数: {len(items)}")

    # 收集所有ID
    ids = []
    for item in items:
        if isinstance(item, dict):
            item_id = item.get("id")
            if item_id:
                ids.append(str(item_id))

    print(f"📋 有效ID数: {len(ids)}")

    # 统计重复ID
    id_counter = Counter(ids)
    duplicate_ids = {id: count for id, count in id_counter.items() if count > 1}

    print(f"🔁 重复ID数: {len(duplicate_ids)}")
    print(
        f"📈 唯一ID比例: {len(set(ids))}/{len(ids)} = {len(set(ids)) / len(ids) * 100:.1f}%"
        if ids
        else "N/A"
    )

    # 找出重复条目的详细信息
    duplicate_details = []
    for dup_id, count in duplicate_ids.items():
        dup_items = []
        for idx, item in enumerate(items):
            if isinstance(item, dict) and str(item.get("id")) == dup_id:
                dup_items.append(
                    {
                        "index": idx,
                        "title": item.get("title", "无标题"),
                        "instruction_path": item.get("instruction_path", "无路径"),
                    }
                )

        duplicate_details.append({"id": dup_id, "count": count, "items": dup_items})

    # 检查数据完整性
    completeness_stats = {
        "total_items": len(items),
        "has_id": sum(1 for item in items if isinstance(item, dict) and item.get("id")),
        "has_title": sum(1 for item in items if isinstance(item, dict) and item.get("title")),
        "has_instruction_path": sum(
            1 for item in items if isinstance(item, dict) and item.get("instruction_path")
        ),
        "has_entry_stage": sum(
            1 for item in items if isinstance(item, dict) and item.get("entry_stage")
        ),
    }

    return {
        "file_path": file_path,
        "total_entries": len(items),
        "total_ids": len(ids),
        "unique_ids": len(set(ids)),
        "duplicate_ids_count": len(duplicate_ids),
        "duplicate_details": duplicate_details,
        "completeness": completeness_stats,
        "duplicate_percentage": len(duplicate_ids) / len(ids) * 100 if ids else 0,
        "sample_duplicates": duplicate_details[:5],  # 只显示前5个重复
    }


def analyze_gene_management_manifest():
    """分析基因管理队列manifest"""
    file_path = "/Volumes/1TB-M2/openclaw/scripts/gene_management_queue_manifest.json"
    return analyze_manifest_file(file_path)


def analyze_priority_execution_queue():
    """分析优先执行队列文件"""
    file_path = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_priority_execution_20260414.json"
    return analyze_manifest_file(file_path)


def main():
    print("🧪 Manifest数据质量分析工具")
    print("=" * 60)
    print("基于深度审计结果：24%重复条目，数据不一致")
    print("=" * 60)

    # 分析两个主要文件
    print("\n1. 分析基因管理队列manifest:")
    result1 = analyze_gene_management_manifest()

    if "error" in result1:
        print(f"   ❌ 错误: {result1['error']}")
    else:
        print(f"   ✅ 总条目: {result1['total_entries']}")
        print(f"   📊 有效ID: {result1['total_ids']}")
        print(f"   🔄 唯一ID: {result1['unique_ids']}")
        print(f"   🔁 重复ID: {result1['duplicate_ids_count']}")
        print(f"   📈 重复比例: {result1['duplicate_percentage']:.1f}%")

        if result1["duplicate_details"]:
            print(f"   📋 重复详情（前{len(result1['sample_duplicates'])}个）:")
            for dup in result1["sample_duplicates"]:
                print(f"      ID: {dup['id']}, 重复次数: {dup['count']}")
                for item in dup["items"][:2]:  # 只显示前2个重复项
                    print(f"        - 索引{item['index']}: {item['title'][:50]}...")

    print("\n2. 分析优先执行队列文件:")
    result2 = analyze_priority_execution_queue()

    if "error" in result2:
        print(f"   ❌ 错误: {result2['error']}")
    else:
        print(f"   ✅ 总条目: {result2['total_entries']}")
        print(f"   📊 有效ID: {result2['total_ids']}")
        print(f"   🔄 唯一ID: {result2['unique_ids']}")
        print(f"   🔁 重复ID: {result2['duplicate_ids_count']}")
        print(f"   📈 重复比例: {result2['duplicate_percentage']:.1f}%")

        if result2["duplicate_details"]:
            print(f"   📋 重复详情（前{len(result2['sample_duplicates'])}个）:")
            for dup in result2["sample_duplicates"]:
                print(f"      ID: {dup['id']}, 重复次数: {dup['count']}")
                for item in dup["items"][:2]:
                    print(f"        - 索引{item['index']}: {item['title'][:50]}...")

    # 数据完整性分析
    print("\n3. 数据完整性分析:")
    for result, name in [(result1, "基因管理manifest"), (result2, "优先执行队列")]:
        if "error" not in result and "completeness" in result:
            comp = result["completeness"]
            print(f"\n   📋 {name}:")
            print(f"      总条目: {comp['total_items']}")
            print(
                f"      有ID: {comp['has_id']} ({comp['has_id'] / comp['total_items'] * 100:.1f}%)"
            )
            print(
                f"      有标题: {comp['has_title']} ({comp['has_title'] / comp['total_items'] * 100:.1f}%)"
            )
            print(
                f"      有指令路径: {comp['has_instruction_path']} ({comp['has_instruction_path'] / comp['total_items'] * 100:.1f}%)"
            )
            print(
                f"      有入口阶段: {comp['has_entry_stage']} ({comp['has_entry_stage'] / comp['total_items'] * 100:.1f}%)"
            )

    print("\n" + "=" * 60)
    print("📊 分析完成")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
