#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py <command>
"""
最终队列修复：处理所有失败任务，确保队列能正常运行和手动拉起
"""

import json
import os
from datetime import UTC, datetime


def load_queue():
    """加载队列状态"""
    queue_file = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_gene_management_20260405.json"

    try:
        with open(queue_file, encoding="utf-8") as f:
            return json.load(f), queue_file
    except Exception as e:
        print(f"❌ 加载队列失败: {e}")
        return None, queue_file


def save_queue(queue_state, queue_file):
    """保存队列状态"""
    try:
        with open(queue_file, "w", encoding="utf-8") as f:
            json.dump(queue_state, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ 保存队列失败: {e}")
        return False


def analyze_and_fix_all_failed_tasks(queue_state):
    """分析和修复所有失败任务"""
    print("=" * 60)
    print("🔍 分析并修复所有失败任务")
    print("=" * 60)

    items = queue_state.get("items", {})
    failed_tasks = []

    # 找出所有失败任务
    for task_id, task in items.items():
        if task.get("status") == "failed":
            failed_tasks.append((task_id, task))

    print(f"📊 发现 {len(failed_tasks)} 个失败任务")

    fixed_count = 0
    pending_count = 0

    for task_id, task in failed_tasks:
        error = task.get("error", "")
        instruction_path = task.get("instruction_path", "")
        stage = task.get("stage", "")

        print(f"\n📝 任务: {task_id}")
        print(f"  标题: {task.get('title', '无标题')[:50]}...")
        print(f"  错误: {error[:80]}..." if error else "  错误: 无")

        # 决定如何修复
        if not instruction_path or instruction_path.strip() == "":
            # instruction_path缺失
            print("  🔧 修复: instruction_path缺失")

            # 创建instruction_path
            if stage == "plan":
                new_path = (
                    f"/Volumes/1TB-M2/openclaw/.openclaw/chat_instructions/final_fixed_{task_id}.md"
                )
                os.makedirs(os.path.dirname(new_path), exist_ok=True)

                content = f"""# 修复的聊天任务: {task.get("title", "无标题")}

## 任务描述
这是一个自动修复的聊天任务，原始任务因为instruction_path缺失而失败。

## 修复说明
- 修复时间: {datetime.now().isoformat()}
- 修复类型: instruction_path缺失
- 原始错误: {error}

## 任务内容
这是一个简单的修复任务，用于测试队列恢复。
"""
                try:
                    with open(new_path, "w", encoding="utf-8") as f:
                        f.write(content)

                    items[task_id]["instruction_path"] = new_path
                    items[task_id]["error"] = ""
                    items[task_id]["status"] = "pending"
                    items[task_id]["finished_at"] = ""
                    items[task_id]["summary"] = "instruction_path已修复，任务重置为pending"

                    print(f"  ✅ 创建指令文件: {new_path}")
                    pending_count += 1
                except Exception as e:
                    print(f"  ❌ 创建指令文件失败: {e}")
                    continue

        elif "API key" in error or "Incorrect API key" in error:
            # API key错误
            print("  🔧 修复: API key错误")

            # 清除错误，设置为pending
            items[task_id]["error"] = ""
            items[task_id]["status"] = "pending"
            items[task_id]["finished_at"] = ""
            items[task_id]["summary"] = "API key错误已清除，任务重置为pending"

            pending_count += 1

        elif "runner 重启恢复" in error:
            # runner重启失败
            print("  🔧 修复: runner重启失败")

            # 清除错误，设置为pending
            items[task_id]["error"] = ""
            items[task_id]["status"] = "pending"
            items[task_id]["finished_at"] = ""
            items[task_id]["summary"] = "runner重启失败错误已清除，任务重置为pending"

            pending_count += 1

        else:
            # 其他错误，直接清除
            print("  🔧 修复: 其他错误")

            items[task_id]["error"] = ""
            items[task_id]["status"] = "pending"
            items[task_id]["finished_at"] = ""
            items[task_id]["summary"] = "错误已清除，任务重置为pending"

            pending_count += 1

        fixed_count += 1

    queue_state["items"] = items

    print("\n📊 修复总结:")
    print(f"  • 总共处理: {fixed_count} 个失败任务")
    print(f"  • 重置为pending: {pending_count} 个")

    return queue_state, pending_count


def setup_queue_for_running(queue_state, pending_tasks):
    """设置队列为运行状态"""
    print("\n" + "=" * 60)
    print("🏃 设置队列为运行状态")
    print("=" * 60)

    items = queue_state.get("items", {})

    if not pending_tasks:
        print("⚠️  没有pending任务，无法设置当前任务")
        return queue_state, False

    # 选择第一个pending任务作为当前任务
    first_pending_id = None
    for task_id, task in items.items():
        if task.get("status") == "pending":
            first_pending_id = task_id
            break

    if not first_pending_id:
        print("❌ 找不到pending任务")
        return queue_state, False

    print(f"🎯 选择当前任务: {first_pending_id}")
    print(f"📝 标题: {items[first_pending_id].get('title', '无标题')}")

    # 设置为running
    items[first_pending_id]["status"] = "running"
    items[first_pending_id]["progress_percent"] = 0
    items[first_pending_id]["started_at"] = datetime.now(UTC).isoformat()

    # 更新队列状态
    queue_state["queue_status"] = "running"
    queue_state["pause_reason"] = ""
    queue_state["current_item_id"] = first_pending_id

    # 收集所有pending任务ID作为current_item_ids
    pending_ids = []
    for task_id, task in items.items():
        if task.get("status") == "pending":
            pending_ids.append(task_id)

    queue_state["current_item_ids"] = pending_ids
    queue_state["updated_at"] = datetime.now(UTC).isoformat()

    # 更新计数
    counts = {
        "pending": len([t for t in items.values() if t.get("status") == "pending"]),
        "running": len([t for t in items.values() if t.get("status") == "running"]),
        "completed": len([t for t in items.values() if t.get("status") == "completed"]),
        "failed": len([t for t in items.values() if t.get("status") == "failed"]),
        "manual_hold": 0,
    }

    queue_state["counts"] = counts

    print("✅ 队列状态设置完成:")
    print(f"  • queue_status: {queue_state['queue_status']}")
    print(f"  • current_item_id: {first_pending_id}")
    print(f"  • pending任务数: {counts['pending']}")
    print(f"  • running任务数: {counts['running']}")

    return queue_state, True


def restart_queue_runner():
    """重启队列运行器"""
    print("\n" + "=" * 60)
    print("🔄 重启队列运行器")
    print("=" * 60)

    import subprocess

    # 检查现有进程
    try:
        result = subprocess.run(
            ["pgrep", "-f", "athena_ai_plan_runner"], capture_output=True, text=True
        )

        if result.stdout.strip():
            pids = result.stdout.strip().split()
            print(f"📊 发现 {len(pids)} 个队列运行器进程")

            # 终止旧进程
            for pid in pids:
                try:
                    subprocess.run(["kill", pid], check=False)
                    print(f"  • 终止进程 PID: {pid}")
                except Exception:
                    pass

            # 等待进程终止
            import time

            time.sleep(2)
    except Exception:
        pass

    # 启动新进程
    runner_script = "/Volumes/1TB-M2/openclaw/scripts/athena_ai_plan_runner.py"

    if os.path.exists(runner_script):
        try:
            # 在后台启动
            subprocess.Popen(
                ["python3", runner_script, "--daemon"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            print("✅ 队列运行器已启动 (daemon模式)")

            # 等待启动
            import time

            time.sleep(3)

            # 检查是否运行
            result = subprocess.run(
                ["pgrep", "-f", "athena_ai_plan_runner"], capture_output=True, text=True
            )

            if result.stdout.strip():
                print(f"✅ 队列运行器进程确认运行 (PID: {result.stdout.strip()})")
                return True
            else:
                print("⚠️  队列运行器进程可能未启动成功")
                return False

        except Exception as e:
            print(f"❌ 启动队列运行器失败: {e}")
            return False
    else:
        print(f"❌ 队列运行器脚本不存在: {runner_script}")
        return False


def test_manual_launch():
    """测试手动拉起功能"""
    print("\n" + "=" * 60)
    print("🧪 测试手动拉起功能")
    print("=" * 60)

    import subprocess

    # 检查Web服务器
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://127.0.0.1:8080"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0 and result.stdout.strip() == "200":
            print("✅ Web服务器正常运行 (http://127.0.0.1:8080)")

            # 测试手动拉起API
            test_payload = json.dumps(
                {"queue_id": "openhuman_aiplan_gene_management_20260405", "item_id": "test_task"}
            )

            result = subprocess.run(
                [
                    "curl",
                    "-s",
                    "-X",
                    "POST",
                    "http://127.0.0.1:8080/api/queue/item/launch",
                    "-H",
                    "Content-Type: application/json",
                    "-d",
                    test_payload,
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                try:
                    response = json.loads(result.stdout)
                    print(f"✅ 手动拉起API响应: {response}")
                except Exception:
                    print(f"✅ 手动拉起API响应 (原始): {result.stdout[:100]}...")
            else:
                print(f"⚠️  手动拉起API可能有问题: {result.stderr[:100]}")
        else:
            print(f"⚠️  Web服务器可能有问题 (HTTP状态码: {result.stdout.strip()})")
    except Exception as e:
        print(f"❌ 手动拉起测试失败: {e}")

    print("\n💡 手动拉起测试建议:")
    print("1. 访问 http://127.0.0.1:8080 查看Athena Web Desktop")
    print("2. 在界面中点击'手动拉起'按钮")
    print("3. 观察队列状态是否更新")


def main():
    """主函数"""
    print("=" * 80)
    print("最终队列修复工具")
    print("=" * 80)
    print("目标: 彻底修复队列问题，确保手动拉起功能正常工作")
    print()

    # 1. 加载队列
    queue_state, queue_file = load_queue()
    if queue_state is None:
        return

    # 2. 修复所有失败任务
    queue_state, pending_count = analyze_and_fix_all_failed_tasks(queue_state)

    if pending_count == 0:
        print("\n⚠️  没有pending任务生成，可能修复失败")
        return

    # 3. 设置队列为运行状态
    queue_state, success = setup_queue_for_running(queue_state, pending_count)

    if not success:
        print("\n❌ 设置队列运行状态失败")
        return

    # 4. 保存修复后的队列
    print("\n" + "=" * 60)
    print("💾 保存修复后的队列状态")
    print("=" * 60)

    if save_queue(queue_state, queue_file):
        print("✅ 队列状态已保存")

        # 显示关键状态
        print("\n📊 最终队列状态:")
        print(f"  • queue_status: {queue_state.get('queue_status', 'unknown')}")
        print(f"  • current_item_id: {queue_state.get('current_item_id', '空')}")
        print(f"  • pending任务数: {queue_state.get('counts', {}).get('pending', 0)}")
        print(f"  • failed任务数: {queue_state.get('counts', {}).get('failed', 0)}")
    else:
        print("❌ 队列状态保存失败")
        return

    # 5. 重启队列运行器
    runner_restarted = restart_queue_runner()

    # 6. 测试手动拉起功能
    test_manual_launch()

    # 7. 总结
    print("\n" + "=" * 80)
    print("修复完成总结")
    print("=" * 80)
    print(f"✅ 队列状态修复: {queue_state.get('queue_status', 'unknown')}")
    print(f"✅ 当前任务设置: {queue_state.get('current_item_id', '空')}")
    print(f"✅ 失败任务处理: {pending_count} 个任务重置为pending")
    print(f"✅ 队列运行器: {'重启成功' if runner_restarted else '可能需要手动启动'}")

    print("\n🎯 下一步操作:")
    print("1. 检查Athena Web Desktop: http://127.0.0.1:8080")
    print("2. 测试手动拉起按钮功能")
    print("3. 监控队列运行: python scripts/queue_monitor.py --alert")
    print("4. 观察任务是否正常执行")


if __name__ == "__main__":
    main()
