#!/usr/bin/env python3
"""
详细调试deduplicate错误
"""

import sys

sys.path.insert(0, "/Volumes/1TB-M2/openclaw")

from contracts.data_quality import DataQualityContract

input_path = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_priority_execution_20260414.json"

print(f"调试: {input_path}")

contract = DataQualityContract(input_path)
if contract.load_manifest():
    print(f"加载成功，items数量: {len(contract.items)}")

    # 检查所有items的data字段类型
    for i, item in enumerate(contract.items):
        if hasattr(item, "data") and not isinstance(item.data, dict):
            print(f"警告: item {i} (id={item.id}) data类型为 {type(item.data)}")
            print(f"      data值: {str(item.data)[:200]}")
            break
    else:
        print("所有item.data都是字典类型")

    # 尝试调用deduplicate
    print("\n尝试调用deduplicate...")
    try:
        deduplicated_items, dedup_report = contract.deduplicate(strategy="keep_first")
        print(f"deduplicate成功: {len(deduplicated_items)}个条目")
    except Exception as e:
        print(f"deduplicate错误: {type(e).__name__}: {str(e)}")
        import traceback

        traceback.print_exc()

        # 尝试手动分析重复
        print("\n尝试手动分析重复...")
        try:
            duplicate_report = contract.analyze_duplicates()
            print(
                f"analyze_duplicates成功: {duplicate_report.get('duplicate_ids_count', 0)}个重复ID"
            )
        except Exception as e2:
            print(f"analyze_duplicates也失败: {type(e2).__name__}: {str(e2)}")
            traceback.print_exc()
else:
    print("加载失败")
