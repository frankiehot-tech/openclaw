#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py health 或 governance_cli.py queue protect
"""
基因管理队列执行监控脚本
实时监控执行状态，自动调整策略
"""

import json
import time
from datetime import datetime, timedelta


class GeneManagementMonitor:
    """基因管理队列执行监控器"""

    def __init__(self):
        self.queue_state_file = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_gene_management_20260405.json"
        self.log_file = "/Volumes/1TB-M2/openclaw/logs/gene_management_monitor.log"
        self.start_time = datetime.now()
        self.expected_duration = timedelta(hours=2, minutes=45)  # 2 小时 45 分钟

    def log_message(self, message, level="INFO"):
        """记录日志消息"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(log_entry)

        # 同时写入日志文件
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_entry + "\n")
        except Exception as e:
            print(f"警告：无法写入日志文件：{e}")

    def load_queue_state(self):
        """加载队列状态"""
        try:
            with open(self.queue_state_file, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            self.log_message(f"队列状态文件未找到：{self.queue_state_file}", "ERROR")
            return None
        except json.JSONDecodeError as e:
            self.log_message(f"队列状态文件格式错误：{e}", "ERROR")
            return None

    def display_status(self, state):
        """显示当前状态"""
        print("\n" + "=" * 80)
        print("🧬 Athena/Open Human 基因管理队列执行状态")
        print("=" * 80)

        # 基本信息
        print("\n📊 队列信息:")
        print(f"  队列 ID: {state.get('queue_id', 'N/A')}")
        print(f"  队列名称：{state.get('name', 'N/A')}")
        print(f"  队列状态：{state.get('queue_status', 'N/A')}")

        # 当前任务
        current_item = state.get("current_item_id", "N/A")
        print(f"\n🎯 当前任务：{current_item}")

        # 任务计数
        counts = state.get("counts", {})
        print("\n📈 任务统计:")
        print(f"  运行中：{counts.get('running', 0)}")
        print(f"  等待中：{counts.get('pending', 0)}")
        print(f"  已完成：{counts.get('completed', 0)}")
        print(f"  失败数：{counts.get('failed', 0)}")

        # 执行进度
        total_tasks = 4  # 总共 4 个任务
        completed = counts.get("completed", 0)
        progress = (completed / total_tasks) * 100
        print(f"\n📊 执行进度：{completed}/{total_tasks} ({progress:.1f}%)")

        # 运行时间
        elapsed = datetime.now() - self.start_time
        print(f"\n⏱️  运行时间：{elapsed}")
        print(f"   预计总时长：{self.expected_duration}")

        # 任务详情
        print("\n📋 任务详情:")
        items = state.get("items", {})
        for task_id, task in items.items():
            status = task.get("status", "unknown")
            phase = task.get("metadata", {}).get("phase", "Unknown")
            priority = task.get("metadata", {}).get("priority", "Unknown")

            # 状态图标
            status_icon = {"running": "🔄", "pending": "⏳", "completed": "✅", "failed": "❌"}.get(
                status, "❓"
            )

            print(f"  {status_icon} [{phase}] {task.get('title', task_id)} (优先级：{priority})")

        # 预计完成时间
        if completed > 0:
            avg_time_per_task = elapsed / completed
            remaining_tasks = total_tasks - completed
            estimated_remaining = avg_time_per_task * remaining_tasks
            estimated_completion = datetime.now() + estimated_remaining
            print(f"\n⏰ 预计完成时间：{estimated_completion.strftime('%H:%M:%S')}")

        print("\n" + "=" * 80)

    def check_anomalies(self, state):
        """检查异常情况"""
        counts = state.get("counts", {})

        # 检查失败任务
        if counts.get("failed", 0) > 0:
            self.log_message(f"⚠️  警告：有 {counts['failed']} 个任务失败！", "WARNING")
            self.suggest_recovery_action()

        # 检查运行时间
        elapsed = datetime.now() - self.start_time
        if elapsed > self.expected_duration * 1.5:
            self.log_message("⚠️  警告：执行时间超过预计时间 50%！", "WARNING")
            self.suggest_time_adjustment()

        # 检查队列状态
        if state.get("queue_status") == "paused":
            self.log_message("⚠️  警告：队列已暂停！", "WARNING")
            self.suggest_resume_queue()

    def suggest_recovery_action(self):
        """建议恢复操作"""
        print("\n💡 建议操作:")
        print("  1. 查看失败任务的详细日志")
        print("  2. 分析失败原因")
        print("  3. 修复问题后重新执行失败任务")
        print("  4. 命令：python3 scripts/athena_ai_plan_runner.py --retry-failed")

    def suggest_time_adjustment(self):
        """建议时间调整"""
        print("\n💡 建议操作:")
        print("  1. 当前执行时间远超预期")
        print("  2. 检查是否有任务卡住")
        print("  3. 考虑暂停队列，分析瓶颈")
        print("  4. 调整后续阶段的预估时间")

    def suggest_resume_queue(self):
        """建议恢复队列"""
        print("\n💡 建议操作:")
        print("  1. 队列当前处于暂停状态")
        print("  2. 检查暂停原因")
        print("  3. 解决问题后恢复队列执行")
        print("  4. 命令：python3 scripts/athena_ai_plan_runner.py --resume")

    def check_completion(self, state):
        """检查是否完成"""
        counts = state.get("counts", {})
        total_tasks = 4

        if counts.get("completed", 0) >= total_tasks:
            self.log_message("🎉 所有任务执行完成！", "SUCCESS")
            self.generate_completion_report()
            return True

        return False

    def generate_completion_report(self):
        """生成完成报告"""
        print("\n" + "=" * 80)
        print("🎉 Athena/Open Human 基因管理系统实施完成报告")
        print("=" * 80)

        elapsed = datetime.now() - self.start_time

        print("\n📊 执行总结:")
        print(f"  开始时间：{self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  完成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  总耗时：{elapsed}")
        print(f"  预计时长：{self.expected_duration}")

        # 计算效率
        efficiency = (self.expected_duration / elapsed) * 100 if elapsed > timedelta(0) else 0
        print(f"  执行效率：{efficiency:.1f}%")

        print("\n✅ 实施成果:")
        print("  1. 基因序列基础设施搭建完成")
        print("  2. CLI 命令框架实现完成")
        print("  3. 队列系统集成配置就绪")
        print("  4. 实施效果审计通过")

        print("\n📋 下一步建议:")
        print("  1. 验证各阶段实施效果")
        print("  2. 查看审计报告")
        print("  3. 规划 G1+ 阶段演进路线")
        print("  4. 开始实际基因管理操作")

        print("\n" + "=" * 80)

    def monitor(self, check_interval=30):
        """启动监控"""
        self.log_message("🔍 开始监控基因管理队列执行...")

        try:
            while True:
                # 加载队列状态
                state = self.load_queue_state()

                if state:
                    # 显示状态
                    self.display_status(state)

                    # 检查异常
                    self.check_anomalies(state)

                    # 检查完成
                    if self.check_completion(state):
                        break

                # 等待下次检查
                time.sleep(check_interval)

        except KeyboardInterrupt:
            print("\n\n👋 监控已停止")
            self.log_message("监控被用户中断", "INFO")
        except Exception as e:
            self.log_message(f"监控异常：{e}", "ERROR")
            raise


def main():
    """主函数"""
    print("=" * 80)
    print("🧬 Athena/Open Human 基因管理队列执行监控器")
    print("=" * 80)
    print("\n按 Ctrl+C 停止监控")
    print("日志文件：/Volumes/1TB-M2/openclaw/logs/gene_management_monitor.log")
    print("检查间隔：30 秒\n")

    monitor = GeneManagementMonitor()
    monitor.monitor()


if __name__ == "__main__":
    main()
