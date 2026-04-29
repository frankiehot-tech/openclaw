#!/usr/bin/env python3
"""调试任务字段 - 修复版本"""

from pathlib import Path

import requests

# 读取token
TOKEN_FILE = Path("/Volumes/1TB-M2/openclaw/.openclaw/athena_web_desktop.token")
token = TOKEN_FILE.read_text().strip()

# API配置
base_url = "http://127.0.0.1:8080"
headers = {"X-OpenClaw-Token": token, "Content-Type": "application/json"}

print("🔍 调试任务字段...")

# 获取所有队列数据
response = requests.get(f"{base_url}/api/athena/queues", headers=headers, timeout=5)
if response.status_code == 200:
    data = response.json()
    routes = data.get("routes", [])

    for route in routes:
        if route.get("queue_id") == "openhuman_aiplan_gene_management_20260405":
            print("📊 找到目标队列:")
            print(f"   队列ID: {route.get('queue_id')}")
            print(f"   路由ID: {route.get('route_id')}")
            items = route.get("items", [])
            print(f"   任务总数: {len(items)}")

            # 检查每个任务的字段
            for i, item in enumerate(items):
                print(f"\n  任务 #{i + 1}:")
                print(f"    ID: {item.get('id')}")
                print(f"    task_id: {item.get('task_id', '字段不存在')}")
                print(f"    route_id: {item.get('route_id', '字段不存在')}")
                print(f"    状态: {item.get('status')}")
                title = item.get("title", "")
                print(f"    标题: {title[:50]}{'...' if len(title) > 50 else ''}")

                # 如果字段为空或不存在
                task_id_val = item.get("task_id")
                route_id_val = item.get("route_id")

                if (
                    task_id_val == ""
                    or task_id_val is None
                    or route_id_val == ""
                    or route_id_val is None
                ):
                    print(f"    ⚠️  问题字段: task_id={task_id_val}, route_id={route_id_val}")

                    # 检查所有字段
                    if i == 0:  # 只检查第一个有问题的任务
                        print("    所有字段:")
                        for key, value in sorted(item.items()):
                            print(f"      {key}: {repr(value)[:60]}")
                        break
            break
else:
    print(f"❌ 获取队列失败: {response.status_code}")

print("\n✅ 调试完成")
