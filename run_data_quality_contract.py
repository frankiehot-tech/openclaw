#!/usr/bin/env python3
"""
运行DataQualityContract清理Manifest重复数据
任务#19: 运行DataQualityContract清理Manifest重复数据
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from contracts.data_quality import DataQualityContract


def main():
    print("🚀 运行DataQualityContract清理Manifest重复数据")
    print("=" * 70)

    # 优先执行队列manifest文件
    manifest_path = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_priority_execution_20260414.json"
    backup_path = f"{manifest_path}.backup"
    dedup_path = f"{manifest_path}.deduplicated"

    print(f"📁 原始文件: {manifest_path}")
    print(f"💾 备份文件: {backup_path}")
    print(f"🔧 去重后文件: {dedup_path}")

    # 1. 备份原始文件
    try:
        import shutil

        shutil.copy2(manifest_path, backup_path)
        print(f"✅ 备份创建成功: {backup_path}")
    except Exception as e:
        print(f"⚠️  备份失败: {e}")
        print("   继续执行（跳过备份）...")

    # 2. 使用deduplicate_manifest函数进行去重
    print("\n🔍 开始分析manifest数据质量...")

    contract = DataQualityContract(manifest_path)

    if not contract.load_manifest():
        print(f"❌ 无法加载manifest文件: {manifest_path}")
        return 1

    # 生成质量报告
    print("📊 生成数据质量报告...")
    report = contract.generate_quality_report()

    print("📋 报告摘要:")
    summary = report["summary"]
    print(f"   总条目数: {summary['total_entries']}")
    print(f"   平均质量评分: {summary['average_quality_score']:.1f}/100")
    print(f"   重复率: {summary['duplicate_rate']:.1f}%")
    print(f"   完整性得分: {summary['integrity_score']:.1f}%")
    print(f"   总体质量: {summary['overall_quality']}")

    # 检查重复情况
    dup_analysis = report["duplicate_analysis"]
    dup_count = dup_analysis["duplicate_ids_count"]

    if dup_count == 0:
        print("\nℹ️  没有发现重复条目，无需去重")
        print(f"   原始文件已备份: {backup_path}")
        return 0

    print(f"\n🔧 发现{dup_count}个重复ID，开始去重...")
    print("   重复详情:")

    dup_by_id = dup_analysis["duplicate_by_id"]
    for i, (dup_id, info) in enumerate(list(dup_by_id.items())[:5]):  # 只显示前5个
        print(f"     {i + 1}. {dup_id[:60]}... ({info['count']}次重复)")

    if len(dup_by_id) > 5:
        print(f"     ... 还有{len(dup_by_id) - 5}个重复ID")

    # 3. 执行去重
    print("\n🧹 执行去重处理（策略: keep_first）...")
    success = contract.save_deduplicated_manifest(dedup_path, strategy="keep_first")

    if not success:
        print("❌ 去重失败")
        return 1

    print("✅ 去重完成")
    print(f"   原始文件: {manifest_path}")
    print(f"   去重后文件: {dedup_path}")

    # 4. 验证去重效果
    print("\n🔍 验证去重效果...")
    verify_contract = DataQualityContract(dedup_path)

    if verify_contract.load_manifest():
        verify_report = verify_contract.generate_quality_report()
        verify_summary = verify_report["summary"]
        verify_dup_count = verify_report["duplicate_analysis"]["duplicate_ids_count"]

        print("📊 验证结果:")
        print(f"   总条目数: {verify_summary['total_entries']}")
        print(f"   重复ID数量: {verify_dup_count}")
        print(f"   平均质量评分: {verify_summary['average_quality_score']:.1f}/100")

        if verify_dup_count == 0:
            print("✅ 验证通过: 去重后没有重复条目")

            # 计算清理的重复条目数量
            original_count = summary["total_entries"]
            dedup_count = verify_summary["total_entries"]
            cleaned_count = original_count - dedup_count

            print("📈 清理统计:")
            print(f"   原始条目: {original_count}")
            print(f"   去重后条目: {dedup_count}")
            print(
                f"   清理的重复条目: {cleaned_count} ({cleaned_count / original_count * 100:.1f}%)"
            )
        else:
            print(f"⚠️  警告: 去重后仍有{verify_dup_count}个重复条目")
            # 显示剩余的重复
            remaining_dups = verify_report["duplicate_analysis"]["duplicate_by_id"]
            for dup_id, info in list(remaining_dups.items())[:3]:
                print(f"     - {dup_id[:50]}... ({info['count']}次重复)")

    # 5. 可选：用去重后的文件替换原始文件
    print("\n💡 可选操作:")
    print(f"   1. 保留当前状态: 原始文件已备份，去重文件保存在 {dedup_path}")
    print(f"   2. 替换原始文件: 运行 'cp {dedup_path} {manifest_path}'")
    print(f"   3. 恢复备份: 运行 'cp {backup_path} {manifest_path}'")

    # 记录清理结果到日志
    print("\n📝 清理任务完成")
    print(f"   - 原始文件: {manifest_path}")
    print(f"   - 备份文件: {backup_path}")
    print(f"   - 去重文件: {dedup_path}")
    print(f"   - 重复ID数量: {dup_count}")

    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⏹️ 用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 运行DataQualityContract失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(3)
