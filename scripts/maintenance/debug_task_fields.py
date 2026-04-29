#!/usr/bin/env python3
"""调试任务字段，找出为什么task_id和route_id为空"""

from pathlib import Path

import requests

# 读取token
TOKEN_FILE = Path("/Volumes/1TB-M2/openclaw/.openclaw/athena_web_desktop.token")
token = TOKEN_FILE.read_text().strip()

# API配置
base_url = "http://127.0.0.1:8080"
headers = {"X-OpenClaw-Token": token, "Content-Type": "application/json"}

print("🔍 调试任务字段...")

# 获取队列数据
response = requests.get(
    f"{base_url}/api/athena/queues/openhuman_aiplan_gene_management_20260405",
    headers=headers,
    timeout=5,
)
if response.status_code == 200:
    data = response.json()
    items = data.get("items", [])

    print(f"📊 队列: {data.get('queue_id')}")
    print(f"   路由ID: {data.get('route_id')}")
    print(f"   任务总数: {len(items)}")

    # 检查每个任务的字段
    for i, item in enumerate(items):
        print(f"\n  任务 #{i + 1}:")
        print(f"    ID: {item.get('id')}")
        print(f"    task_id: {item.get('task_id')}")
        print(f"    route_id: {item.get('route_id')}")
        print(f"    状态: {item.get('status')}")
        print(f"    标题: {item.get('title', '')[:50]}...")

        # 检查是否缺少字段
        if item.get("task_id") == "" or item.get("route_id") == "":
            print("    ⚠️  空字段!")

            # 打印所有字段
            print("    所有字段:")
            for key, value in item.items():
                print(f"      {key}: {repr(value)[:60]}")

            # 如果是第一个空字段任务，深入检查
            break
else:
    print(f"❌ 获取队列失败: {response.status_code}")

# 测试手动拉起API使用正确的字段
print("\n🚀 测试手动拉起API...")

# 查找一个pending或failed的任务，且有非空的task_id和route_id
for item in items:
    status = item.get("status")
    task_id = item.get("task_id")
    route_id = item.get("route_id")

    if status in ["pending", "failed"] and task_id and route_id:
        print("  找到可拉起任务:")
        print(f"    任务ID: {task_id}")
        print(f"    路由ID: {route_id}")
        print(f"    状态: {status}")
        print(f"    标题: {item.get('title', '')}")

        # 测试手动拉起
        launch_url = f"{base_url}/api/athena/queues/items/{route_id}/{task_id}/launch"
        print(f"    🚀 调用API: POST {launch_url}")

        try:
            launch_response = requests.post(launch_url, headers=headers, timeout=10)
            print(f"      状态码: {launch_response.status_code}")
            print(f"      响应: {launch_response.text}")
            break
        except Exception as e:
            print(f"      ❌ 请求失败: {e}")
            break
else:
    print("  没有找到合适的任务进行测试")

print("\n✅ 调试完成")
