#!/usr/bin/env python3
"""调试队列任务项结构"""

import json
from pathlib import Path

import requests

# 读取token
TOKEN_FILE = Path("/Volumes/1TB-M2/openclaw/.openclaw/athena_web_desktop.token")
token = TOKEN_FILE.read_text().strip()

# API配置
base_url = "http://127.0.0.1:8080"
headers = {"X-OpenClaw-Token": token}

print("🔍 调试队列任务项结构...")

# 获取队列数据
response = requests.get(f"{base_url}/api/athena/queues", headers=headers, timeout=5)
if response.status_code == 200:
    data = response.json()
    routes = data.get("routes", [])

    for route in routes:
        queue_id = route.get("queue_id")
        print(f"\n📊 队列: {queue_id}")
        print(f"   状态: {route.get('queue_status')}")
        print(f"   任务数: {len(route.get('items', []))}")

        # 检查前几个任务项
        items = route.get("items", [])
        if items:
            print(f"\n   第一个任务项的结构:")
            first_item = items[0]
            for key, value in first_item.items():
                print(f"     {key}: {repr(value)[:80]}")

            # 检查是否有route_id和task_id字段
            missing_fields = []
            if "route_id" not in first_item:
                missing_fields.append("route_id")
            if "task_id" not in first_item:
                missing_fields.append("task_id")

            if missing_fields:
                print(f"\n   ⚠️ 缺失字段: {missing_fields}")

                # 查看所有任务项中是否有这些字段
                for item in items:
                    if "route_id" in item or "task_id" in item:
                        print(f"   ✅ 有些任务项包含这些字段")
                        break
                else:
                    print(f"   ❌ 所有任务项都缺失这些字段")

            # 检查手动拉起所需的字段
            print(f"\n   🚀 手动拉起所需字段:")
            print(f"     任务ID字段: {first_item.get('id', '未找到')}")
            print(f"     路由ID字段: 未在任务项中找到，可能在队列级别")

            # 队列级别的route_id
            route_id = route.get("route_id", "")
            print(f"     队列route_id: {route_id}")
else:
    print(f"❌ 获取队列失败: {response.status_code}")

# 检查athena_web_desktop_compat.py中的queue_item_from_manifest函数
print(f"\n🔧 检查queue_item_from_manifest函数...")
compat_file = Path("/Volumes/1TB-M2/openclaw/scripts/athena_web_desktop_compat.py")
if compat_file.exists():
    with open(compat_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 查找queue_item_from_manifest函数定义
    import re

    func_match = re.search(
        r"def queue_item_from_manifest\([^)]+\)[^:]+:(.*?)def ", content, re.DOTALL
    )
    if func_match:
        func_body = func_match.group(1)
        return_match = re.search(r"return \{([^}]+(?:\{[^}]*\}[^}]*)*)\}", func_body, re.DOTALL)
        if return_match:
            return_dict = return_match.group(1)
            lines = return_dict.strip().split("\n")
            print(f"   函数返回的字段:")
            for line in lines:
                line = line.strip()
                if ":" in line:
                    key = line.split(":")[0].strip().strip("\"'")
                    print(f"     - {key}")

            # 检查是否有route_id和task_id
            if '"route_id"' not in return_dict and "'route_id'" not in return_dict:
                print(f"   ⚠️ 返回字典中没有route_id字段")
            if '"task_id"' not in return_dict and "'task_id'" not in return_dict:
                print(f"   ⚠️ 返回字典中没有task_id字段")

print(f"\n✅ 调试完成")
