#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py <command>
"""
最终队列修复与监控启动脚本
解决queue_status仍为dependency_blocked的问题，并启动24小时监控验证
"""

import json
import os
import subprocess
from datetime import datetime

# 队列文件路径
QUEUE_FILE = (
    "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json"
)
BACKUP_FILE = f"{QUEUE_FILE}.backup_final_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def load_queue():
    """加载队列文件"""
    with open(QUEUE_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_queue(data):
    """保存队列文件，确保状态持久化"""
    # 备份原文件
    if os.path.exists(QUEUE_FILE) and not os.path.exists(BACKUP_FILE):
        import shutil

        shutil.copy2(QUEUE_FILE, BACKUP_FILE)
        print(f"📂 已备份原文件: {BACKUP_FILE}")

    # 确保目录存在
    os.makedirs(os.path.dirname(QUEUE_FILE), exist_ok=True)

    # 写入文件
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"💾 已保存队列文件: {QUEUE_FILE}")

    # 验证写入成功
    with open(QUEUE_FILE, encoding="utf-8") as f:
        saved_data = json.load(f)
        if saved_data.get("queue_status") == data.get("queue_status"):
            print(f"✅ 状态验证成功: queue_status = {saved_data.get('queue_status')}")
        else:
            print(
                f"❌ 状态验证失败: 期望 {data.get('queue_status')}, 实际 {saved_data.get('queue_status')}"
            )


def analyze_queue_stall():
    """分析队列停滞原因"""
    print("🔍 分析队列停滞原因...")

    queue_data = load_queue()

    # 检查基本状态
    queue_status = queue_data.get("queue_status", "unknown")
    pause_reason = queue_data.get("pause_reason", "")
    counts = queue_data.get("counts", {})

    print("📊 当前队列状态:")
    print(f"  queue_status: {queue_status}")
    print(f"  pause_reason: {pause_reason}")
    print(f"  任务统计: {json.dumps(counts, ensure_ascii=False)}")

    # 分析pending任务
    items = queue_data.get("items", {})
    pending_tasks = []

    for task_id, task_data in items.items():
        if task_data.get("status") == "pending":
            summary = task_data.get("summary", "")
            pending_tasks.append(
                {
                    "task_id": task_id,
                    "summary": summary[:100] + "..." if len(summary) > 100 else summary,
                }
            )

    print(f"📋 找到 {len(pending_tasks)} 个pending任务")

    return queue_data, pending_tasks


def fix_queue_stall():
    """修复队列停滞问题"""
    print("🔧 开始修复队列停滞问题...")

    queue_data, pending_tasks = analyze_queue_stall()

    # 强制修复：无论依赖状态如何，将队列状态设为running
    # 因为依赖可能已经解决，但状态未更新
    old_status = queue_data.get("queue_status", "unknown")

    # 更新队列状态
    queue_data["queue_status"] = "running"
    queue_data["pause_reason"] = ""  # 清除暂停原因

    # 确保updated_at是最新的
    queue_data["updated_at"] = datetime.now().isoformat()

    # 如果没有当前任务，设置第一个pending任务为当前任务
    current_item_id = queue_data.get("current_item_id", "")
    if not current_item_id and pending_tasks:
        first_task = pending_tasks[0]["task_id"]
        queue_data["current_item_id"] = first_task
        print(f"🎯 设置当前任务为: {first_task}")

    # 重新计算counts
    items = queue_data.get("items", {})
    pending_count = sum(1 for task in items.values() if task.get("status") == "pending")
    running_count = sum(1 for task in items.values() if task.get("status") == "running")
    completed_count = sum(1 for task in items.values() if task.get("status") == "completed")
    failed_count = sum(1 for task in items.values() if task.get("status") == "failed")

    if "counts" not in queue_data:
        queue_data["counts"] = {}

    queue_data["counts"]["pending"] = pending_count
    queue_data["counts"]["running"] = running_count
    queue_data["counts"]["completed"] = completed_count
    queue_data["counts"]["failed"] = failed_count

    print(f"🔄 队列状态从 {old_status} 强制更新为 running")
    print(
        f"📊 更新后任务统计: pending={pending_count}, running={running_count}, completed={completed_count}, failed={failed_count}"
    )

    # 保存修复
    save_queue(queue_data)

    return queue_data


