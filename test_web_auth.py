#!/usr/bin/env python3
"""测试Web API认证问题"""

import json
from pathlib import Path

import requests

# 读取token
TOKEN_FILE = Path("/Volumes/1TB-M2/openclaw/.openclaw/athena_web_desktop.token")
if TOKEN_FILE.exists():
    token = TOKEN_FILE.read_text().strip()
    print(f"✅ Token文件存在: {TOKEN_FILE}")
    print(f"📄 Token值: {token}")
else:
    print(f"❌ Token文件不存在: {TOKEN_FILE}")
    token = ""

# API端点
base_url = "http://127.0.0.1:8080"
headers = {"X-OpenClaw-Token": token}

# 测试端点
test_endpoints = [
    "/api/athena/queues",
    "/api/athena/queues/openhuman_aiplan_gene_management_20260405",
]

print(f"\n🔧 测试Web API认证...")
print(f"🌐 基础URL: {base_url}")
print(f"🔑 认证头: X-OpenClaw-Token: {token[:10]}...")

for endpoint in test_endpoints:
    url = base_url + endpoint
    print(f"\n📡 测试端点: {endpoint}")

    # 不带token测试
    print("  1. 不带token测试...")
    try:
        response = requests.get(url, timeout=5)
        print(f"     状态码: {response.status_code}")
        if response.status_code == 200:
            print(f"     响应: {response.text[:100]}...")
        elif response.status_code == 401:
            print(f"     响应: {response.text}")
        else:
            print(f"     响应: {response.text}")
    except Exception as e:
        print(f"     ❌ 请求失败: {e}")

    # 带token测试
    print("  2. 带token测试...")
    try:
        response = requests.get(url, headers=headers, timeout=5)
        print(f"     状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"     ✅ 认证成功!")
            print(f"     响应keys: {list(data.keys())}")
            if "queue_status" in data:
                print(f"     队列状态: {data.get('queue_status')}")
                print(f"     任务统计: {data.get('statistics', {})}")
        elif response.status_code == 401:
            print(f"     ❌ 认证失败: {response.text}")
        else:
            print(f"     响应: {response.text[:200]}...")
    except Exception as e:
        print(f"     ❌ 请求失败: {e}")

# 测试手动拉起端点（需要正确的参数格式）
print(f"\n🔧 测试手动拉起端点...")
print("💡 注意: 手动拉起端点需要POST请求和正确的route_id/task_id参数")

# 首先获取基因管理队列的状态，以获取任务信息
queue_url = base_url + "/api/athena/queues/openhuman_aiplan_gene_management_20260405"
try:
    response = requests.get(queue_url, headers=headers, timeout=5)
    if response.status_code == 200:
        queue_data = response.json()
        items = queue_data.get("items", [])
        if items:
            # 找到一个pending或failed的任务
            for item in items:
                if item.get("status") in ["pending", "failed"]:
                    route_id = item.get("route_id", "")
                    task_id = item.get("task_id", "")
                    if route_id and task_id:
                        print(f"\n🎯 找到可测试的任务:")
                        print(f"   路由ID: {route_id}")
                        print(f"   任务ID: {task_id}")
                        print(f"   状态: {item.get('status')}")
                        print(f"   标题: {item.get('title', '')}")

                        # 测试手动拉起
                        launch_url = (
                            f"{base_url}/api/athena/queues/items/{route_id}/{task_id}/launch"
                        )
                        print(f"   🚀 测试手动拉起: POST {launch_url}")

                        try:
                            launch_response = requests.post(launch_url, headers=headers, timeout=5)
                            print(f"     状态码: {launch_response.status_code}")
                            print(f"     响应: {launch_response.text}")
                        except Exception as e:
                            print(f"     ❌ 请求失败: {e}")
                        break
        else:
            print("ℹ️  队列中没有找到pending或failed的任务")
    else:
        print(f"❌ 无法获取队列状态: {response.status_code}")
except Exception as e:
    print(f"❌ 获取队列失败: {e}")

print(f"\n✅ 测试完成")
