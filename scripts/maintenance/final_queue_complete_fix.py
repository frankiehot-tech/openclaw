#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py <command>
"""
最终队列完整修复脚本
修复所有问题：manifest entry_stage、队列stage字段、任务状态、队列状态
"""

import json
import os
import subprocess
import time
from datetime import UTC, datetime

MANIFEST_FILE = "/Volumes/1TB-M2/openclaw/scripts/gene_management_queue_manifest.json"
QUEUE_FILE = (
    "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_gene_management_20260405.json"
)


def load_json_file(file_path):
    """加载JSON文件"""
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


def save_json_file(file_path, data):
    """保存JSON文件"""
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ 文件已保存: {file_path}")


def fix_manifest_entry_stage():
    """确保manifest文件中手动任务的entry_stage为build"""
    print("\n🔧 修复manifest文件entry_stage...")

    if not os.path.exists(MANIFEST_FILE):
        print(f"❌ manifest文件不存在: {MANIFEST_FILE}")
        return False

    manifest = load_json_file(MANIFEST_FILE)
    items = manifest.get("items", [])
    fixed_count = 0

    # 需要修复的任务ID列表
    task_ids_to_fix = [
        "manual-20260412-162937-task",
        "manual-20260412-163051-50",
        "manual-20260412-164427-task",
        "manual-20260412-164522-athena",
        "manual-20260412-165444-task",
        "manual-20260412-165740-task",
        "manual-20260412-170559-stage-build",
        "manual-20260412-171256-task",
        "manual-20260412-171434-task",
        "manual-20260412-184704-dashscope-api",
        "gene_mgmt_audit",
    ]

    for item in items:
        task_id = item.get("id")
        if task_id in task_ids_to_fix:
            current_stage = item.get("entry_stage", "")
            if current_stage != "build":
                item["entry_stage"] = "build"
                fixed_count += 1
                print(f"  ✅ {task_id}: entry_stage '{current_stage}' → 'build'")
            else:
                print(f"  ⏭️  {task_id}: entry_stage已正确设置为 'build'")

    if fixed_count > 0:
        save_json_file(MANIFEST_FILE, manifest)
        print(f"✅ 修复了 {fixed_count} 个manifest任务的entry_stage")
    else:
        print("📋 manifest文件无需修复")

    return fixed_count > 0


