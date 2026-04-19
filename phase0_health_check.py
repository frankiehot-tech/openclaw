#!/usr/bin/env python3
"""
阶段0：部署准备与预检 - 系统健康检查脚本
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

import psutil


def check_queue_status(queue_file_path):
    """检查队列文件状态"""
    try:
        with open(queue_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        queue_id = data.get("queue_id", "unknown")
        current_item_id = data.get("current_item_id", "")
        updated_at = data.get("updated_at", "")

        # 处理items，可能是字典或列表
        raw_items = data.get("items", {})
        items_dict = {}

        if isinstance(raw_items, list):
            # items是列表，转换为字典，键为item['id']
            for item in raw_items:
                if isinstance(item, dict) and "id" in item:
                    items_dict[item["id"]] = item
        else:
            # items已经是字典
            items_dict = raw_items

        # 统计任务状态
        status_counts = {}
        for item_id, item_data in items_dict.items():
            status = item_data.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1

        # 检查队列是否卡住
        is_stuck = False
        if current_item_id and current_item_id in items_dict:
            item_status = items_dict[current_item_id].get("status", "")
            # 如果当前任务是running但很久没更新，可能卡住
            if item_status == "running":
                # 检查updated_at时间
                try:
                    update_time = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                    now = datetime.now(timezone.utc)
                    time_diff = (now - update_time).total_seconds()
                    if time_diff > 3600:  # 超过1小时
                        is_stuck = True
                except:
                    pass

        return {
            "queue_id": queue_id,
            "current_item_id": current_item_id,
            "updated_at": updated_at,
            "status_counts": status_counts,
            "total_items": len(items_dict),
            "is_stuck": is_stuck,
            "health_score": calculate_health_score(status_counts, is_stuck),
        }
    except Exception as e:
        return {"queue_id": os.path.basename(queue_file_path), "error": str(e), "health_score": 0}


def calculate_health_score(status_counts, is_stuck):
    """计算队列健康分数（0-100）"""
    if not status_counts:
        return 0

    total = sum(status_counts.values())
    if total == 0:
        return 0

    # 惩罚失败任务
    failed = status_counts.get("failed", 0)
    failed_penalty = min(50, (failed / total) * 100)

    # 奖励完成的任务
    completed = status_counts.get("completed", 0)
    completed_reward = min(50, (completed / total) * 50)

    # 基础分数
    base_score = 50

    # 调整
    score = base_score - failed_penalty + completed_reward

    # 如果卡住，严重扣分
    if is_stuck:
        score = max(0, score - 30)

    return min(100, max(0, score))


def check_process_health(process_name):
    """检查进程健康状态"""
    try:
        processes = []
        for proc in psutil.process_iter(
            ["pid", "name", "cmdline", "status", "cpu_percent", "memory_percent"]
        ):
            try:
                cmdline = " ".join(proc.info["cmdline"]) if proc.info["cmdline"] else ""
                if process_name.lower() in cmdline.lower():
                    processes.append(
                        {
                            "pid": proc.info["pid"],
                            "name": proc.info["name"],
                            "cmdline": cmdline[:200],  # 截断
                            "status": proc.info["status"],
                            "cpu_percent": proc.info["cpu_percent"],
                            "memory_percent": proc.info["memory_percent"],
                            "alive": True,
                        }
                    )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return processes
    except Exception as e:
        return {"error": str(e)}


def check_monitor_dashboard(port=5002):
    """检查监控仪表板状态"""
    try:
        import requests

        try:
            response = requests.get(f"http://localhost:{port}/api/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "running",
                    "status_code": response.status_code,
                    "queues_monitored": data.get("queues_monitored", 0),
                    "alerts_active": data.get("alerts_active", 0),
                }
            else:
                return {"status": "error", "status_code": response.status_code}
        except requests.exceptions.ConnectionError:
            return {"status": "not_running"}
    except ImportError:
        # requests未安装，使用curl
        try:
            result = subprocess.run(
                ["curl", "-s", f"http://localhost:{port}/api/status"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return {
                    "status": "running",
                    "queues_monitored": data.get("queues_monitored", 0),
                    "alerts_active": data.get("alerts_active", 0),
                }
            else:
                return {"status": "curl_error", "returncode": result.returncode}
        except:
            return {"status": "check_failed"}


def main():
    print("🧪 阶段0：系统健康检查")
    print("=" * 60)

    # 检查队列文件
    queue_dir = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue"
    if not os.path.exists(queue_dir):
        print(f"❌ 队列目录不存在: {queue_dir}")
        return

    # 主要队列文件
    main_queues = [
        "openhuman_aiplan_build_priority_20260328.json",
        "openhuman_aiplan_gene_management_20260405.json",
        "openhuman_aiplan_priority_execution_20260414.json",
    ]

    all_queues_healthy = True
    queue_reports = []

    for queue_file in main_queues:
        queue_path = os.path.join(queue_dir, queue_file)
        if os.path.exists(queue_path):
            print(f"\n📊 检查队列: {queue_file}")
            report = check_queue_status(queue_path)
            queue_reports.append(report)

            if "error" in report:
                print(f"   ❌ 检查失败: {report['error']}")
                all_queues_healthy = False
            else:
                print(f"   队列ID: {report['queue_id']}")
                print(f"   当前任务: {report['current_item_id'] or '无'}")
                print(f"   最后更新: {report['updated_at']}")
                print(f"   任务统计: {report['status_counts']}")
                print(f"   总任务数: {report['total_items']}")
                print(f"   是否卡住: {'是' if report['is_stuck'] else '否'}")
                print(f"   健康分数: {report['health_score']:.1f}/100")

                if report["health_score"] < 70:
                    all_queues_healthy = False
                    print(f"   ⚠️ 队列健康分数较低 (<70)")
        else:
            print(f"\n📊 队列文件不存在: {queue_file}")
            queue_reports.append({"queue_id": queue_file, "error": "文件不存在", "health_score": 0})
            all_queues_healthy = False

    # 检查进程
    print(f"\n🔄 检查系统进程:")

    process_checks = [
        ("athena_ai_plan_runner", "队列运行器"),
        ("athena_web_desktop", "Web服务器"),
        ("queue_monitor", "队列监控"),
        ("queue_monitor_dashboard", "监控仪表板"),
    ]

    all_processes_healthy = True
    for proc_name, display_name in process_checks:
        processes = check_process_health(proc_name)
        if isinstance(processes, dict) and "error" in processes:
            print(f"   ❌ {display_name}: 检查失败 - {processes['error']}")
            all_processes_healthy = False
        elif processes:
            print(f"   ✅ {display_name}: {len(processes)}个进程运行中")
            for proc in processes[:2]:  # 显示前2个
                print(
                    f"     - PID {proc['pid']}: {proc['status']}, CPU: {proc['cpu_percent']:.1f}%, 内存: {proc['memory_percent']:.1f}%"
                )
        else:
            print(f"   ⚠️ {display_name}: 未找到运行进程")
            all_processes_healthy = False

    # 检查监控仪表板
    print(f"\n📈 检查监控仪表板:")
    dashboard_status = check_monitor_dashboard(5002)
    print(f"   仪表板状态: {dashboard_status.get('status', 'unknown')}")
    if dashboard_status.get("status") == "running":
        print(f"   监控队列数: {dashboard_status.get('queues_monitored', 0)}")
        print(f"   活跃告警数: {dashboard_status.get('alerts_active', 0)}")

    # 总结
    print(f"\n" + "=" * 60)
    print("📋 健康检查总结")
    print("=" * 60)

    # 计算总体健康分数
    total_health_score = 0
    valid_scores = 0
    for report in queue_reports:
        if "health_score" in report and not isinstance(report["health_score"], str):
            total_health_score += report["health_score"]
            valid_scores += 1

    avg_health_score = total_health_score / valid_scores if valid_scores > 0 else 0

    print(f"   队列平均健康分数: {avg_health_score:.1f}/100")
    print(f"   所有队列健康: {'✅ 是' if all_queues_healthy else '❌ 否'}")
    print(f"   所有进程运行: {'✅ 是' if all_processes_healthy else '❌ 否'}")
    print(
        f"   监控仪表板: {'✅ 运行中' if dashboard_status.get('status') == 'running' else '❌ 未运行'}"
    )

    # 质量门禁判断
    quality_gate_passed = (
        all_queues_healthy
        and all_processes_healthy
        and dashboard_status.get("status") == "running"
        and avg_health_score >= 70
    )

    print(f"\n   质量门禁通过: {'✅ 通过' if quality_gate_passed else '❌ 未通过'}")

    # 建议
    print(f"\n💡 建议:")
    if not all_queues_healthy:
        print("   - 修复队列健康问题（失败任务、卡住任务）")
    if not all_processes_healthy:
        print("   - 启动缺失的系统进程")
    if dashboard_status.get("status") != "running":
        print("   - 启动队列监控仪表板")
    if avg_health_score < 70:
        print(f"   - 提高队列健康分数（当前: {avg_health_score:.1f}/100）")

    return quality_gate_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
