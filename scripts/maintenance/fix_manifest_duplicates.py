#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py repair <command> 或 governance_cli.py queue fix
"""
修复manifest重复条目脚本

基于深度审计发现：优先执行队列中有51个重复条目
此脚本使用DataQualityContract进行数据质量分析和修复
"""

import json
import os
import sys
from datetime import datetime

# 添加当前目录到Python路径，以便导入contracts
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from contracts.data_quality import DataQualityContract, deduplicate_manifest


def analyze_manifest_quality(manifest_path):
    """分析manifest数据质量"""
    print(f"🔍 分析manifest数据质量: {manifest_path}")

    contract = DataQualityContract(manifest_path)

    if not contract.load_manifest():
        print(f"❌ 无法加载manifest文件: {manifest_path}")
        return None

    # 生成质量报告
    quality_report = contract.generate_quality_report()

    # 打印摘要
    print("📊 数据质量分析结果:")
    print(f"   总条目数: {quality_report['summary']['total_entries']}")
    print(f"   平均质量评分: {quality_report['summary']['average_quality_score']:.1f}/100")
    print(f"   重复率: {quality_report['summary']['duplicate_rate']:.1f}%")
    print(f"   完整性得分: {quality_report['summary']['integrity_score']:.1f}%")
    print(f"   总体质量: {quality_report['summary']['overall_quality']}")

    # 检查重复问题
    dup_analysis = quality_report["duplicate_analysis"]
    if dup_analysis["duplicate_ids_count"] > 0:
        print("\n🔴 发现重复问题:")
        print(f"   重复ID数量: {dup_analysis['duplicate_ids_count']}")
        print(f"   总重复条目数: {dup_analysis['duplicate_summary']['total_duplicate_entries']}")
        print(f"   最多重复次数: {dup_analysis['duplicate_summary']['max_duplicate_count']}次")

        # 显示前10个重复ID
        print("\n   前10个重复ID:")
        dup_by_id = dup_analysis["duplicate_by_id"]
        for i, (dup_id, info) in enumerate(list(dup_by_id.items())[:10]):
            print(f"     {i + 1}. {dup_id[:70]}... ({info['count']}次重复)")

    return contract, quality_report


def fix_manifest_duplicates(contract, manifest_path, backup=True):
    """修复manifest重复条目"""
    print("\n🔧 开始修复manifest重复条目...")

    # 创建备份
    if backup:
        backup_path = manifest_path + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        import shutil

        shutil.copy2(manifest_path, backup_path)
        print(f"📁 已创建备份: {backup_path}")

    # 执行去重
    output_path = manifest_path.replace(".json", "_deduplicated.json")
    success = deduplicate_manifest(manifest_path, output_path, strategy="keep_first")

    if success:
        print(f"✅ 去重完成: {output_path}")

        # 验证去重结果
        print("\n🔍 验证去重结果...")
        verify_contract = DataQualityContract(output_path)
        if verify_contract.load_manifest():
            verify_report = verify_contract.generate_quality_report()
            new_dup_count = verify_report["duplicate_analysis"]["duplicate_ids_count"]

            if new_dup_count == 0:
                print("✅ 验证通过: 去重后没有重复条目")

                # 替换原始文件
                import shutil

                shutil.copy2(output_path, manifest_path)
                print(f"📝 已更新原始manifest: {manifest_path}")

                # 保留去重后的文件供参考
                print(f"📁 去重副本保留在: {output_path}")

                return True
            else:
                print(f"⚠️  警告: 去重后仍有{new_dup_count}个重复条目")
                print(f"📁 去重文件保留在: {output_path}（需要进一步处理）")
                return False
        else:
            print("❌ 无法验证去重结果")
            return False
    else:
        print("❌ 去重失败")
        return False


def main():
    """主函数"""
    print("=" * 70)
    print("🔧 Manifest数据质量修复工具")
    print(f"   时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # 从.athena-auto-queue.json获取manifest路径
    config_file = ".athena-auto-queue.json"
    if not os.path.exists(config_file):
        print(f"❌ 配置文件不存在: {config_file}")
        return 1

    with open(config_file, encoding="utf-8") as f:
        config = json.load(f)

    routes = config.get("routes", [])

    for route in routes:
        route_id = route.get("route_id")
        manifest_path = route.get("manifest_path")
        route_name = route.get("name", route_id)

        print(f"\n📋 检查路由: {route_name} ({route_id})")
        print(f"   Manifest路径: {manifest_path}")

        if not os.path.exists(manifest_path):
            print("   ⚠️  Manifest文件不存在，跳过")
            continue

        # 分析数据质量
        result = analyze_manifest_quality(manifest_path)
        if result is None:
            continue

        contract, quality_report = result

        # 检查是否需要修复重复
        dup_count = quality_report["duplicate_analysis"]["duplicate_ids_count"]
        if dup_count > 0:
            print(f"\n🔴 发现{dup_count}个重复ID，需要修复")

            # 询问用户是否继续修复
            response = input(f"   是否修复{route_name}的重复条目？ (y/N): ").strip().lower()
            if response == "y":
                fix_manifest_duplicates(contract, manifest_path)
            else:
                print("   ⏭️  跳过修复")
        else:
            print("   ✅ 没有发现重复条目，无需修复")

    print("\n" + "=" * 70)
    print("🎉 数据质量检查完成")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