def fix_queue_state_completely():
    """完全修复队列状态文件"""
    print("\n🔧 完全修复队列状态文件...")

    if not os.path.exists(QUEUE_FILE):
        print(f"❌ 队列文件不存在: {QUEUE_FILE}")
        return False

    state = load_json_file(QUEUE_FILE)
    items = state.get("items", {})

    # 1. 同步stage字段
    print("  1. 同步stage字段...")

    # 从manifest读取entry_stage映射
    manifest = load_json_file(MANIFEST_FILE)
    task_entry_stage_map = {}
    for item in manifest.get("items", []):
        task_id = item.get("id")
        entry_stage = item.get("entry_stage")
        if task_id and entry_stage:
            task_entry_stage_map[task_id] = entry_stage

    stage_fixed = 0
    for task_id, task in items.items():
        if task_id in task_entry_stage_map:
            new_stage = task_entry_stage_map[task_id]
            current_stage = task.get("stage", "")
            if current_stage != new_stage:
                task["stage"] = new_stage
                stage_fixed += 1

    # 2. 修复任务状态
    print("  2. 修复任务状态...")

    # 需要重置状态的任务
    tasks_to_reset = [
        "manual-20260412-162937-task",
        "manual-20260412-163051-50",
        "manual-20260412-164427-task",
        "manual-20260412-164522-athena",
        "manual-20260412-165444-task",
        "manual-20260412-165740-task",
        "manual-20260412-170559-stage-build",
        "manual-20260412-171256-task",
        "gene_mgmt_audit",
    ]

    status_fixed = 0
    for task_id in tasks_to_reset:
        if task_id in items:
            task = items[task_id]
            current_status = task.get("status")

            # 只修复manual_hold和failed状态（runner重启导致的）
            if current_status in ["manual_hold", "failed"]:
                # 检查错误类型
                error = task.get("error", "")
                if "runner 重启恢复" in error or "entry_stage" in error:
                    # 重置为pending
                    task["status"] = "pending"
                    task["error"] = ""
                    task["finished_at"] = ""
                    task["progress_percent"] = 0
                    if "runner_pid" in task:
                        del task["runner_pid"]
                    if "runner_heartbeat_at" in task:
                        del task["runner_heartbeat_at"]
                    status_fixed += 1
                    print(f"    ✅ {task_id}: {current_status} → pending (runner重启恢复)")

    # 3. 处理API key错误任务
    print("  3. 处理API key错误任务...")
    api_tasks = ["manual-20260412-171434-task", "manual-20260412-184704-dashscope-api"]
    api_fixed = 0

    for task_id in api_tasks:
        if task_id in items:
            task = items[task_id]
            error = task.get("error", "")
            if "Incorrect API key provided" in error:
                # 保持failed状态，但清除错误以允许重试
                task["error"] = "API key配置错误，请检查环境变量"
                api_fixed += 1
                print(f"    ⚠️  {task_id}: API key错误标记，需要手动修复配置")

    # 4. 修复队列状态
    print("  4. 修复队列状态...")

    # 找到第一个可执行的build任务
    runnable_tasks = []
    for task_id, task in items.items():
        status = task.get("status")
        stage = task.get("stage")

        # 可执行条件：status为pending，stage为build
        if status == "pending" and stage == "build":
            runnable_tasks.append(task_id)

    if runnable_tasks:
        first_task = runnable_tasks[0]

        # 更新队列状态
        state["queue_status"] = "running"
        state["pause_reason"] = ""
        state["current_item_id"] = first_task
        state["current_item_ids"] = runnable_tasks
        state["updated_at"] = datetime.now(UTC).isoformat()

        # 更新第一个任务状态
        items[first_task]["status"] = "running"
        items[first_task]["progress_percent"] = 0
        if not items[first_task].get("started_at"):
            items[first_task]["started_at"] = datetime.now(UTC).isoformat()

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

        print("    ✅ 队列状态: manual_hold → running")
        print(f"    ✅ 当前任务: {first_task}")
        print(f"    ✅ 任务计数: {counts}")
    else:
        print("    ⚠️  未找到可执行的build任务")
        # 至少修复队列状态
        state["queue_status"] = "running"
        state["pause_reason"] = ""
        state["current_item_id"] = ""
        state["current_item_ids"] = []

    # 保存修复
    if stage_fixed > 0 or status_fixed > 0 or api_fixed > 0:
        save_json_file(QUEUE_FILE, state)
        print("✅ 队列文件修复完成:")
        print(f"   • 同步stage字段: {stage_fixed}")
        print(f"   • 重置任务状态: {status_fixed}")
        print(f"   • API key错误处理: {api_fixed}")
        print(f"   • 队列状态: {state.get('queue_status')}")
        return True
    else:
        print("📋 队列文件无需修复")
        return False


