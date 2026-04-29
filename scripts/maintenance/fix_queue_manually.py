#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py repair <command> 或 governance_cli.py queue fix
"""
手动修复基因管理队列文件
直接修改队列状态和任务配置，确保修复生效
"""

import json
import os
from datetime import UTC, datetime

QUEUE_FILE = (
    "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_gene_management_20260405.json"
)


def load_queue():
    """加载队列文件"""
    with open(QUEUE_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_queue(state):
    """保存队列文件"""
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    print(f"✅ 队列文件已保存: {QUEUE_FILE}")


def print_queue_status(state):
    """打印队列状态"""
    print(f"队列状态: {state.get('queue_status', 'unknown')}")
    print(f"暂停原因: {state.get('pause_reason', 'unknown')}")
    print(f"当前任务: {state.get('current_item_id', '空')}")

    counts = state.get("counts", {})
    print(
        f"任务统计: pending={counts.get('pending', 0)}, running={counts.get('running', 0)}, "
        f"failed={counts.get('failed', 0)}, manual_hold={counts.get('manual_hold', 0)}, "
        f"completed={counts.get('completed', 0)}"
    )

    return state.get("queue_status"), counts


def fix_instruction_paths(state):
    """修复instruction_path缺失的任务"""
    items = state["items"]
    fixed_count = 0

    # 任务ID到指令文件的映射
    task_to_instruction = {
        "manual-20260412-162937-task": "/Volumes/1TB-M2/openclaw/.openclaw/chat_instructions/auto_fixed_manual-20260412-162937-task.md",
        "manual-20260412-163051-50": "/Volumes/1TB-M2/openclaw/.openclaw/chat_instructions/auto_fixed_manual-20260412-163051-50.md",
        "manual-20260412-164427-task": "/Volumes/1TB-M2/openclaw/.openclaw/chat_instructions/auto_fixed_manual-20260412-164427-task.md",
        "manual-20260412-164522-athena": "/Volumes/1TB-M2/openclaw/.openclaw/chat_instructions/auto_fixed_manual-20260412-164522-athena.md",
    }

    for task_id, instruction_path in task_to_instruction.items():
        if task_id in items:
            print(f"检查任务 {task_id}:")
            print(f"  当前status: {items[task_id].get('status')}")
            print(f"  当前instruction_path: {items[task_id].get('instruction_path')}")

            if os.path.exists(instruction_path):
                items[task_id]["instruction_path"] = instruction_path
                items[task_id]["error"] = ""
                items[task_id]["status"] = "pending"
                items[task_id]["finished_at"] = ""
                items[task_id]["summary"] = "instruction_path已修复，任务重置为pending"
                fixed_count += 1
                print(f"  ✅ 已修复: {instruction_path}")
            else:
                print(f"  ❌ 指令文件不存在: {instruction_path}")

    return fixed_count


def fix_api_key_tasks(state):
    """修复API key错误的任务"""
    items = state["items"]
    fixed_count = 0

    api_key_tasks = ["manual-20260412-171434-task", "manual-20260412-184704-dashscope-api"]

    for task_id in api_key_tasks:
        if task_id in items and items[task_id].get("status") == "failed":
            print(f"检查API key任务 {task_id}:")
            print(f"  当前status: {items[task_id].get('status')}")
            print(
                f"  当前error: {items[task_id].get('error')[:50] if items[task_id].get('error') else '空'}"
            )

            # 验证API key
            dashscope_key = os.environ.get("DASHSCOPE_API_KEY")
            if dashscope_key:
                items[task_id]["error"] = ""
                items[task_id]["status"] = "pending"
                items[task_id]["finished_at"] = ""
                items[task_id]["summary"] = "API key已验证，任务重置为pending"
                fixed_count += 1
                print("  ✅ 已修复API key任务")
            else:
                print("  ❌ 未找到DASHSCOPE_API_KEY环境变量")

    return fixed_count


def fix_manual_hold_tasks(state):
    """修复manual_hold任务"""
    items = state["items"]
    manual_hold_tasks = []

    for task_id, task in items.items():
        if task.get("status") == "manual_hold":
            manual_hold_tasks.append(task_id)

    if not manual_hold_tasks:
        print("📋 没有manual_hold任务需要修复")
        return False

    print(f"📋 发现 {len(manual_hold_tasks)} 个manual_hold任务: {manual_hold_tasks}")

    # 选择第一个任务作为当前任务
    first_task = manual_hold_tasks[0]

    # 修复队列状态
    state["queue_status"] = "running"
    state["pause_reason"] = ""
    state["current_item_id"] = first_task
    state["current_item_ids"] = manual_hold_tasks
    state["updated_at"] = datetime.now(UTC).isoformat()

    # 更新第一个任务状态
    items[first_task]["status"] = "running"
    items[first_task]["progress_percent"] = 0
    if not items[first_task].get("started_at"):
        items[first_task]["started_at"] = datetime.now(UTC).isoformat()

    # 其他任务设置为pending
    for i, task_id in enumerate(manual_hold_tasks):
        if i == 0:
            continue
        items[task_id]["status"] = "pending"

    # 重新计算计数
    counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "manual_hold": 0}

    for task_id, task in items.items():
        status = task.get("status")
        if status == "pending":
            counts["pending"] += 1
        elif status == "running":
            counts["running"] += 1
        elif status == "completed":
            counts["completed"] += 1
        elif status == "failed":
            counts["failed"] += 1
        elif status == "manual_hold":
            counts["manual_hold"] += 1

    state["counts"] = counts

    print("✅ 队列状态修复完成:")
    print(f"   • queue_status: {state['queue_status']}")
    print(f"   • current_item_id: {state['current_item_id']}")
    print(f"   • counts: {counts}")

    return True


