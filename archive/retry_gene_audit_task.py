#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py task <command>
"""重试gene_mgmt_audit任务"""

import json
from pathlib import Path

import requests

# 读取token
TOKEN_FILE = Path("/Volumes/1TB-M2/openclaw/.openclaw/athena_web_desktop.token")
token = TOKEN_FILE.read_text().strip()

# API配置
base_url = "http://127.0.0.1:8080"
headers = {"X-OpenClaw-Token": token, "Content-Type": "application/json"}

print("🔄 重试gene_mgmt_audit任务...")

# 首先获取队列状态
response = requests.get(f"{base_url}/api/athena/queues", headers=headers, timeout=5)
if response.status_code != 200:
    print(f"❌ 获取队列失败: {response.status_code}")
    print(f"响应: {response.text}")
    exit(1)

data = response.json()
routes = data.get("routes", [])

target_queue = None
target_route_id = None

for route in routes:
    if route.get("queue_id") == "openhuman_aiplan_gene_management_20260405":
        target_queue = route
        target_route_id = route.get("route_id")
        break

if not target_queue:
    print("❌ 未找到基因管理队列")
    exit(1)

print("📊 找到队列:")
print(f"   队列ID: {target_queue.get('queue_id')}")
print(f"   路由ID: {target_route_id}")
print(f"   队列状态: {target_queue.get('queue_status')}")

# 查找gene_mgmt_audit任务
items = target_queue.get("items", [])
target_item = None

for item in items:
    if item.get("id") == "gene_mgmt_audit":
        target_item = item
        break

if not target_item:
    print("❌ 未找到gene_mgmt_audit任务")
    # 列出所有任务
    print("可用的任务:")
    for i, item in enumerate(items):
        print(f"  {i + 1}. ID: {item.get('id')}, 状态: {item.get('status')}")
    exit(1)

print("📋 找到任务:")
print(f"   ID: {target_item.get('id')}")
print(f"   标题: {target_item.get('title')}")
print(f"   状态: {target_item.get('status')}")
print(f"   错误: {target_item.get('error', '无')}")

# 重试任务API
# 根据之前观察，重试API端点是: /api/athena/queues/items/{route_id}/{task_id}/retry
task_id = target_item.get("id")

print("\n🔄 调用重试API...")
retry_url = f"{base_url}/api/athena/queues/items/{target_route_id}/{task_id}/retry"
print(f"   重试URL: {retry_url}")

retry_response = requests.post(retry_url, headers=headers, timeout=10)
print(f"   响应状态码: {retry_response.status_code}")

if retry_response.status_code == 200:
    print("✅ 重试成功!")
    retry_data = retry_response.json()
    print(f"   响应: {json.dumps(retry_data, indent=2, ensure_ascii=False)}")
else:
    print("❌ 重试失败")
    print(f"   响应: {retry_response.text}")

# 等待几秒后检查状态
print("\n⏳ 等待3秒后检查任务状态...")
import time

time.sleep(3)

# 重新获取队列状态
response2 = requests.get(f"{base_url}/api/athena/queues", headers=headers, timeout=5)
if response2.status_code == 200:
    data2 = response2.json()
    for route in data2.get("routes", []):
        if route.get("queue_id") == "openhuman_aiplan_gene_management_20260405":
            items2 = route.get("items", [])
            for item in items2:
                if item.get("id") == "gene_mgmt_audit":
                    print("📊 更新后的任务状态:")
                    print(f"   状态: {item.get('status')}")
                    print(f"   进度: {item.get('progress_percent', 0)}%")
                    print(f"   错误: {item.get('error', '无')}")
                    break
            break

print("\n✅ 脚本执行完成")
