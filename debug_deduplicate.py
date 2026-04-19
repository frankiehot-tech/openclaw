#!/usr/bin/env python3
"""
调试deduplicate_manifest错误
"""

import sys

sys.path.insert(0, "/Volumes/1TB-M2/openclaw")

from contracts.data_quality import DataQualityContract, deduplicate_manifest

input_path = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_priority_execution_20260414.json"
output_path = input_path.replace(".json", "_test_deduplicated.json")

print(f"调试: {input_path}")

# 直接调用save_deduplicated_manifest看看错误
try:
    contract = DataQualityContract(input_path)
    if contract.load_manifest():
        print(f"加载成功，items数量: {len(contract.items) if contract.items else 0}")

        # 检查items类型
        if contract.items:
            for i, item in enumerate(contract.items[:3]):
                print(f"   item {i}: type={type(item)}, value={str(item)[:100]}")

        # 尝试去重
        print("尝试调用save_deduplicated_manifest...")
        success = contract.save_deduplicated_manifest(output_path, "keep_first")
        print(f"结果: {success}")
    else:
        print("加载失败")
except Exception as e:
    print(f"错误: {type(e).__name__}: {str(e)}")
    import traceback

    traceback.print_exc()
