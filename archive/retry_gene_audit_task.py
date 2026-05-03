#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py task <command>
"""重试gene_mgmt_audit任务"""

import json
import time
from pathlib import Path

import requests


def main() -> None:
    TOKEN_FILE = Path("/Volumes/1TB-M2/openclaw/.openclaw/athena_web_desktop.token")
    token = TOKEN_FILE.read_text().strip()

    base_url = "http://127.0.0.1:8080"
    headers = {"X-OpenClaw-Token": token, "Content-Type": "application/json"}

    print("重试gene_mgmt_audit任务...")

    # 获取队列状态
    response = requests.get(f"{base_url}/api/athena/queues", headers=headers, timeout=5)
    if response.status_code != 200:
        print(f"获取队列失败: {response.status_code}")
        return

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
        print("未找到基因管理队列")
        return

    items = target_queue.get("items", [])
    target_item = None

    for item in items:
        if item.get("id") == "gene_mgmt_audit":
            target_item = item
            break

    if not target_item:
        print("未找到gene_mgmt_audit任务")
        return

    print(f"找到任务: {target_item.get('id')}, 状态: {target_item.get('status')}")

    # 调用重试API
    task_id = target_item.get("id")
    retry_url = f"{base_url}/api/athena/queues/items/{target_route_id}/{task_id}/retry"

    retry_response = requests.post(retry_url, headers=headers, timeout=10)
    if retry_response.status_code == 200:
        print("重试成功")
    else:
        print(f"重试失败: {retry_response.text}")
        return

    # 等待后检查状态
    time.sleep(3)

    response2 = requests.get(f"{base_url}/api/athena/queues", headers=headers, timeout=5)
    if response2.status_code == 200:
        data2 = response2.json()
        for route in data2.get("routes", []):
            if route.get("queue_id") == "openhuman_aiplan_gene_management_20260405":
                for item in route.get("items", []):
                    if item.get("id") == "gene_mgmt_audit":
                        print(f"更新状态: {item.get('status')}")
                        break
                break

    print("脚本执行完成")


if __name__ == "__main__":
    main()
