#!/usr/bin/env python3
"""
队列状态保护守护进程
防止队列状态被意外重置
"""

import json
import os
import signal
import time
from datetime import datetime
from pathlib import Path


class QueueStateProtector:
    def __init__(self):
        self.queue_file = Path(
            "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_plan_manual_20260328.json"
        )
        self.protection_file = Path("/Volumes/1TB-M2/openclaw/.openclaw/queue_protection.lock")
        self.running = True

        # 设置信号处理
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        print(f"收到信号 {signum}，正在停止保护进程...")
        self.running = False

    def protect_queue_state(self):
        """保护队列状态不被重置"""

        if not self.queue_file.exists():
            print(f"❌ 队列状态文件不存在: {self.queue_file}")
            return False

        try:
            with open(self.queue_file, encoding="utf-8") as f:
                queue_state = json.load(f)

            # 检查队列状态是否异常
            current_status = queue_state.get("queue_status", "")
            current_item = queue_state.get("current_item_id", "")

            # 如果队列状态异常，自动修复
            if current_status in ["manual_hold", "stopped", "unknown"] and current_item == "":
                print(f"⚠️ [{datetime.now()}] 检测到队列状态异常，正在修复...")

                # 查找可执行任务
                items = queue_state.get("items", {})
                executable_tasks = []

                for task_id, task in items.items():
                    task_status = task.get("status", "")
                    if task_status in ["pending", ""]:
                        executable_tasks.append(task_id)

                if executable_tasks:
                    # 修复队列状态
                    queue_state["queue_status"] = "running"
                    queue_state["current_item_id"] = executable_tasks[0]
                    queue_state["current_item_ids"] = executable_tasks
                    queue_state["pause_reason"] = ""
                    queue_state["updated_at"] = datetime.now().isoformat()

                    # 保存修复后的状态
                    with open(self.queue_file, "w", encoding="utf-8") as f:
                        json.dump(queue_state, f, indent=2, ensure_ascii=False)

                    print(f"✅ [{datetime.now()}] 队列状态已修复，当前任务: {executable_tasks[0]}")
                    return True
                else:
                    print(f"⚠️ [{datetime.now()}] 队列没有可执行任务")
                    return False
            else:
                print(f"✅ [{datetime.now()}] 队列状态正常")
                return True

        except Exception as e:
            print(f"❌ [{datetime.now()}] 保护队列状态失败: {e}")
            return False

    def run(self):
        """运行保护进程"""

        print(f"🚀 [{datetime.now()}] 启动队列状态保护守护进程")

        # 创建保护锁文件
        try:
            self.protection_file.parent.mkdir(parents=True, exist_ok=True)
            self.protection_file.write_text(str(os.getpid()) + "\n", encoding="utf-8")
        except Exception as e:
            print(f"❌ 创建保护锁文件失败: {e}")

        # 保护循环
        while self.running:
            self.protect_queue_state()

            # 等待30秒再次检查
            for _i in range(30):
                if not self.running:
                    break
                time.sleep(1)

        # 清理保护锁文件
        try:
            if self.protection_file.exists():
                self.protection_file.unlink()
        except Exception:
            pass

        print(f"🛑 [{datetime.now()}] 队列状态保护守护进程已停止")


if __name__ == "__main__":
    protector = QueueStateProtector()
    protector.run()
