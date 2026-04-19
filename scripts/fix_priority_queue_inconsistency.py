#!/usr/bin/env python3
"""
修复优先执行队列数据不一致问题
- 从Web API获取实际的任务状态
- 同步到本地队列文件
- 更新counts统计
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import requests

# 配置
ROOT_DIR = Path(__file__).parent.parent
QUEUE_FILE = (
    ROOT_DIR / ".openclaw" / "plan_queue" / "openhuman_aiplan_priority_execution_20260414.json"
)
TOKEN_FILE = ROOT_DIR / ".openclaw" / "athena_web_desktop.token"
WEB_API_URL = "http://127.0.0.1:8080/api/athena/queues"


def load_auth_token() -> str:
    """加载认证token"""
    if TOKEN_FILE.exists():
        try:
            return TOKEN_FILE.read_text().strip()
        except Exception as e:
            print(f"读取token文件失败: {e}")

    # 默认token
    return "FxwdCOtBnl_e0wQJQ2107OUqWkPOBa67"


def get_web_queue_status(token: str) -> Dict[str, Any]:
    """从Web API获取队列状态"""
    headers = {"X-OpenClaw-Token": token}

    try:
        response = requests.get(WEB_API_URL, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"Web API请求失败: {response.status_code} - {response.text[:200]}")
            return {}

        data = response.json()

        # 找到优先执行队列
        for route in data.get("routes", []):
            if route.get("queue_id") == "openhuman_aiplan_build_priority_20260328":
                return {
                    "queue_status": route.get("queue_status", ""),
                    "items": route.get("items", []),
                    "route_id": route.get("route_id", ""),
                }

        print("在Web API中未找到优先执行队列")
        return {}

    except Exception as e:
        print(f"获取Web队列状态失败: {e}")
        return {}


def update_queue_file(queue_file: Path, web_data: Dict[str, Any]) -> bool:
    """更新队列文件，同步状态"""
    if not queue_file.exists():
        print(f"队列文件不存在: {queue_file}")
        return False

    try:
        with open(queue_file, "r", encoding="utf-8") as f:
            file_data = json.load(f)
    except Exception as e:
        print(f"读取队列文件失败: {e}")
        return False

    web_items = web_data.get("items", [])
    if not web_items:
        print("Web数据中没有任务项")
        return False

    # 创建Web任务ID到状态的映射
    web_status_map = {}
    for item in web_items:
        task_id = item.get("id", "")
        status = item.get("status", "")
        if task_id and status:
            web_status_map[task_id] = status

    # 更新文件中的任务状态
    file_items = file_data.get("items", [])
    updated_count = 0

    for i, item in enumerate(file_items):
        task_id = item.get("id", "")
        if task_id in web_status_map:
            new_status = web_status_map[task_id]
            if item.get("status") != new_status:
                item["status"] = new_status
                updated_count += 1

    # 重新计算统计
    status_counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "manual_hold": 0}

    for item in file_items:
        status = item.get("status", "")
        if status in status_counts:
            status_counts[status] += 1

    # 更新文件数据
    file_data["queue_status"] = web_data.get("queue_status", "running")
    file_data["counts"] = status_counts

    # 如果当前项目为空，尝试设置第一个非completed任务为当前项目
    if not file_data.get("current_item_id"):
        for item in file_items:
            status = item.get("status", "")
            if status not in ["completed", "failed", "manual_hold"]:
                file_data["current_item_id"] = item.get("id", "")
                break

    # 更新时间戳
    from datetime import datetime

    file_data["updated_at"] = datetime.now().isoformat()

    # 保存文件
    try:
        # 创建备份
        backup_file = queue_file.with_suffix(
            f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        import shutil

        shutil.copy2(queue_file, backup_file)
        print(f"创建备份: {backup_file}")

        # 写入更新后的文件
        with open(queue_file, "w", encoding="utf-8") as f:
            json.dump(file_data, f, ensure_ascii=False, indent=2)

        print(f"✅ 队列文件更新成功")
        print(f"   - 更新任务数: {updated_count}")
        print(f"   - 队列状态: {file_data['queue_status']}")
        print(f"   - 任务统计: {status_counts}")
        print(f"   - 当前任务: {file_data.get('current_item_id', '无')}")

        return True

    except Exception as e:
        print(f"保存队列文件失败: {e}")
        return False


def main():
    print("🔧 开始修复优先执行队列数据不一致问题")
    print(f"队列文件: {QUEUE_FILE}")

    # 加载token
    token = load_auth_token()
    print(f"认证token: {token[:10]}...")

    # 获取Web API数据
    print("📡 获取Web API队列状态...")
    web_data = get_web_queue_status(token)

    if not web_data:
        print("❌ 无法从Web API获取队列数据")
        return 1

    print(f"   - 队列状态: {web_data.get('queue_status')}")
    print(f"   - 任务数: {len(web_data.get('items', []))}")

    # 更新队列文件
    print("🔄 更新本地队列文件...")
    if update_queue_file(QUEUE_FILE, web_data):
        print("✅ 修复完成")

        # 建议重启队列运行器
        print("\n💡 建议操作:")
        print("   1. 重启队列运行器以加载修复后的数据:")
        print("      pkill -f athena_ai_plan_runner.py")
        print(
            "      nohup python3 scripts/athena_ai_plan_runner.py > logs/athena_ai_plan_runner.nohup.log 2>&1 &"
        )
        print("   2. 检查队列状态:")
        print(
            f"      curl -H 'X-OpenClaw-Token: {token[:10]}...' http://127.0.0.1:8080/api/athena/queues"
        )

        return 0
    else:
        print("❌ 修复失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
