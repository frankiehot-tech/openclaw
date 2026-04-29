#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py <command>
"""
快速流量切换测试脚本
验证系统就绪状态，执行简化的批次1测试
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

import psutil


class QuickTrafficSwitchTest:
    """快速流量切换测试"""

    def __init__(self):
        self.base_dir = Path("/Volumes/1TB-M2/openclaw")
        self.queue_dir = self.base_dir / ".openclaw" / "plan_queue"
        self.test_duration = 120  # 2分钟测试（简化版）

    def check_system_health(self):
        """检查系统健康状态"""
        print("🔍 检查系统健康状态...")

        checks = []

        # 1. 检查队列运行器
        queue_runner_found = False
        queue_runner_pid = None
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if proc.info["cmdline"] and any(
                    "athena_ai_plan_runner.py" in arg for arg in proc.info["cmdline"]
                ):
                    queue_runner_found = True
                    queue_runner_pid = proc.info["pid"]
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        checks.append(
            {
                "name": "队列运行器",
                "status": "✅" if queue_runner_found else "❌",
                "details": f"PID: {queue_runner_pid}" if queue_runner_found else "未找到",
            }
        )

        # 2. 检查Web仪表板
        web_dashboard_found = False
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if proc.info["cmdline"] and any(
                    "athena_web_desktop_compat.py" in arg for arg in proc.info["cmdline"]
                ):
                    web_dashboard_found = True
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        checks.append(
            {
                "name": "Web仪表板",
                "status": "✅" if web_dashboard_found else "⚠️",
                "details": "运行中" if web_dashboard_found else "未运行（可选）",
            }
        )

        # 3. 检查监控仪表板
        monitor_dashboard_found = False
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if proc.info["cmdline"] and any(
                    "queue_monitor_dashboard.py" in arg for arg in proc.info["cmdline"]
                ):
                    monitor_dashboard_found = True
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        checks.append(
            {
                "name": "监控仪表板",
                "status": "✅" if monitor_dashboard_found else "⚠️",
                "details": "运行中" if monitor_dashboard_found else "未运行（可选）",
            }
        )

        # 4. 检查队列文件
        queue_files = list(self.queue_dir.glob("*.json"))
        checks.append(
            {
                "name": "队列文件",
                "status": "✅" if queue_files else "⚠️",
                "details": (
                    f"找到 {len(queue_files)} 个队列文件" if queue_files else "未找到队列文件"
                ),
            }
        )

        # 5. 检查系统资源
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()

        cpu_status = "✅" if cpu_percent < 80 else "⚠️"
        memory_status = "✅" if memory.percent < 80 else "⚠️"

        checks.append(
            {
                "name": "系统资源",
                "status": f"{cpu_status}/{memory_status}",
                "details": f"CPU: {cpu_percent:.1f}%, 内存: {memory.percent:.1f}%",
            }
        )

        # 打印检查结果
        print("\n📋 健康检查结果:")
        for check in checks:
            print(f"  {check['status']} {check['name']}: {check['details']}")

        # 计算总体健康状态
        # 调试：打印每个检查的状态
        print("\n🔧 健康检查调试信息:")
        for check in checks:
            # 系统资源的状态可能是"✅/✅"，所以检查是否包含✅或⚠️
            status_contains_ok = "✅" in check["status"] or "⚠️" in check["status"]
            not_queue_failed = not (check["name"] == "队列运行器" and "❌" in check["status"])
            print(
                f"  {check['name']}: status={check['status']}, status_contains_ok={status_contains_ok}, not_queue_failed={not_queue_failed}"
            )

        all_ok = True
        for check in checks:
            # 队列运行器必须包含✅，不能包含❌
            if check["name"] == "队列运行器" and "❌" in check["status"]:
                all_ok = False
                print("  ❌ 关键检查失败: 队列运行器状态包含❌")
                break
            # 其他检查必须包含✅或⚠️
            if "✅" not in check["status"] and "⚠️" not in check["status"]:
                all_ok = False
                print(f"  ❌ 检查失败: {check['name']}状态不包含✅或⚠️: {check['status']}")
                break

        print(f"  📊 总体健康状态: {'✅ 通过' if all_ok else '❌ 失败'}")

        return all_ok, checks

    def simulate_batch1(self):
        """模拟批次1：测试队列迁移（10%流量）"""
        print("\n🚀 模拟批次1：测试队列迁移（10%流量）")
        print("⏱️ 测试时长: 2分钟（快速验证版）")

        batch_start = datetime.now()
        monitoring_data = []

        # 模拟2分钟监控
        for i in range(2):
            elapsed_minutes = i
            remaining_minutes = 4 - i

            print(f"\n⏱️ 批次执行中... 已进行 {elapsed_minutes} 分钟，剩余 {remaining_minutes} 分钟")

            # 检查当前状态
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()

            # 检查队列运行器
            queue_runner_alive = False
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    if proc.info["cmdline"] and any(
                        "athena_ai_plan_runner.py" in arg for arg in proc.info["cmdline"]
                    ):
                        queue_runner_alive = True
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # 检查队列状态
            queue_status = "unknown"
            if self.queue_dir.exists():
                queue_files = list(self.queue_dir.glob("*.json"))
                if queue_files:
                    try:
                        with open(queue_files[0], encoding="utf-8") as f:
                            data = json.load(f)
                            queue_status = data.get("queue_status", "unknown")
                    except Exception:
                        pass

            # 记录监控数据
            monitoring_data.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "elapsed_minutes": elapsed_minutes,
                    "queue_runner_alive": queue_runner_alive,
                    "queue_status": queue_status,
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                }
            )

            # 打印状态
            print(
                f"  📊 状态: 队列运行器={'✅' if queue_runner_alive else '❌'}, 队列状态={queue_status}"
            )
            print(f"  💻 资源: CPU={cpu_percent:.1f}%, 内存={memory.percent:.1f}%")

            # 如果有问题，记录警告
            if not queue_runner_alive:
                print("  ⚠️ 警告: 队列运行器未运行!")

            if cpu_percent > 90:
                print(f"  ⚠️ 警告: CPU使用率过高 ({cpu_percent:.1f}%)")

            if memory.percent > 90:
                print(f"  ⚠️ 警告: 内存使用率过高 ({memory.percent:.1f}%)")

            # 等待1分钟
            if i < 4:
                print("  ⏳ 等待1分钟...")
                time.sleep(60)

        batch_end = datetime.now()
        duration_seconds = (batch_end - batch_start).total_seconds()

        # 分析结果
        queue_runner_stable = all(data["queue_runner_alive"] for data in monitoring_data)
        cpu_stable = all(data["cpu_percent"] < 90 for data in monitoring_data)
        memory_stable = all(data["memory_percent"] < 90 for data in monitoring_data)

        success = queue_runner_stable and cpu_stable and memory_stable

        print(f"\n{'✅' if success else '❌'} 批次1模拟完成")
        print(f"⏱️ 持续时间: {duration_seconds // 60}分{duration_seconds % 60}秒")
        print(f"📊 结果: {'成功' if success else '失败'}")

        # 详细结果
        print("\n📈 详细结果:")
        print(f"  - 队列运行器稳定性: {'✅ 稳定' if queue_runner_stable else '❌ 不稳定'}")
        print(f"  - CPU稳定性: {'✅ 稳定' if cpu_stable else '❌ 不稳定'}")
        print(f"  - 内存稳定性: {'✅ 稳定' if memory_stable else '❌ 不稳定'}")

        return success, monitoring_data

    def generate_test_report(self, health_checks, batch_success, monitoring_data):
        """生成测试报告"""
        report_file = self.base_dir / "quick_traffic_switch_test_report.md"

        report = f"""# 快速流量切换测试报告