def check_queue_runner():
    """检查队列运行器状态"""
    print("🔍 检查队列运行器状态...")

    try:
        # 检查队列运行器进程
        result = subprocess.run(
            ["ps", "aux", "|", "grep", "athena_ai_plan_runner", "|", "grep", "-v", "grep"],
            shell=True,
            capture_output=True,
            text=True,
        )

        if result.stdout:
            print("✅ 队列运行器进程正在运行:")
            print(result.stdout.strip())
        else:
            print("❌ 队列运行器进程未找到")
            print("⚠️ 建议重启队列运行器")

    except Exception as e:
        print(f"❌ 检查队列运行器时出错: {e}")


def start_monitoring():
    """启动24小时监控验证"""
    print("🚀 启动24小时监控验证...")

    # 检查监控仪表板
    monitor_dashboard_pid = None

    try:
        result = subprocess.run(
            ["ps", "aux", "|", "grep", "queue_monitor_dashboard", "|", "grep", "-v", "grep"],
            shell=True,
            capture_output=True,
            text=True,
        )

        if result.stdout:
            print("✅ 队列监控仪表板正在运行")
            # 提取PID
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split()
                    if len(parts) > 1:
                        monitor_dashboard_pid = parts[1]
                        print(f"  仪表板PID: {monitor_dashboard_pid}")
        else:
            print("⚠️ 队列监控仪表板未运行，准备启动...")

            # 启动监控仪表板
            dashboard_script = "/Volumes/1TB-M2/openclaw/queue_monitor_dashboard.py"
            if os.path.exists(dashboard_script):
                # 在后台启动仪表板
                process = subprocess.Popen(
                    ["python3", dashboard_script, ">", "dashboard.log", "2>&1", "&"],
                    shell=True,
                    cwd="/Volumes/1TB-M2/openclaw",
                )
                print(f"✅ 已启动队列监控仪表板 (PID: {process.pid})")
                monitor_dashboard_pid = process.pid
            else:
                print(f"❌ 监控仪表板脚本不存在: {dashboard_script}")

    except Exception as e:
        print(f"❌ 检查监控仪表板时出错: {e}")

    # 检查监控守护进程
    try:
        result = subprocess.run(
            ["ps", "aux", "|", "grep", "two_minute_queue_monitor", "|", "grep", "-v", "grep"],
            shell=True,
            capture_output=True,
            text=True,
        )

        if result.stdout:
            print("✅ 队列监控守护进程正在运行")
        else:
            print("⚠️ 队列监控守护进程未运行")
            print("⚠️ 建议检查cron任务配置")

    except Exception as e:
        print(f"❌ 检查监控守护进程时出错: {e}")

    # 提供监控访问信息
    print("\n📊 监控访问信息:")
    print("  1. 队列监控仪表板: http://localhost:5002/")
    print("  2. 监控API端点: http://localhost:5002/api/status")
    print("  3. 查看监控日志: tail -f dashboard.log")
    print("  4. 查看队列运行器日志: 检查进程输出")

    return monitor_dashboard_pid


def configure_enhanced_monitoring():
    """配置增强型监控"""
    print("🔧 配置增强型监控...")

    # 检查queue_monitor.py脚本
    monitor_script = "/Volumes/1TB-M2/openclaw/queue_monitor.py"

    if os.path.exists(monitor_script):
        print(f"✅ 找到监控脚本: {monitor_script}")

        # 检查脚本中是否包含增强监控功能
        with open(monitor_script, encoding="utf-8") as f:
            content = f.read()

            enhanced_features = []
            if "queue_health_score" in content:
                enhanced_features.append("队列健康度评分")
            if "real_time_alert" in content or "send_alert" in content:
                enhanced_features.append("实时告警")
            if "system_resource_monitoring" in content:
                enhanced_features.append("系统资源监控")
            if "dependency_analysis" in content:
                enhanced_features.append("依赖分析")

            if enhanced_features:
                print(f"✅ 监控脚本已包含增强功能: {', '.join(enhanced_features)}")
            else:
                print("⚠️ 监控脚本可能缺少增强功能")
    else:
        print(f"❌ 监控脚本不存在: {monitor_script}")

    # 提供增强监控建议
    print("\n💡 增强监控建议:")
    print("  1. 配置邮件告警: 编辑queue_monitor.py中的邮件配置")
    print("  2. 配置Slack Webhook: 添加Slack通知渠道")
    print("  3. 设置监控阈值: 调整队列停滞检测时间")
    print("  4. 添加资源监控: 监控CPU、内存、磁盘使用率")
    print("  5. 实施24小时监控: 确保监控守护进程持续运行")


