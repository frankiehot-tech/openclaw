#!/usr/bin/env python3
"""
状态一致性检查工具

基于StateSyncContract.validate_state_consistency()方法，检查Athena队列系统的状态一致性。

使用方法：
    python3 check_state_consistency.py [queue_id] [--all] [--repair] [--verbose]

参数：
    queue_id: 要检查的队列ID（如'openhuman_aiplan_build_priority_20260328'）
    --all: 检查所有队列
    --repair: 自动修复不一致问题
    --verbose: 显示详细信息
"""

import argparse
import json
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from contracts.athena_state_sync_adapter import get_athena_state_sync_adapter


def find_all_queue_ids() -> list[str]:
    """查找所有队列ID"""
    queue_dir = Path("/Volumes/1TB-M2/openclaw/.openclaw/plan_queue")
    if not queue_dir.exists():
        print(f"⚠️  队列目录不存在: {queue_dir}")
        return []

    queue_ids = []
    for file_path in queue_dir.glob("*.json"):
        # 跳过manifest文件（根据命名模式）
        filename = file_path.name
        if "manifest" in filename or "backup" in filename or "deduplicated" in filename:
            continue

        # 提取队列ID（文件名不带扩展名）
        queue_id = filename[:-5]  # 移除.json
        queue_ids.append(queue_id)

    return sorted(queue_ids)


def check_single_queue(queue_id: str, repair: bool = False, verbose: bool = False) -> bool:
    """检查单个队列的状态一致性"""
    print(f"\n🔍 检查队列: {queue_id}")
    print("-" * 60)

    try:
        # 获取状态同步适配器
        adapter = get_athena_state_sync_adapter(queue_id)

        # 验证状态一致性
        report = adapter.validate_state_consistency()

        if "error" in report:
            print(f"❌ 验证失败: {report['error']}")
            return False

        # 显示报告
        print(f"📊 一致性得分: {report.get('consistency_score', 0):.1f}%")
        print(f"📋 任务总数: {report.get('total_tasks', 0)}")

        components = report.get("components", {})
        print("📦 组件状态:")
        for comp, count in components.items():
            print(f"   - {comp}: {count} 个任务")

        inconsistencies = report.get("inconsistencies", [])
        print(f"⚠️  不一致数量: {len(inconsistencies)}")

        if inconsistencies and verbose:
            print("\n📝 不一致详情:")
            for inc in inconsistencies[:5]:  # 最多显示5个
                print(f"   - 任务: {inc['task_id']}")
                print(f"     状态: {inc.get('states', {})}")
                print(f"     严重性: {inc.get('severity', 'unknown')}")

        # 如果发现不一致且启用了修复
        if inconsistencies and repair:
            print(f"\n🔧 修复不一致问题...")
            repair_report = adapter.repair_inconsistencies()

            if "error" in repair_report:
                print(f"❌ 修复失败: {repair_report['error']}")
            else:
                print(
                    f"✅ 修复完成: 成功 {repair_report.get('total_repaired', 0)}, 失败 {len(repair_report.get('failed', []))}"
                )

                # 重新验证
                print(f"\n🔄 重新验证...")
                new_report = adapter.validate_state_consistency()
                new_score = new_report.get("consistency_score", 0)
                print(f"📊 新一致性得分: {new_score:.1f}%")

                if new_score >= 100.0:
                    print("✅ 状态完全一致")
                else:
                    print(f"⚠️  仍存在不一致: {len(new_report.get('inconsistencies', []))} 个")

        # 判断检查是否通过
        consistency_score = report.get("consistency_score", 0)
        return consistency_score >= 95.0  # 95%以上认为通过

    except Exception as e:
        print(f"❌ 检查队列 {queue_id} 时出错: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description="检查Athena队列系统状态一致性")
    parser.add_argument("queue_id", nargs="?", help="要检查的队列ID")
    parser.add_argument("--all", action="store_true", help="检查所有队列")
    parser.add_argument("--repair", action="store_true", help="自动修复不一致问题")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细信息")

    args = parser.parse_args()

    if not args.queue_id and not args.all:
        print("❌ 请指定队列ID或使用 --all 检查所有队列")
        parser.print_help()
        return 1

    print("🚀 Athena队列系统状态一致性检查")
    print("=" * 60)

    # 确定要检查的队列
    queue_ids = []
    if args.all:
        queue_ids = find_all_queue_ids()
        if not queue_ids:
            print("❌ 未找到任何队列")
            return 1
        print(f"📋 找到 {len(queue_ids)} 个队列: {', '.join(queue_ids)}")
    else:
        queue_ids = [args.queue_id]

    # 检查每个队列
    results = {}
    for queue_id in queue_ids:
        success = check_single_queue(queue_id, args.repair, args.verbose)
        results[queue_id] = success

    # 总结
    print("\n" + "=" * 60)
    print("📊 检查总结")
    print("-" * 60)

    total = len(results)
    passed = sum(1 for success in results.values() if success)
    failed = total - passed

    print(f"✅ 通过: {passed}/{total}")
    print(f"❌ 失败: {failed}/{total}")

    if failed > 0:
        failed_queues = [qid for qid, success in results.items() if not success]
        print(f"⚠️  失败的队列: {', '.join(failed_queues)}")

    # 建议
    if failed == 0:
        print("\n🎉 所有队列状态一致！")
    else:
        print("\n💡 建议:")
        if args.repair:
            print("   - 自动修复未完全解决问题，可能需要手动检查")
        else:
            print("   - 使用 --repair 参数尝试自动修复")
            print("   - 使用 --verbose 查看不一致详情")
        print("   - 检查队列运行器是否正常工作")
        print("   - 检查Web界面与队列文件的时间戳")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⏹️ 用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 检查失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
