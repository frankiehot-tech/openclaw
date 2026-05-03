#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py <command>
"""
手动队列修复脚本
直接强制更新queue_status为running，确保写入成功
"""

import json
import os
import sys

QUEUE_FILE = (
    "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"
)


def load_queue():
    with open(QUEUE_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_queue(data):
    # 备份原文件
    backup_file = f"{QUEUE_FILE}.manual_backup"
    if os.path.exists(QUEUE_FILE) and not os.path.exists(backup_file):
        import shutil

        shutil.copy2(QUEUE_FILE, backup_file)
        print(f"备份: {backup_file}")

    # 写入新文件
    temp_file = f"{QUEUE_FILE}.tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # 原子性替换
    os.replace(temp_file, QUEUE_FILE)
    print(f"已保存: {QUEUE_FILE}")

    # 验证
    with open(QUEUE_FILE, encoding="utf-8") as f:
        saved = json.load(f)

    if saved.get("queue_status") == data.get("queue_status"):
        print(f"✅ 验证成功: queue_status = {saved.get('queue_status')}")
        return True
    else:
        print(f"❌ 验证失败: 期望 {data.get('queue_status')}, 实际 {saved.get('queue_status')}")
        return False


def main():
    print("手动修复队列状态...")

    try:
        data = load_queue()
        old_status = data.get("queue_status", "unknown")
        old_pause = data.get("pause_reason", "")

        print(f"当前状态: queue_status={old_status}, pause_reason={old_pause}")

        # 强制更新
        data["queue_status"] = "running"
        data["pause_reason"] = ""

        # 确保有当前任务（如果为空）
        if not data.get("current_item_id") and data.get("items"):
            items = data.get("items", {})
            pending = [tid for tid, task in items.items() if task.get("status") == "pending"]
            if pending:
                data["current_item_id"] = pending[0]
                print(f"设置当前任务: {data['current_item_id']}")

        # 重新计算counts（可选）
        items = data.get("items", {})
        pending = sum(1 for task in items.values() if task.get("status") == "pending")
        running = sum(1 for task in items.values() if task.get("status") == "running")
        completed = sum(1 for task in items.values() if task.get("status") == "completed")
        failed = sum(1 for task in items.values() if task.get("status") == "failed")

        if "counts" not in data:
            data["counts"] = {}

        data["counts"]["pending"] = pending
        data["counts"]["running"] = running
        data["counts"]["completed"] = completed
        data["counts"]["failed"] = failed

        print(f"更新后: queue_status=running, pending={pending}, running={running}")

        # 保存
        if save_queue(data):
            print("✅ 队列修复完成")
            print("🚀 现在可以开始24小时监控验证")
        else:
            print("❌ 队列修复失败，需要手动检查")
            sys.exit(1)

    except Exception as e:
        print(f"错误: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
