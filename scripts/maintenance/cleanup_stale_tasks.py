#!/usr/bin/env python3
"""清理陈旧队列任务脚本"""

import json
import os
import time
from datetime import datetime, timedelta


def analyze_stale_tasks():
    """分析陈旧任务"""

    print("🔍 分析陈旧队列任务...")

    stale_tasks = []
    queue_dir = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/"

    for file_name in os.listdir(queue_dir):
        if file_name.endswith(".json"):
            file_path = os.path.join(queue_dir, file_name)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                for task_id, task_data in data.get("items", {}).items():
                    status = task_data.get("status", "")
                    error = task_data.get("error", "")
                    started_at = task_data.get("started_at", "")
                    runner_heartbeat_at = task_data.get("runner_heartbeat_at", "")

                    # 检查是否为陈旧任务
                    if "stale" in error.lower() or "no heartbeat" in error.lower():
                        stale_tasks.append(
                            {
                                "queue_file": file_name,
                                "task_id": task_id,
                                "task_title": task_data.get("title", ""),
                                "status": status,
                                "error": error,
                                "started_at": started_at,
                                "runner_heartbeat_at": runner_heartbeat_at,
                                "file_path": file_path,
                            }
                        )

            except Exception as e:
                print(f"❌ 分析队列文件失败: {file_name} - {e}")

    return stale_tasks


def cleanup_stale_tasks(stale_tasks):
    """清理陈旧任务"""

    print("\n🧹 清理陈旧任务...")

    if not stale_tasks:
        print("✅ 未发现陈旧任务")
        return 0

    cleaned_count = 0

    for task_info in stale_tasks:
        print(f"\n处理任务: {task_info['task_title']}")
        print(f"  队列: {task_info['queue_file']}")
        print(f"  错误: {task_info['error']}")
        print(f"  开始时间: {task_info['started_at']}")

        try:
            # 读取队列文件
            with open(task_info["file_path"], "r", encoding="utf-8") as f:
                data = json.load(f)

            task_id = task_info["task_id"]

            if task_id in data.get("items", {}):
                # 更新任务状态为failed（如果还不是failed）
                if data["items"][task_id].get("status") != "failed":
                    data["items"][task_id]["status"] = "failed"
                    data["items"][task_id]["finished_at"] = datetime.now().isoformat()

                # 保存更新后的队列文件
                with open(task_info["file_path"], "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                print(f"  ✅ 已标记为failed状态")
                cleaned_count += 1
            else:
                print(f"  ❌ 任务不存在于队列文件中")

        except Exception as e:
            print(f"  ❌ 清理失败: {e}")

    return cleaned_count


def verify_cleanup():
    """验证清理结果"""

    print("\n🔍 验证清理结果...")

    # 重新分析陈旧任务
    stale_tasks = analyze_stale_tasks()

    if not stale_tasks:
        print("✅ 所有陈旧任务已清理")
        return True
    else:
        print(f"❌ 仍有 {len(stale_tasks)} 个陈旧任务:")
        for task in stale_tasks:
            print(f"  - {task['task_title']}: {task['error']}")
        return False


def main():
    """主函数"""

    print("=" * 60)
    print("陈旧队列任务清理工具")
    print("=" * 60)

    # 分析陈旧任务
    stale_tasks = analyze_stale_tasks()

    if stale_tasks:
        print(f"\n📊 发现 {len(stale_tasks)} 个陈旧任务:")
        for i, task in enumerate(stale_tasks, 1):
            print(f"\n{i}. {task['task_title']}")
            print(f"   队列: {task['queue_file']}")
            print(f"   错误: {task['error']}")
            print(f"   开始时间: {task['started_at']}")
    else:
        print("\n✅ 未发现陈旧任务")

    # 清理陈旧任务
    cleaned_count = cleanup_stale_tasks(stale_tasks)

    # 验证清理结果
    success = verify_cleanup()

    print("\n" + "=" * 60)
    print("清理完成！")
    print("=" * 60)

    print(f"\n📊 清理统计:")
    print(f"  发现陈旧任务: {len(stale_tasks)} 个")
    print(f"  清理成功: {cleaned_count} 个")

    if success:
        print("\n🎉 所有陈旧任务已成功清理")
    else:
        print("\n⚠️ 仍有陈旧任务需要处理")

    print("\n下一步建议:")
    print("1. 重新执行失败的任务（如果需要）")
    print("2. 监控队列运行状态")
    print("3. 定期运行此清理工具")


if __name__ == "__main__":
    main()