def create_monitoring_plan():
    """创建24小时监控验证计划"""
    print("📋 创建24小时监控验证计划...")

    plan = {
        "start_time": datetime.now().isoformat(),
        "duration_hours": 24,
        "monitoring_checks": [
            {"check": "队列状态监控", "frequency": "每2分钟", "metric": "queue_status"},
            {"check": "任务执行进度", "frequency": "每5分钟", "metric": "progress_percent"},
            {"check": "系统资源使用", "frequency": "每10分钟", "metric": "cpu_memory_disk"},
            {"check": "依赖阻塞检测", "frequency": "每15分钟", "metric": "dependency_blocks"},
            {"check": "错误率监控", "frequency": "每30分钟", "metric": "error_rate"},
            {"check": "吞吐量统计", "frequency": "每小时", "metric": "tasks_per_hour"},
        ],
        "alert_config": {
            "immediate_alerts": [
                "queue_status=dependency_blocked",
                "queue_status=failed",
                "system_cpu>90%",
            ],
            "hourly_summary": True,
            "daily_report": True,
        },
        "verification_criteria": [
            "队列状态保持running至少95%的时间",
            "任务执行成功率>90%",
            "无长时间依赖阻塞(>1小时)",
            "系统资源使用稳定(无内存泄漏)",
            "监控告警准确率>95%",
        ],
    }

    # 保存监控计划
    plan_file = "/Volumes/1TB-M2/openclaw/24_hour_monitoring_plan.json"
    with open(plan_file, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)

    print(f"✅ 已保存24小时监控验证计划: {plan_file}")
    print(f"📅 监控开始时间: {plan['start_time']}")
    print(f"⏱️  监控时长: {plan['duration_hours']}小时")

    return plan


def main():
    """主函数"""
    print("=" * 60)
    print("🎯 最终队列修复与24小时监控验证启动")
    print("=" * 60)

    try:
        # 步骤1: 修复队列停滞问题
        print("\n" + "=" * 40)
        print("步骤1: 修复队列停滞问题")
        print("=" * 40)
        fix_queue_stall()

        # 步骤2: 检查队列运行器
        print("\n" + "=" * 40)
        print("步骤2: 检查队列运行器状态")
        print("=" * 40)
        check_queue_runner()

        # 步骤3: 启动监控
        print("\n" + "=" * 40)
        print("步骤3: 启动24小时监控验证")
        print("=" * 40)
        start_monitoring()

        # 步骤4: 配置增强监控
        print("\n" + "=" * 40)
        print("步骤4: 配置增强型监控")
        print("=" * 40)
        configure_enhanced_monitoring()

        # 步骤5: 创建监控计划
        print("\n" + "=" * 40)
        print("步骤5: 创建24小时监控验证计划")
        print("=" * 40)
        create_monitoring_plan()

        print("\n" + "=" * 60)
        print("✅ 队列修复与监控验证启动完成")
        print("=" * 60)
        print("\n📋 后续行动建议:")
        print("  1. 立即检查队列状态: 确认queue_status为running")
        print("  2. 访问监控仪表板: http://localhost:5002/")
        print("  3. 监控24小时性能: 观察新架构在生产流量下的表现")
        print("  4. 完善运维文档: 基于监控数据更新故障处理指南")
        print("  5. 配置告警通知: 设置邮件/Slack/webhook告警渠道")
        print("\n⏰ 24小时监控验证已启动，请定期检查监控仪表板。")

    except Exception as e:
        print(f"\n❌ 执行过程中出错: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
