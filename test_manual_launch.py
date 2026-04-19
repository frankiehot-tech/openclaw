#!/usr/bin/env python3
"""测试手动拉起功能"""

import json
from pathlib import Path

import requests

# 读取token
TOKEN_FILE = Path("/Volumes/1TB-M2/openclaw/.openclaw/athena_web_desktop.token")
token = TOKEN_FILE.read_text().strip()

# API配置
base_url = "http://127.0.0.1:8080"
headers = {"X-OpenClaw-Token": token, "Content-Type": "application/json"}

print(f"🔑 Token: {token[:10]}...")
print(f"🌐 基础URL: {base_url}")

# 1. 获取所有队列信息
print("\n📋 步骤1: 获取所有队列信息...")
queues_url = base_url + "/api/athena/queues"
try:
    response = requests.get(queues_url, headers=headers, timeout=5)
    if response.status_code == 200:
        queues_data = response.json()
        routes = queues_data.get("routes", [])
        print(f"✅ 获取到 {len(routes)} 个队列")

        # 2. 查找基因管理队列
        gene_queue = None
        for route in routes:
            if route.get("queue_id") == "openhuman_aiplan_gene_management_20260405":
                gene_queue = route
                break

        if gene_queue:
            print(f"🎯 找到基因管理队列:")
            print(f"   队列ID: {gene_queue.get('queue_id')}")
            print(f"   队列状态: {gene_queue.get('queue_status')}")
            print(f"   暂停原因: {gene_queue.get('pause_reason')}")
            print(f"   任务总数: {sum(gene_queue.get('counts', {}).values())}")

            # 显示任务统计
            counts = gene_queue.get("counts", {})
            print(
                f"   任务统计: pending={counts.get('pending', 0)}, running={counts.get('running', 0)}, completed={counts.get('completed', 0)}, failed={counts.get('failed', 0)}, manual_hold={counts.get('manual_hold', 0)}"
            )

            # 3. 查找可手动拉起的任务
            items = gene_queue.get("items", [])
            launchable_items = []
            for item in items:
                status = item.get("status")
                if status in ["pending", "failed"]:
                    launchable_items.append(item)

            print(f"\n🚀 步骤2: 查找可手动拉起的任务...")
            print(f"   总共 {len(items)} 个任务，其中 {len(launchable_items)} 个可手动拉起")

            if launchable_items:
                # 测试第一个可拉起的任务
                test_item = launchable_items[0]
                route_id = test_item.get("route_id", "")
                task_id = test_item.get("task_id", "")

                print(f"\n🧪 步骤3: 测试手动拉起任务...")
                print(f"   任务ID: {task_id}")
                print(f"   路由ID: {route_id}")
                print(f"   状态: {test_item.get('status')}")
                print(f"   标题: {test_item.get('title', '')}")

                # 4. 测试手动拉起
                launch_url = f"{base_url}/api/athena/queues/items/{route_id}/{task_id}/launch"
                print(f"   🚀 调用手动拉起API: POST {launch_url}")

                try:
                    launch_response = requests.post(launch_url, headers=headers, timeout=10)
                    print(f"     状态码: {launch_response.status_code}")
                    print(f"     响应: {launch_response.text}")

                    if launch_response.status_code == 200:
                        result = launch_response.json()
                        if result.get("ok"):
                            print(f"     ✅ 手动拉起成功!")
                            print(f"     消息: {result.get('message', '')}")
                        else:
                            print(f"     ⚠️ 手动拉起返回成功状态但ok为false")
                            print(f"     错误: {result.get('error', '')}")
                    elif launch_response.status_code == 401:
                        print(f"     ❌ 认证失败: 401 Unauthorized")
                    elif launch_response.status_code == 404:
                        print(f"     ❌ 端点不存在: 404 Not Found")
                    else:
                        print(f"     ⚠️ 其他错误: {launch_response.status_code}")

                except Exception as e:
                    print(f"     ❌ 请求失败: {e}")
            else:
                print("ℹ️ 没有可手动拉起的任务（pending或failed状态）")

                # 显示所有任务状态供参考
                print("\n📊 所有任务状态:")
                status_counts = {}
                for item in items:
                    status = item.get("status", "unknown")
                    status_counts[status] = status_counts.get(status, 0) + 1
                for status, count in status_counts.items():
                    print(f"   {status}: {count}个")
        else:
            print("❌ 未找到基因管理队列")
    else:
        print(f"❌ 获取队列失败: 状态码 {response.status_code}")
        print(f"   响应: {response.text}")

except Exception as e:
    print(f"❌ 请求异常: {e}")

# 5. 测试重试失败任务端点
print("\n🔄 步骤4: 测试重试失败任务端点...")
retry_url = base_url + "/api/athena/queues/retry-failed"
try:
    retry_response = requests.post(retry_url, headers=headers, timeout=10)
    print(f"   状态码: {retry_response.status_code}")
    print(f"   响应: {retry_response.text}")

    if retry_response.status_code == 200:
        result = retry_response.json()
        print(f"   ✅ 重试失败任务API调用成功")
        if isinstance(result, dict):
            for key, value in result.items():
                print(f"     {key}: {value}")
except Exception as e:
    print(f"   ❌ 请求失败: {e}")

print("\n✅ 测试完成")
