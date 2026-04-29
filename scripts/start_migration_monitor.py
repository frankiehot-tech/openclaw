#!/usr/bin/env python3
"""
启动迁移监控器脚本
在后台运行迁移监控器，并记录日志
"""

import os
import subprocess
import sys
import time


def main():
    # 切换到项目目录
    os.chdir("/Volumes/1TB-M2/openclaw")

    # 监控器脚本路径
    monitor_script = "/Volumes/1TB-M2/openclaw/mini-agent/agent/core/migration_monitor.py"

    print("🚀 启动DeepSeek迁移监控器...")
    print(f"脚本路径: {monitor_script}")
    print(f"工作目录: {os.getcwd()}")

    # 检查脚本是否存在
    if not os.path.exists(monitor_script):
        print(f"❌ 错误: 监控器脚本不存在: {monitor_script}")
        return 1

    # 启动监控器进程
    print("🔄 启动监控器进程...")

    # 使用子进程运行，捕获输出到日志文件
    log_file = "/Volumes/1TB-M2/openclaw/mini-agent/logs/migration_monitor.log"
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    with open(log_file, "a") as log:
        log.write(f"\n{'=' * 80}\n")
        log.write(f"迁移监控器启动时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        log.write(f"{'=' * 80}\n")

    # 启动后台进程
    try:
        process = subprocess.Popen(
            [sys.executable, monitor_script],
            stdout=open(log_file, "a"),
            stderr=subprocess.STDOUT,
            cwd="/Volumes/1TB-M2/openclaw",
        )

        print(f"✅ 监控器进程已启动 (PID: {process.pid})")
        print(f"📝 日志输出到: {log_file}")
        print("📊 数据库路径: /Volumes/1TB-M2/openclaw/mini-agent/data/cost_tracking.db")
        print("⏱️  检查间隔: 15分钟")

        # 保存PID文件以便后续管理
        pid_file = "/Volumes/1TB-M2/openclaw/mini-agent/data/migration_monitor.pid"
        with open(pid_file, "w") as f:
            f.write(str(process.pid))

        print(f"📋 PID文件: {pid_file}")

        # 等待几秒检查进程是否正常运行
        time.sleep(2)
        if process.poll() is None:
            print("✅ 监控器正在正常运行")
            print("\n📈 监控器将监控以下指标:")
            print("   • 成本节省百分比 (目标: >70%)")
            print("   • 质量一致性 (目标: >0.9)")
            print("   • 错误率差异 (目标: <0.02)")
            print("   • 响应时间差异 (目标: <20%)")
            print("\n🚨 告警阈值:")
            print("   • 严重告警: 成本节省<50%, 质量一致性<0.85, 错误率差异>0.05")
            print("   • 警告: 成本节省50-70%, 质量一致性0.85-0.9, 错误率差异0.02-0.05")
            print("\n📋 报告将保存到: /Volumes/1TB-M2/openclaw/mini-agent/reports/")
            return 0
        else:
            print("❌ 监控器进程已退出")
            # 读取日志的最后几行
            with open(log_file) as f:
                lines = f.readlines()[-10:]
            print("最近日志:")
            for line in lines:
                print(f"  {line.rstrip()}")
            return 1

    except Exception as e:
        print(f"❌ 启动监控器失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