## 测试概览
- **测试时间**: {datetime.now().isoformat()}
- **测试类型**: 批次1模拟（10%流量，5分钟简化版）
- **总体结果**: {"✅ 通过" if batch_success else "❌ 失败"}

## 系统健康检查
"""

        for check in health_checks:
            report += f"- **{check['name']}**: {check['status']} {check['details']}\n"

        report += f"""
## 批次1模拟结果
- **批次名称**: 测试队列迁移（10%流量）
- **测试时长**: 5分钟
- **结果**: {"✅ 成功" if batch_success else "❌ 失败"}

## 监控数据摘要
"""

        if monitoring_data:
            first_data = monitoring_data[0]
            last_data = monitoring_data[-1]

            report += f"""
### 开始状态（{first_data.get("timestamp", "N/A")}）
- 队列运行器: {"✅ 运行中" if first_data.get("queue_runner_alive") else "❌ 未运行"}
- 队列状态: {first_data.get("queue_status", "unknown")}
- CPU使用率: {first_data.get("cpu_percent", 0):.1f}%
- 内存使用率: {first_data.get("memory_percent", 0):.1f}%

### 结束状态（{last_data.get("timestamp", "N/A")}）
- 队列运行器: {"✅ 运行中" if last_data.get("queue_runner_alive") else "❌ 未运行"}
- 队列状态: {last_data.get("queue_status", "unknown")}
- CPU使用率: {last_data.get("cpu_percent", 0):.1f}%
- 内存使用率: {last_data.get("memory_percent", 0):.1f}%

