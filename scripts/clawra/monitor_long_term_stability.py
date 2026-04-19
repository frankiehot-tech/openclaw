#!/usr/bin/env python3
"""
MAREF长期稳定性监控脚本
运行此脚本进行24小时稳定性监控
用法: python3 monitor_long_term_stability.py --hours 24
"""

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def main():
    parser = argparse.ArgumentParser(description="MAREF长期稳定性监控")
    parser.add_argument("--hours", type=int, default=24, help="监控小时数")
    parser.add_argument("--interval", type=int, default=300, help="检查间隔秒数")
    args = parser.parse_args()

    print(f"=== MAREF长期稳定性监控开始 ===")
    print(f"时间: {datetime.now()}")
    print(f"时长: {args.hours} 小时")
    print(f"检查间隔: {args.interval} 秒")

    try:
        from maref_memory_integration import init_memory_manager
        from maref_monitor import MAREFMonitor
        from run_maref_daily_report import create_integration_environment

        print("初始化MAREF组件...")
        state_manager, agents = create_integration_environment()
        memory_manager = init_memory_manager(performance_mode=True)
        monitor = MAREFMonitor(state_manager, agents)

        start_time = time.time()
        end_time = start_time + (args.hours * 3600)

        check_count = 0
        metrics_data = []

        print("开始监控循环...")
        while time.time() < end_time:
            check_count += 1
            current_time = datetime.now()

            try:
                # 收集指标
                metrics = monitor.collect_all_metrics()
                metrics["check_timestamp"] = current_time.isoformat()
                metrics["check_number"] = check_count

                metrics_data.append(metrics)

                # 状态检查
                current_state = state_manager.current_state
                hexagram_name = state_manager.get_hexagram_name()

                print(f"检查 #{check_count} - {current_time.strftime('%H:%M:%S')}")
                print(f"  当前状态: {current_state} ({hexagram_name})")
                print(f"  智能体: {len(agents)} 个活跃")

                # 每10次检查保存一次数据
                if check_count % 10 == 0:
                    with open(f"logs/long_term_monitor_checkpoint_{check_count}.json", "w") as f:
                        json.dump(metrics_data[-10:], f, indent=2)

            except Exception as e:
                print(f"  检查 #{check_count} 出错: {e}")
                # 记录错误但继续
                error_entry = {
                    "error": str(e),
                    "check_timestamp": current_time.isoformat(),
                    "check_number": check_count,
                }
                metrics_data.append(error_entry)

            # 等待下一个检查点
            time.sleep(args.interval)

        # 监控完成
        elapsed_hours = (time.time() - start_time) / 3600
        print(f"=== 长期稳定性监控完成 ===")
        print(f"总检查次数: {check_count}")
        print(f"实际运行时间: {elapsed_hours:.1f} 小时")

        # 保存完整数据
        output_file = (
            f"logs/long_term_monitor_complete_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(output_file, "w") as f:
            json.dump(
                {
                    "monitor_summary": {
                        "start_time": datetime.fromtimestamp(start_time).isoformat(),
                        "end_time": datetime.fromtimestamp(end_time).isoformat(),
                        "duration_hours": elapsed_hours,
                        "total_checks": check_count,
                    },
                    "metrics_data": metrics_data,
                },
                f,
                indent=2,
            )

        print(f"监控数据已保存到: {output_file}")

    except Exception as e:
        print(f"监控脚本初始化失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
