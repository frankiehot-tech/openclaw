#!/usr/bin/env python3
"""
MAREF性能指标收集脚本
定期收集系统、MAREF和智能体性能指标并存储
"""

import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

try:
    from maref_monitor import MAREFMonitor

    print("✅ 成功导入MAREFMonitor")
except ImportError as e:
    print(f"❌ 导入MAREFMonitor失败: {e}")
    sys.exit(1)


def collect_and_store_metrics(monitor, output_dir="logs/metrics"):
    """收集并存储性能指标"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 收集指标
    print(f"开始收集性能指标...")
    start_time = time.perf_counter()

    try:
        # 收集所有指标
        metrics = monitor.collect_all_metrics()
        collection_time = (time.perf_counter() - start_time) * 1000

        # 添加元数据
        metrics["metadata"] = {
            "collection_time_ms": collection_time,
            "collection_timestamp": datetime.now().isoformat(),
            "monitor_version": "1.0",
        }

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"metrics_{timestamp}.json"
        filepath = output_path / filename

        # 保存到文件
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(metrics, f, ensure_ascii=False, indent=2)

        print(f"✅ 指标收集完成，耗时: {collection_time:.1f}ms")
        print(f"📊 指标已保存到: {filepath}")

        # 记录到聚合文件
        record_to_summary(metrics, output_path)

        # 清理旧文件（保留最近7天）
        cleanup_old_metrics(output_path, days_to_keep=7)

        return filepath

    except Exception as e:
        print(f"❌ 指标收集失败: {e}")
        import traceback

        traceback.print_exc()
        return None


def record_to_summary(metrics, output_dir):
    """记录到汇总文件"""
    summary_file = output_dir / "metrics_summary.jsonl"

    summary_entry = {
        "timestamp": metrics.get("timestamp", datetime.now().isoformat()),
        "collection_time": metrics["metadata"]["collection_time_ms"],
        "system": {
            "cpu_usage": metrics["system"].get("cpu_usage"),
            "memory_usage": metrics["system"].get("memory_usage"),
            "disk_usage": metrics["system"].get("disk_usage"),
        },
        "maref": {
            "control_entropy_h_c": metrics["maref"].get("control_entropy_h_c"),
            "gray_code_compliance_rate": metrics["maref"]
            .get("gray_code_compliance_rate", {})
            .get("rate", 1.0),
            "state_transition_time_ms": metrics["maref"].get("state_transition_time_ms"),
        },
        "agents": {
            "count": len(metrics["agents"]),
            "healthy_count": sum(
                1 for a in metrics["agents"].values() if a.get("health_score", 0) >= 0.8
            ),
        },
    }

    try:
        with open(summary_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(summary_entry, ensure_ascii=False) + "\n")
        print(f"📈 指标已记录到汇总文件: {summary_file}")
    except Exception as e:
        print(f"⚠️  记录到汇总文件失败: {e}")


def cleanup_old_metrics(output_dir, days_to_keep=7):
    """清理旧指标文件"""
    cutoff_time = datetime.now() - timedelta(days=days_to_keep)

    try:
        deleted_count = 0
        for file_path in output_dir.glob("metrics_*.json"):
            if file_path.is_file():
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time < cutoff_time:
                    file_path.unlink()
                    deleted_count += 1

        if deleted_count > 0:
            print(f"🧹 清理了 {deleted_count} 个超过 {days_to_keep} 天的旧指标文件")
    except Exception as e:
        print(f"⚠️  清理旧文件失败: {e}")


def get_health_status(metrics):
    """获取健康状态"""
    health_status = {
        "system": "healthy",
        "maref": "healthy",
        "agents": "healthy",
        "overall": "healthy",
    }

    # 系统健康检查
    if metrics["system"].get("memory_usage", 0) > 90:
        health_status["system"] = "critical"
    elif metrics["system"].get("memory_usage", 0) > 80:
        health_status["system"] = "warning"

    if metrics["system"].get("cpu_usage", 0) > 95:
        health_status["system"] = "critical"
    elif metrics["system"].get("cpu_usage", 0) > 85:
        health_status["system"] = "warning"

    # MAREF健康检查
    h_c = metrics["maref"].get("control_entropy_h_c", 0)
    if h_c > 5.5:
        health_status["maref"] = "critical"
    elif h_c > 4.5:
        health_status["maref"] = "warning"

    # 智能体健康检查
    healthy_agents = sum(1 for a in metrics["agents"].values() if a.get("health_score", 0) >= 0.8)
    total_agents = len(metrics["agents"])

    if total_agents > 0:
        health_rate = healthy_agents / total_agents
        if health_rate < 0.6:
            health_status["agents"] = "critical"
        elif health_rate < 0.8:
            health_status["agents"] = "warning"

    # 总体健康状态
    if "critical" in health_status.values():
        health_status["overall"] = "critical"
    elif "warning" in health_status.values():
        health_status["overall"] = "warning"

    return health_status


def print_health_report(metrics):
    """打印健康报告"""
    health_status = get_health_status(metrics)

    print(f"\n{'='*60}")
    print(f"MAREF系统健康报告")
    print(f"{'='*60}")
    print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"总体状态: {health_status['overall'].upper()}")
    print(f"\n子系统状态:")
    print(f"  - 系统资源: {health_status['system'].upper()}")
    print(f"  - MAREF核心: {health_status['maref'].upper()}")
    print(f"  - 智能体: {health_status['agents'].upper()}")

    print(f"\n关键指标:")
    print(f"  - CPU使用率: {metrics['system'].get('cpu_usage', 0):.1f}%")
    print(f"  - 内存使用率: {metrics['system'].get('memory_usage', 0):.1f}%")
    print(f"  - 控制熵H_c: {metrics['maref'].get('control_entropy_h_c', 0):.3f} bits")
    print(
        f"  - 格雷编码合规率: {metrics['maref'].get('gray_code_compliance_rate', {}).get('rate', 1.0)*100:.1f}%"
    )
    print(
        f"  - 健康智能体: {sum(1 for a in metrics['agents'].values() if a.get('health_score', 0) >= 0.8)}/{len(metrics['agents'])}"
    )

    print(f"{'='*60}")


def main():
    """主函数"""
    print("=== MAREF性能指标收集 ===")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 创建监控器（需要state_manager和agents）
    monitor = None
    try:
        # 尝试获取集成环境
        from run_maref_daily_report import create_integration_environment

        print("正在创建集成环境...")
        integration_result = create_integration_environment()

        if isinstance(integration_result, tuple) and len(integration_result) >= 2:
            state_manager, agents = integration_result[0], integration_result[1]
            monitor = MAREFMonitor(state_manager=state_manager, agents=agents)
            print(f"✅ 监控器创建成功，监控 {len(agents)} 个智能体")
        else:
            print("⚠️  集成环境返回格式不符合预期，创建基础监控器")
            monitor = MAREFMonitor()
    except Exception as e:
        print(f"⚠️  创建集成环境失败，使用基础监控器: {e}")
        monitor = MAREFMonitor()

    if monitor is None:
        print("❌ 无法创建监控器，退出")
        sys.exit(1)

    # 收集指标
    output_dir = "logs/metrics"
    result = collect_and_store_metrics(monitor, output_dir)

    if result:
        print_health_report(monitor.collect_all_metrics())
        print(f"\n✅ 性能指标收集完成")
        print(f"📁 数据目录: {output_dir}")
        print(f"📅 下次建议收集时间: {(datetime.now() + timedelta(minutes=5)).strftime('%H:%M')}")
    else:
        print("❌ 性能指标收集失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