### 稳定性分析
- 队列运行器稳定性: {"✅ 稳定（全程运行）" if all(d.get("queue_runner_alive") for d in monitoring_data) else "❌ 不稳定"}
- CPU稳定性: {"✅ 稳定（<90%）" if all(d.get("cpu_percent", 0) < 90 for d in monitoring_data) else "❌ 不稳定"}
- 内存稳定性: {"✅ 稳定（<90%）" if all(d.get("memory_percent", 0) < 90 for d in monitoring_data) else "❌ 不稳定"}
"""

        # 建议
        report += """
## 建议

### 如果测试通过 ✅
1. **继续完整流量切换**: 可以开始完整的渐进式流量切换
2. **监控系统**: 建议运行完整的traffic_switch_monitor.py脚本
3. **文档更新**: 记录测试结果和配置

### 如果测试失败 ❌
1. **问题诊断**: 检查失败原因，修复问题
2. **系统优化**: 调整配置，优化资源使用
3. **重新测试**: 修复问题后重新运行测试

## 下一步
- 运行完整流量切换: `python3 scripts/traffic_switch_monitor.py`
- 监控24小时: 确保系统长期稳定
- 更新运维文档: 记录切换过程和结果

---
*报告生成时间: {datetime.now().isoformat()}*
"""

        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"\n📄 测试报告已生成: {report_file}")

        return report_file


def main():
    """主函数"""
    print("=" * 60)
    print("🚀 快速流量切换测试")
    print("=" * 60)

    tester = QuickTrafficSwitchTest()

    # 步骤1: 系统健康检查
    print("\n📋 步骤1: 系统健康检查")
    health_ok, health_checks = tester.check_system_health()

    if not health_ok:
        print("\n❌ 系统健康检查失败，无法继续测试")
        print("请修复问题后重新运行测试")
        return 1

    # 步骤2: 模拟批次1
    print("\n" + "=" * 60)
    print("📋 步骤2: 模拟批次1（10%流量，5分钟测试）")

    confirm = input("确认开始测试? (输入 'y' 确认): ")

    if confirm.lower() != "y":
        print("\n⏸️ 测试已取消")
        return 0

    batch_success, monitoring_data = tester.simulate_batch1()

    # 步骤3: 生成报告
    print("\n" + "=" * 60)
    print("📋 步骤3: 生成测试报告")

    report_file = tester.generate_test_report(health_checks, batch_success, monitoring_data)

    # 最终建议
    print("\n" + "=" * 60)
    if batch_success:
        print("🎉 快速测试通过！")
        print("建议: 可以开始完整的渐进式流量切换")
        print("命令: python3 scripts/traffic_switch_monitor.py")
    else:
        print("❌ 快速测试失败")
        print("建议: 检查问题原因，修复后重新测试")

    print(f"\n📄 详细报告: {report_file}")
    print("=" * 60)

    return 0 if batch_success else 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⏸️ 测试被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