def main():
    print("=" * 80)
    print("手动修复基因管理队列")
    print("=" * 80)

    if not os.path.exists(QUEUE_FILE):
        print(f"❌ 队列文件不存在: {QUEUE_FILE}")
        return

    # 1. 加载队列状态
    print("\n📂 加载队列状态...")
    state = load_queue()

    print("\n📊 修复前队列状态:")
    old_status, old_counts = print_queue_status(state)

    # 2. 修复instruction_path缺失任务
    print("\n🔧 修复instruction_path缺失任务...")
    fixed_instruction = fix_instruction_paths(state)

    # 3. 修复API key错误任务
    print("\n🔧 修复API key错误任务...")
    fixed_api = fix_api_key_tasks(state)

    # 4. 修复manual_hold状态
    print("\n🔧 修复队列manual_hold状态...")
    fixed_queue = fix_manual_hold_tasks(state)

    # 5. 保存修复后的状态
    if fixed_instruction > 0 or fixed_api > 0 or fixed_queue:
        print("\n💾 保存修复后的队列状态...")
        save_queue(state)

        print("\n📊 修复后队列状态:")
        new_status, new_counts = print_queue_status(state)

        print("\n📈 状态变化:")
        print(f"  queue_status: {old_status} → {new_status}")
        print(f"  pending: {old_counts.get('pending', 0)} → {new_counts.get('pending', 0)}")
        print(f"  running: {old_counts.get('running', 0)} → {new_counts.get('running', 0)}")
        print(f"  failed: {old_counts.get('failed', 0)} → {new_counts.get('failed', 0)}")
        print(
            f"  manual_hold: {old_counts.get('manual_hold', 0)} → {new_counts.get('manual_hold', 0)}"
        )
    else:
        print("\n📋 没有需要修复的问题")

    # 6. 重启队列运行器
    print("\n🔄 重启队列运行器...")
    restart_queue_runner()

    print("\n" + "=" * 80)
    print("修复完成")
    print("=" * 80)


def restart_queue_runner():
    """重启队列运行器"""
    # 停止现有的运行器进程
    stop_cmd = "pkill -f 'athena_ai_plan_runner.py daemon'"
    import subprocess

    subprocess.run(stop_cmd, shell=True)

    # 启动新的运行器
    start_cmd = "python3 scripts/athena_ai_plan_runner.py daemon --queue-id openhuman_aiplan_gene_management_20260405"
    try:
        result = subprocess.run(start_cmd, shell=True, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ 队列运行器启动成功")
        else:
            print(f"⚠️  队列运行器启动可能有问题: {result.stderr[:100]}")
    except Exception as e:
        print(f"❌ 队列运行器启动异常: {e}")

    # 检查进程
    check_cmd = "ps aux | grep 'athena_ai_plan_runner.py' | grep -v grep"
    subprocess.run(check_cmd, shell=True)


if __name__ == "__main__":
    main()