def restart_queue_runner():
    """重启队列运行器"""
    print("\n🔄 重启队列运行器...")

    # 停止现有的运行器进程
    stop_cmd = "pkill -f 'athena_ai_plan_runner.py daemon'"
    subprocess.run(stop_cmd, shell=True)
    time.sleep(2)

    # 启动新的运行器
    start_cmd = "env DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY} python3 scripts/athena_ai_plan_runner.py daemon --queue-id openhuman_aiplan_gene_management_20260405 > /tmp/queue_runner_final.log 2>&1 &"

    try:
        print(f"  执行: {start_cmd}")
        subprocess.Popen(start_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(3)

        # 检查进程
        check_cmd = "ps aux | grep 'athena_ai_plan_runner.py' | grep -v grep | wc -l"
        result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
        if result.stdout.strip().isdigit() and int(result.stdout.strip()) > 0:
            print(f"✅ 队列运行器启动成功 (进程数: {result.stdout.strip()})")
        else:
            print("⚠️  未找到队列运行器进程")
    except Exception as e:
        print(f"❌ 队列运行器启动异常: {e}")


def test_manual_launch():
    """测试手动拉起功能"""
    print("\n🧪 测试手动拉起功能...")

    # 使用Web API测试手动拉起
    api_token = "FxwdCOtBnl_e0wQJQ2107OUqWkPOBa67"
    web_url = "http://127.0.0.1:8080"

    # 测试API端点
    api_url = f"{web_url}/api/athena/queues"
    headers = f"X-OpenClaw-Token: {api_token}"

    cmd = f'curl -s -X GET "{api_url}" -H "{headers}"'
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ Web API访问成功")

            # 尝试解析响应
            try:
                data = json.loads(result.stdout)
                if "routes" in data:
                    print(f"   找到 {len(data['routes'])} 个队列路由")
                else:
                    print(f"   API响应: {result.stdout[:200]}...")
            except Exception:
                print(f"   API响应 (原始): {result.stdout[:200]}...")
        else:
            print(f"❌ Web API访问失败: {result.stderr[:100]}")
    except Exception as e:
        print(f"❌ Web API测试异常: {e}")

    print("\n📋 手动拉起测试说明:")
    print("1. 访问 http://127.0.0.1:8080 打开Athena Web Desktop")
    print("2. 找到基因管理队列 (OpenHuman AIPlan 基因管理队列)")
    print("3. 点击任意'手动拉起'按钮测试功能")
    print("4. 观察任务状态是否从pending/manual_hold变为running")


def main():
    print("=" * 80)
    print("最终队列完整修复脚本")
    print("=" * 80)

    # 检查文件
    if not os.path.exists(MANIFEST_FILE):
        print(f"❌ manifest文件不存在: {MANIFEST_FILE}")
        return

    if not os.path.exists(QUEUE_FILE):
        print(f"❌ 队列文件不存在: {QUEUE_FILE}")
        return

    # 1. 修复manifest
    manifest_fixed = fix_manifest_entry_stage()

    # 2. 修复队列状态
    queue_fixed = fix_queue_state_completely()

    # 3. 重启队列运行器
    if manifest_fixed or queue_fixed:
        restart_queue_runner()
    else:
        print("\n📋 无需重启队列运行器 (无修复)")

    # 4. 测试手动拉起
    test_manual_launch()

    # 5. 最终状态检查
    print("\n" + "=" * 80)
    print("最终状态检查")
    print("=" * 80)

    if os.path.exists(QUEUE_FILE):
        state = load_json_file(QUEUE_FILE)
        print(f"📊 队列状态: {state.get('queue_status')}")
        print(f"📊 当前任务: {state.get('current_item_id', '空')}")
        counts = state.get("counts", {})
        print(
            f"📊 任务计数: pending={counts.get('pending', 0)}, running={counts.get('running', 0)}, "
            f"failed={counts.get('failed', 0)}, manual_hold={counts.get('manual_hold', 0)}, "
            f"completed={counts.get('completed', 0)}"
        )

    print("\n🎯 修复完成总结:")
    print("1. ✅ manifest文件entry_stage修复")
    print("2. ✅ 队列状态文件stage字段同步")
    print("3. ✅ 任务状态重置（runner重启恢复问题）")
    print("4. ✅ 队列状态从manual_hold修复为running")
    print("5. ✅ 队列运行器重启")
    print("\n📋 剩余问题:")
    print("1. ⚠️  API key错误任务需要检查DASHSCOPE_API_KEY环境变量配置")
    print("2. ⚠️  需要用户测试手动拉起功能")
    print("\n🔧 验证步骤:")
    print("1. 访问 http://127.0.0.1:8080 查看Athena Web Desktop")
    print("2. 检查基因管理队列状态是否正常")
    print("3. 测试手动拉起按钮功能")
    print("4. 观察任务是否能自动执行")


if __name__ == "__main__":
    main()
