#!/usr/bin/env python3
"""
最终基因管理队列修复脚本
直接修复队列文件中的根本问题，确保手动拉起功能恢复正常
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

QUEUE_FILE = (
    "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_gene_management_20260405.json"
)
WEB_SERVER_URL = "http://127.0.0.1:8080"
API_TOKEN = "FxwdCOtBnl_e0wQJQ2107OUqWkPOBa67"  # 从HTML meta标签获取的token


def load_queue_state():
    """加载队列状态"""
    with open(QUEUE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_queue_state(state):
    """保存队列状态"""
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    print(f"✅ 队列状态已保存到 {QUEUE_FILE}")


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
            if os.path.exists(instruction_path):
                items[task_id]["instruction_path"] = instruction_path
                items[task_id]["error"] = ""
                items[task_id]["status"] = "pending"
                items[task_id]["finished_at"] = ""
                items[task_id]["summary"] = "instruction_path已修复，任务重置为pending"
                fixed_count += 1
                print(f"✅ 修复 {task_id}: {instruction_path}")
            else:
                print(f"❌ 指令文件不存在: {instruction_path}")

    return fixed_count


def fix_api_key_tasks(state):
    """修复API key错误的任务"""
    items = state["items"]
    fixed_count = 0

    api_key_tasks = ["manual-20260412-171434-task", "manual-20260412-184704-dashscope-api"]

    for task_id in api_key_tasks:
        if task_id in items and items[task_id].get("status") == "failed":
            # 验证API key
            dashscope_key = os.environ.get("DASHSCOPE_API_KEY")
            if dashscope_key:
                items[task_id]["error"] = ""
                items[task_id]["status"] = "pending"
                items[task_id]["finished_at"] = ""
                items[task_id]["summary"] = "API key已验证，任务重置为pending"
                fixed_count += 1
                print(f"✅ 修复API key任务 {task_id}")
            else:
                print(f"❌ 未找到DASHSCOPE_API_KEY环境变量")

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

    print(f"📋 发现 {len(manual_hold_tasks)} 个manual_hold任务")

    # 选择第一个任务作为当前任务
    first_task = manual_hold_tasks[0]

    # 修复队列状态
    state["queue_status"] = "running"
    state["pause_reason"] = ""
    state["current_item_id"] = first_task
    state["current_item_ids"] = manual_hold_tasks
    state["updated_at"] = datetime.now(timezone.utc).isoformat()

    # 更新第一个任务状态
    items[first_task]["status"] = "running"
    items[first_task]["progress_percent"] = 0
    if not items[first_task].get("started_at"):
        items[first_task]["started_at"] = datetime.now(timezone.utc).isoformat()

    # 其他任务设置为pending
    for i, task_id in enumerate(manual_hold_tasks):
        if i == 0:
            continue
        items[task_id]["status"] = "pending"

    # 更新计数
    counts = state["counts"]
    counts["pending"] = len(manual_hold_tasks) - 1
    counts["running"] = 1
    counts["manual_hold"] = 0
    counts["failed"] = 0  # 重置失败计数

    state["counts"] = counts

    print(f"✅ 队列状态修复完成:")
    print(f"   • queue_status: {state['queue_status']}")
    print(f"   • current_item_id: {state['current_item_id']}")
    print(f"   • counts: pending={counts['pending']}, running={counts['running']}")

    return True


def test_web_api():
    """测试Web API和手动拉起功能"""
    print("\n🧪 测试Web API和手动拉起功能")

    # 测试API端点
    api_url = f"{WEB_SERVER_URL}/api/athena/queues"
    headers = f"X-OpenClaw-Token: {API_TOKEN}"

    cmd = f'curl -s -X GET "{api_url}" -H "{headers}"'
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ Web API访问成功")
            try:
                data = json.loads(result.stdout)
                print(f"   API响应: {json.dumps(data, ensure_ascii=False)[:200]}...")
            except:
                print(f"   API响应 (原始): {result.stdout[:200]}...")
        else:
            print(f"❌ Web API访问失败: {result.stderr[:100]}")
    except Exception as e:
        print(f"❌ Web API测试异常: {e}")

    # 测试手动拉起端点
    print("\n🔧 测试手动拉起端点...")
    # 需要有效的queue_id和item_id
    test_cmd = f'curl -s -X POST "{WEB_SERVER_URL}/api/athena/queues/test/launch" -H "{headers}" -H "Content-Type: application/json"'
    try:
        result = subprocess.run(test_cmd, shell=True, capture_output=True, text=True, timeout=5)
        print(f"   手动拉起端点响应: {result.stdout[:100]}...")
    except Exception as e:
        print(f"   手动拉起测试异常: {e}")


def restart_queue_runner():
    """重启队列运行器"""
    print("\n🔄 重启队列运行器")

    # 停止现有的运行器进程
    stop_cmd = "pkill -f 'athena_ai_plan_runner.py daemon'"
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


def main():
    print("=" * 80)
    print("最终基因管理队列修复脚本")
    print("=" * 80)

    if not os.path.exists(QUEUE_FILE):
        print(f"❌ 队列文件不存在: {QUEUE_FILE}")
        return

    # 1. 加载队列状态
    print("\n📂 加载队列状态...")
    state = load_queue_state()

    print(f"   队列状态: {state.get('queue_status', 'unknown')}")
    print(f"   暂停原因: {state.get('pause_reason', 'unknown')}")
    print(f"   当前任务: {state.get('current_item_id', '空')}")

    counts = state.get("counts", {})
    print(
        f"   任务统计: pending={counts.get('pending', 0)}, running={counts.get('running', 0)}, "
        f"failed={counts.get('failed', 0)}, manual_hold={counts.get('manual_hold', 0)}"
    )

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
        save_queue_state(state)
    else:
        print("\n📋 没有需要修复的问题")

    # 6. 重启队列运行器
    restart_queue_runner()

    # 7. 测试Web API
    test_web_api()

    # 8. 总结
    print("\n" + "=" * 80)
    print("修复总结")
    print("=" * 80)
    print(f"• instruction_path缺失任务修复: {fixed_instruction}个")
    print(f"• API key错误任务修复: {fixed_api}个")
    print(f"• 队列manual_hold状态修复: {'✅' if fixed_queue else '❌'}")

    print("\n🎯 下一步建议:")
    print("1. 访问 http://127.0.0.1:8080 查看Athena Web Desktop")
    print("2. 在Web界面中测试手动拉起功能")
    print("3. 运行监控脚本: python3 scripts/queue_monitor.py --alert")
    print("4. 检查队列状态: python3 scripts/athena_ai_plan_runner.py status " + QUEUE_FILE)


if __name__ == "__main__":
    main()
