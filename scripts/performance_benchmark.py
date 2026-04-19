#!/usr/bin/env python3
"""全域压力测试性能基准监控"""

import json
import time
from datetime import datetime
from pathlib import Path

import psutil


def collect_performance_metrics():
    """收集性能指标"""
    metrics = {
        "timestamp": datetime.now().isoformat(),
        "cpu": {
            "percent": psutil.cpu_percent(interval=1),
            "count": psutil.cpu_count(),
            "load_avg": psutil.getloadavg() if hasattr(psutil, "getloadavg") else [0, 0, 0],
        },
        "memory": {
            "total": psutil.virtual_memory().total,
            "available": psutil.virtual_memory().available,
            "percent": psutil.virtual_memory().percent,
            "used": psutil.virtual_memory().used,
        },
        "disk": {"usage": psutil.disk_usage("/")._asdict()},
        "network": {
            "bytes_sent": psutil.net_io_counters().bytes_sent,
            "bytes_recv": psutil.net_io_counters().bytes_recv,
        },
        "processes": len(psutil.pids()),
    }
    return metrics


def main():
    """主函数"""
    output_dir = Path("workspace/full_domain_stress_test_20260408/performance")
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics_file = output_dir / "performance_metrics.jsonl"

    print("🚀 性能基准监控启动...")

    try:
        while True:
            metrics = collect_performance_metrics()

            # 写入指标文件
            with open(metrics_file, "a") as f:
                f.write(json.dumps(metrics) + "\n")

            # 控制台输出摘要
            print(
                f"[{metrics['timestamp']}] CPU: {metrics['cpu']['percent']}% | "
                f"Memory: {metrics['memory']['percent']}% | "
                f"Processes: {metrics['processes']}"
            )

            time.sleep(60)  # 每分钟收集一次

    except KeyboardInterrupt:
        print("\n🛑 性能监控停止")


if __name__ == "__main__":
    main()
