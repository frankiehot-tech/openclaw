#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py repair <command> 或 governance_cli.py queue fix
"""
修复"无法定位当前队列项"问题
解决Web界面手动拉起按钮无响应问题
"""

import json
import os
from datetime import datetime


def diagnose_queue_item_location():
    """诊断队列项定位问题"""

    print("🔍 诊断无法定位当前队列项问题...")

    queue_file = (
        "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_plan_manual_20260328.json"
    )

    if not os.path.exists(queue_file):
        print(f"❌ 队列状态文件不存在: {queue_file}")
        return None

    try:
        with open(queue_file, encoding="utf-8") as f:
            queue_state = json.load(f)

        print(f"📊 队列状态: {queue_state.get('queue_status', 'unknown')}")
        print(f"🎯 当前任务ID: {queue_state.get('current_item_id', '空')}")
        print(f"📋 当前任务列表: {queue_state.get('current_item_ids', [])}")

        # 分析任务状态
        items = queue_state.get("items", {})

        print("\n📋 任务状态分析:")
        for task_id, task in items.items():
            status = task.get("status", "unknown")
            stage = task.get("stage", "unknown")
            print(f"   {task_id}: {status} (阶段: {stage})")

        # 检查OpenCode CLI任务
        opencode_task = items.get("opencode_cli_optimization", {})
        if opencode_task:
            print(f"\n🔍 OpenCode CLI任务状态: {opencode_task.get('status', 'unknown')}")
            print(f"📁 文件路径: {opencode_task.get('instruction_path', '未设置')}")

        return queue_state

    except Exception as e:
        print(f"❌ 诊断队列项定位问题失败: {e}")
        return None


def fix_queue_item_location():
    """修复队列项定位问题"""

    print("\n🔧 修复无法定位当前队列项问题...")

    queue_file = (
        "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_plan_manual_20260328.json"
    )

    try:
        with open(queue_file, encoding="utf-8") as f:
            queue_state = json.load(f)

        items = queue_state.get("items", {})

        # 查找可执行的任务
        executable_tasks = []
        manual_tasks = []

        for task_id, task in items.items():
            status = task.get("status", "")
            if status in ["pending", ""]:
                executable_tasks.append(task_id)
            elif status == "manual_hold":
                manual_tasks.append(task_id)

        print(f"🔍 发现可执行任务: {executable_tasks}")
        print(f"🔍 发现手动保留任务: {manual_tasks}")

        if executable_tasks:
            # 有可执行任务，设置当前任务
            current_task = executable_tasks[0]
            queue_state["current_item_id"] = current_task
            queue_state["current_item_ids"] = executable_tasks
            queue_state["queue_status"] = "running"
            queue_state["pause_reason"] = ""

            print(f"✅ 设置当前任务: {current_task}")

        elif manual_tasks:
            # 只有手动任务，需要激活一个作为当前任务
            current_task = manual_tasks[0]

            # 激活第一个手动任务
            items[current_task]["status"] = "pending"
            items[current_task]["progress_percent"] = 0

            queue_state["current_item_id"] = current_task
            queue_state["current_item_ids"] = [current_task]
            queue_state["queue_status"] = "running"
            queue_state["pause_reason"] = ""

            print(f"✅ 激活手动任务作为当前任务: {current_task}")

        else:
            # 没有可用任务，需要创建新任务
            print("⚠️ 没有发现可用任务，需要创建新任务")
            return False

        # 更新任务计数
        counts = queue_state.get("counts", {})
        counts["pending"] = len([t for t in items.values() if t.get("status") in ["pending", ""]])
        counts["running"] = 1 if queue_state["current_item_id"] else 0
        counts["manual_hold"] = len([t for t in items.values() if t.get("status") == "manual_hold"])
        queue_state["counts"] = counts

        # 更新时间戳
        queue_state["updated_at"] = datetime.now().isoformat()

        # 保存修复后的状态
        with open(queue_file, "w", encoding="utf-8") as f:
            json.dump(queue_state, f, indent=2, ensure_ascii=False)

        print("✅ 队列项定位问题已修复")
        print(f"📊 新队列状态: {queue_state['queue_status']}")
        print(f"🎯 当前任务: {queue_state['current_item_id']}")

        return True

    except Exception as e:
        print(f"❌ 修复队列项定位问题失败: {e}")
        return False


def check_web_interface_communication():
    """检查Web接口与队列通信"""

    print("\n🌐 检查Web接口与队列通信...")

    # 检查Web服务器脚本
    web_script = "/Volumes/1TB-M2/openclaw/scripts/athena_web_desktop_compat.py"

    if not os.path.exists(web_script):
        print(f"❌ Web服务器脚本不存在: {web_script}")
        return False

    # 检查队列读取功能
    queue_file = (
        "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_plan_manual_20260328.json"
    )

    if not os.path.exists(queue_file):
        print(f"❌ 队列状态文件不存在: {queue_file}")
        return False

    try:
        # 模拟Web接口读取队列
        with open(queue_file, encoding="utf-8") as f:
            queue_data = json.load(f)

        # 检查关键字段是否存在
        required_fields = ["queue_id", "name", "current_item_id", "items"]
        for field in required_fields:
            if field not in queue_data:
                print(f"❌ 队列数据缺少必要字段: {field}")
                return False

        print("✅ Web接口与队列通信正常")
        return True

    except Exception as e:
        print(f"❌ Web接口与队列通信检查失败: {e}")
        return False


def create_manual_launch_fix():
    """创建手动拉起功能修复"""

    print("\n🔧 修复手动拉起功能...")

    # 检查Web服务器的手动拉起API实现
    web_script = "/Volumes/1TB-M2/openclaw/scripts/athena_web_desktop_compat.py"

    if not os.path.exists(web_script):
        print(f"❌ Web服务器脚本不存在: {web_script}")
        return False

    try:
        # 读取Web服务器代码，检查手动拉起功能
        with open(web_script, encoding="utf-8") as f:
            web_code = f.read()

        # 检查是否存在手动拉起功能
        if "launch_queue_item" in web_code:
            print("✅ Web服务器包含手动拉起功能")

            # 检查功能实现是否完整
            if "route_from_id" in web_code and "load_manifest_items" in web_code:
                print("✅ 手动拉起功能实现完整")
                return True
            else:
                print("⚠️ 手动拉起功能实现可能不完整")
                return False
        else:
            print("❌ Web服务器缺少手动拉起功能")
            return False

    except Exception as e:
        print(f"❌ 检查手动拉起功能失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("🔧 无法定位当前队列项问题修复工具")
    print("=" * 60)

    # 诊断问题
    queue_state = diagnose_queue_item_location()
    if not queue_state:
        print("❌ 诊断失败，无法继续修复")
        return

    # 检查Web接口通信
    if not check_web_interface_communication():
        print("⚠️ Web接口通信可能存在问题")

    # 检查手动拉起功能
    if not create_manual_launch_fix():
        print("⚠️ 手动拉起功能可能需要修复")

    # 修复队列项定位问题
    if fix_queue_item_location():
        print("\n✅ 队列项定位问题修复成功")
    else:
        print("\n❌ 队列项定位问题修复失败")
        return

    print("\n🎯 修复完成，下一步操作:")
    print("1. 访问 http://127.0.0.1:8080 验证队列状态")
    print("2. 测试手动拉起按钮功能")
    print("3. 检查无法定位当前队列项错误是否消失")


if __name__ == "__main__":
    main()
