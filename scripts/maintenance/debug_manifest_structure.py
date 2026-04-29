#!/usr/bin/env python3
"""
调试manifest数据结构
"""

import json

input_path = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_priority_execution_20260414.json"

print(f"分析文件结构: {input_path}")

with open(input_path, encoding="utf-8") as f:
    data = json.load(f)

print(f"数据根类型: {type(data)}")

if isinstance(data, dict):
    print(f"字典键: {list(data.keys())}")
    if "items" in data:
        items = data["items"]
        print(f"items类型: {type(items)}, 长度: {len(items) if isinstance(items, list) else 'N/A'}")

        # 检查前5个条目的类型
        for i in range(min(5, len(items))):
            item = items[i]
            print(f"  条目 {i}: 类型={type(item)}")
            if isinstance(item, dict):
                print(f"      键: {list(item.keys())[:10]}...")
                print(f"      id值: {item.get('id', '无id')}")
            else:
                print(f"      值: {str(item)[:100]}...")
else:
    print(f"数据内容: {str(data)[:200]}...")
