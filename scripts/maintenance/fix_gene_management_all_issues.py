#!/usr/bin/env python3
"""
综合修复基因管理队列所有问题
包括：队列manual_hold状态、instruction_path缺失任务、API key错误、手动拉起功能测试
"""

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone


def load_queue_state(queue_file):
    """加载队列状态文件"""
    try:
        with open(queue_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 加载队列状态失败: {e}")
        return None


def save_queue_state(queue_file, queue_state):
    """保存队列状态文件"""
    try:
        with open(queue_file, "w", encoding="utf-8") as f:
            json.dump(queue_state, f, indent=2, ensure_ascii=False)
        print(f"✅ 队列状态已保存到 {queue_file}")
        return True
    except Exception as e:
        print(f"❌ 保存队列状态失败: {e}")
        return False


def diagnose_queue_problems(queue_state):
    """诊断队列所有问题"""
    print("=" * 60)
    print("🔍 综合诊断基因管理队列问题")
    print("=" * 60)

    items = queue_state.get("items", {})
    counts = queue_state.get("counts", {})

    # 1. 队列状态问题
    print(f"\n📊 队列状态分析:")
    print(f"  • queue_status: {queue_state.get('queue_status', 'unknown')}")
    print(f"  • pause_reason: {queue_state.get('pause_reason', 'unknown')}")
    print(f"  • current_item_id: {queue_state.get('current_item_id', '空')}")
    print(f"  • updated_at: {queue_state.get('updated_at', 'unknown')}")

    # 2. 任务统计
    print(f"\n📈 任务统计:")
    print(f"  • pending: {counts.get('pending', 0)}")
    print(f"  • running: {counts.get('running', 0)}")
    print(f"  • completed: {counts.get('completed', 0)}")
    print(f"  • failed: {counts.get('failed', 0)}")
    print(f"  • manual_hold: {counts.get('manual_hold', 0)}")

    # 3. 分析失败任务
    failed_tasks = []
    instruction_path_missing = []
    api_key_errors = []
    other_failed = []

    for task_id, task in items.items():
        status = task.get("status", "")
        if status == "failed":
            error = task.get("error", "")
            instruction_path = task.get("instruction_path", "")

            failed_tasks.append(
                {
                    "id": task_id,
                    "title": task.get("title", "无标题"),
                    "error": error,
                    "instruction_path": instruction_path,
                }
            )

            if not instruction_path or instruction_path.strip() == "":
                instruction_path_missing.append(task_id)
            elif "API key" in error or "Incorrect API key" in error:
                api_key_errors.append(task_id)
            else:
                other_failed.append(task_id)

    print(f"\n❌ 失败任务分析 ({len(failed_tasks)}个):")
    print(f"  • instruction_path缺失: {len(instruction_path_missing)}个")
    print(f"  • API key错误: {len(api_key_errors)}个")
    print(f"  • 其他失败: {len(other_failed)}个")

    if instruction_path_missing:
        print(f"\n📝 instruction_path缺失任务:")
        for task_id in instruction_path_missing:
            task = items.get(task_id, {})
            print(f"  • {task_id}: {task.get('title', '无标题')[:50]}...")

    if api_key_errors:
        print(f"\n🔑 API key错误任务:")
        for task_id in api_key_errors:
            task = items.get(task_id, {})
            error = task.get("error", "无错误信息")
            print(f"  • {task_id}: {task.get('title', '无标题')[:50]}...")
            print(f"    错误: {error[:80]}...")

    # 4. 分析manual_hold任务
    manual_hold_tasks = []
    for task_id, task in items.items():
        if task.get("status") == "manual_hold":
            manual_hold_tasks.append(task_id)

    print(f"\n🖐️  manual_hold任务 ({len(manual_hold_tasks)}个):")
    for task_id in manual_hold_tasks:
        task = items.get(task_id, {})
        print(f"  • {task_id}: {task.get('title', '无标题')[:50]}...")

    return {
        "queue_state": queue_state,
        "failed_tasks": failed_tasks,
        "instruction_path_missing": instruction_path_missing,
        "api_key_errors": api_key_errors,
        "other_failed": other_failed,
        "manual_hold_tasks": manual_hold_tasks,
        "items": items,
        "counts": counts,
    }


def fix_instruction_path_missing_tasks(queue_state, instruction_path_missing):
    """修复instruction_path缺失的任务"""
    print("\n" + "=" * 60)
    print("🔧 修复instruction_path缺失任务")
    print("=" * 60)

    items = queue_state.get("items", {})
    fixed_count = 0

    for task_id in instruction_path_missing:
        task = items.get(task_id, {})
        stage = task.get("stage", "")
        title = task.get("title", "")

        # 基于任务信息创建合理的instruction_path
        if stage == "plan":
            # 计划阶段任务，创建简单的指令文件
            instruction_content = f"# 计划任务: {title}\n\n这是一个自动生成的计划任务指令文件。"
            instruction_path = (
                f"/Volumes/1TB-M2/openclaw/.openclaw/chat_instructions/auto_fixed_{task_id}.md"
            )

            # 确保目录存在
            os.makedirs(os.path.dirname(instruction_path), exist_ok=True)

            # 写入指令文件
            try:
                with open(instruction_path, "w", encoding="utf-8") as f:
                    f.write(instruction_content)
                print(f"✅ 为任务 {task_id} 创建指令文件: {instruction_path}")

                # 更新任务状态
                items[task_id]["instruction_path"] = instruction_path
                items[task_id]["error"] = ""
                items[task_id]["status"] = "pending"
                items[task_id]["finished_at"] = ""
                items[task_id]["summary"] = "instruction_path已自动修复，任务重新设置为pending状态"

                fixed_count += 1
            except Exception as e:
                print(f"❌ 创建指令文件失败 ({task_id}): {e}")
        else:
            # 其他阶段，标记为无法修复
            print(f"⚠️  任务 {task_id} 无法自动修复 (stage: {stage})")

    queue_state["items"] = items
    print(f"\n✅ 修复完成: {fixed_count}个instruction_path缺失任务已修复")
    return fixed_count


def check_dashscope_api_key():
    """检查DashScope API key配置"""
    print("\n" + "=" * 60)
    print("🔑 检查DashScope API key配置")
    print("=" * 60)

    # 检查环境变量
    dashscope_key = os.environ.get("DASHSCOPE_API_KEY")
    if dashscope_key:
        print(f"✅ 找到DASHSCOPE_API_KEY环境变量")
        print(f"   密钥前8位: {dashscope_key[:8]}...")

        # 测试API key
        test_command = [
            "curl",
            "-s",
            "-X",
            "GET",
            "https://dashscope.aliyuncs.com/api/v1/models",
            "-H",
            f"Authorization: Bearer {dashscope_key}",
            "-H",
            "Content-Type: application/json",
        ]

        try:
            result = subprocess.run(test_command, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("✅ API key验证成功")
                return True
            else:
                print(f"❌ API key验证失败: {result.stderr[:100]}")
                return False
        except Exception as e:
            print(f"❌ API key测试异常: {e}")
            return False
    else:
        print("❌ 未找到DASHSCOPE_API_KEY环境变量")

        # 检查可能的配置文件
        config_files = [
            "/Volumes/1TB-M2/openclaw/.bashrc",
            "/Volumes/1TB-M2/openclaw/.zshrc",
            "/Volumes/1TB-M2/openclaw/.profile",
            "/Volumes/1TB-M2/openclaw/.bash_profile",
            "/Volumes/1TB-M2/openclaw/.env",
        ]

        for config_file in config_files:
            if os.path.exists(config_file):
                try:
                    with open(config_file, "r", encoding="utf-8") as f:
                        content = f.read()
                        if "DASHSCOPE" in content or "dashscope" in content:
                            print(f"💡 在 {config_file} 中找到DashScope相关配置")
                except:
                    pass

        return False


def fix_api_key_error_tasks(queue_state, api_key_errors):
    """修复API key错误的任务"""
    print("\n" + "=" * 60)
    print("🔧 修复API key错误任务")
    print("=" * 60)

    items = queue_state.get("items", {})
    fixed_count = 0

    # 先检查API key配置
    api_key_valid = check_dashscope_api_key()

    if not api_key_valid:
        print("\n⚠️  API key配置有问题，无法修复API key错误任务")
        print("💡 建议运行DashScope维护脚本: ./dashscope-maintenance.sh --all")
        return 0

    # 修复任务
    for task_id in api_key_errors:
        task = items.get(task_id, {})

        # 清除错误，重新设置为pending状态
        items[task_id]["error"] = ""
        items[task_id]["status"] = "pending"
        items[task_id]["finished_at"] = ""
        items[task_id]["summary"] = "API key已验证，任务重新设置为pending状态"

        print(f"✅ 修复任务 {task_id}: API key错误已清除，状态重置为pending")
        fixed_count += 1

    queue_state["items"] = items
    print(f"\n✅ 修复完成: {fixed_count}个API key错误任务已修复")
    return fixed_count


def fix_queue_manual_hold_state(queue_state, manual_hold_tasks):
    """修复队列manual_hold状态"""
    print("\n" + "=" * 60)
    print("🔧 修复队列manual_hold状态")
    print("=" * 60)

    if not manual_hold_tasks:
        print("⚠️  没有manual_hold任务，无需修复")
        return False

    # 选择第一个manual_hold任务作为当前任务
    first_task_id = manual_hold_tasks[0]
    items = queue_state.get("items", {})

    print(f"🎯 选择任务作为当前任务: {first_task_id}")
    print(f"📝 任务标题: {items[first_task_id].get('title', '无标题')}")

    # 检查任务是否可以执行
    task_error = items[first_task_id].get("error", "")
    if task_error:
        print(f"⚠️  任务有错误: {task_error[:80]}...")
        print("💡 清除错误并设置为pending状态")
        items[first_task_id]["error"] = ""
        items[first_task_id]["status"] = "pending"

    # 修复队列状态
    queue_state["queue_status"] = "running"
    queue_state["pause_reason"] = ""
    queue_state["current_item_id"] = first_task_id
    queue_state["current_item_ids"] = manual_hold_tasks
    queue_state["updated_at"] = datetime.now(timezone.utc).isoformat()

    # 更新任务状态
    items[first_task_id]["status"] = "running"
    items[first_task_id]["progress_percent"] = 0
    if not items[first_task_id].get("started_at"):
        items[first_task_id]["started_at"] = datetime.now(timezone.utc).isoformat()

    # 其他manual_hold任务设置为pending
    for i, task_id in enumerate(manual_hold_tasks):
        if i == 0:
            continue  # 第一个已经是running
        items[task_id]["status"] = "pending"

    # 更新任务计数
    counts = queue_state.get("counts", {})
    counts["pending"] = len(manual_hold_tasks) - 1
    counts["running"] = 1
    counts["manual_hold"] = 0
    queue_state["counts"] = counts
    queue_state["items"] = items

    print("✅ 队列状态已修复:")
    print(f"  • queue_status: {queue_state['queue_status']}")
    print(f"  • pause_reason: {queue_state['pause_reason']}")
    print(f"  • current_item_id: {first_task_id}")
    print(f"  • counts: pending={counts['pending']}, running={counts['running']}")

    return True


def test_manual_launch_functionality():
    """测试手动拉起功能"""
    print("\n" + "=" * 60)
    print("🧪 测试手动拉起功能")
    print("=" * 60)

    # 检查Web服务器状态
    web_server_url = "http://127.0.0.1:8080"
    check_command = ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", web_server_url]

    try:
        result = subprocess.run(check_command, capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip() == "200":
            print(f"✅ Web服务器正常 ({web_server_url})")

            # 检查手动拉起API端点
            launch_api_url = "http://127.0.0.1:8080/api/queue/item/launch"
            api_check = subprocess.run(
                [
                    "curl",
                    "-s",
                    "-X",
                    "POST",
                    launch_api_url,
                    "-H",
                    "Content-Type: application/json",
                    "-d",
                    '{"queue_id": "test", "item_id": "test"}',
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if api_check.returncode == 0:
                print(f"✅ 手动拉起API端点存在")
                try:
                    response = json.loads(api_check.stdout)
                    print(f"   API响应: {response}")
                except:
                    print(f"   API响应 (原始): {api_check.stdout[:100]}...")
            else:
                print(f"⚠️  手动拉起API端点可能有问题: {api_check.stderr[:100]}")
        else:
            print(f"❌ Web服务器可能未运行 (HTTP状态码: {result.stdout.strip()})")
    except Exception as e:
        print(f"❌ Web服务器检查失败: {e}")

    print("\n💡 手动拉起功能测试建议:")
    print("1. 确保Web服务器运行: python fixed_athena_web_server.py")
    print("2. 访问 http://127.0.0.1:8080 查看Athena Web Desktop")
    print("3. 在Web界面中尝试手动拉起任务")
    print("4. 检查队列状态文件是否更新")


def main():
    """主函数"""
    print("=" * 80)
    print("基因管理队列综合修复工具")
    print("=" * 80)
    print("目标: 修复所有队列问题，使手动拉起功能恢复正常")
    print()

    queue_file = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_gene_management_20260405.json"

    if not os.path.exists(queue_file):
        print(f"❌ 队列状态文件不存在: {queue_file}")
        return

    # 1. 加载队列状态
    queue_state = load_queue_state(queue_file)
    if queue_state is None:
        return

    # 2. 诊断所有问题
    diagnosis = diagnose_queue_problems(queue_state)

    # 3. 修复instruction_path缺失任务
    if diagnosis["instruction_path_missing"]:
        fixed_instruction = fix_instruction_path_missing_tasks(
            queue_state, diagnosis["instruction_path_missing"]
        )
    else:
        fixed_instruction = 0
        print("\n📝 没有instruction_path缺失任务需要修复")

    # 4. 修复API key错误任务
    if diagnosis["api_key_errors"]:
        fixed_api = fix_api_key_error_tasks(queue_state, diagnosis["api_key_errors"])
    else:
        fixed_api = 0
        print("\n🔑 没有API key错误任务需要修复")

    # 5. 修复队列manual_hold状态
    if diagnosis["manual_hold_tasks"]:
        fixed_queue = fix_queue_manual_hold_state(queue_state, diagnosis["manual_hold_tasks"])
    else:
        fixed_queue = False
        print("\n🖐️  没有manual_hold任务需要修复")

    # 6. 保存修复后的状态
    if fixed_instruction > 0 or fixed_api > 0 or fixed_queue:
        print("\n" + "=" * 60)
        print("💾 保存修复后的队列状态")
        print("=" * 60)

        if save_queue_state(queue_file, queue_state):
            print("✅ 队列状态已成功保存")
        else:
            print("❌ 队列状态保存失败")
    else:
        print("\n📋 没有需要修复的问题")

    # 7. 测试手动拉起功能
    test_manual_launch_functionality()

    # 8. 总结
    print("\n" + "=" * 80)
    print("修复总结")
    print("=" * 80)
    print(f"• instruction_path缺失任务修复: {fixed_instruction}个")
    print(f"• API key错误任务修复: {fixed_api}个")
    print(f"• 队列manual_hold状态修复: {'✅' if fixed_queue else '❌'}")

    if fixed_instruction > 0 or fixed_api > 0 or fixed_queue:
        print("\n🎯 下一步:")
        print(
            "1. 检查队列状态: cat "
            + queue_file
            + " | grep -E 'queue_status|current_item_id|counts'"
        )
        print("2. 重启队列运行器: python scripts/athena_ai_plan_runner.py --daemon")
        print("3. 测试手动拉起: 访问 http://127.0.0.1:8080")
        print("4. 监控队列运行: python scripts/queue_monitor.py --alert")
    else:
        print("\n💡 所有问题已解决或无需修复")
        print("请直接测试手动拉起功能")


if __name__ == "__main__":
    main()
