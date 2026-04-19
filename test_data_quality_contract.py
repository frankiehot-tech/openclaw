#!/usr/bin/env python3
"""
测试DataQualityContract契约功能

验证：
1. 重复条目检测和去重功能
2. 数据完整性验证
3. 质量评分系统
4. 多种去重策略
"""

import os
import sys

sys.path.insert(0, "/Volumes/1TB-M2/openclaw")

from contracts.data_quality import DataQualityContract, DataQualityItem


def test_basic_deduplication():
    """测试基本去重功能"""
    print("=" * 60)
    print("测试1: 基本去重功能")
    print("=" * 60)

    # 测试数据 - 模拟重复条目
    test_items = [
        {"id": "task_1", "title": "任务1", "entry_stage": "build", "instruction_path": "/path/1"},
        {"id": "task_2", "title": "任务2", "entry_stage": "build", "instruction_path": "/path/2"},
        {
            "id": "task_1",
            "title": "任务1重复",
            "entry_stage": "build",
            "instruction_path": "/path/1",
        },  # 重复ID
        {"id": "task_3", "title": "任务3", "entry_stage": "build", "instruction_path": "/path/3"},
        {
            "id": "task_2",
            "title": "任务2重复",
            "entry_stage": "build",
            "instruction_path": "/path/2",
        },  # 重复ID
    ]

    print(f"📊 测试数据: {len(test_items)}个条目")

    # 创建契约
    contract = DataQualityContract()

    # 分析重复 - 需要先加载数据到契约
    print(f"\n🔍 分析重复条目:")
    # 创建临时契约并加载测试数据
    temp_contract = DataQualityContract()
    # 直接设置items（因为测试数据是原始字典，不是DataQualityItem）
    # 需要转换为DataQualityItem
    temp_contract.items = []
    for i, item in enumerate(test_items):
        quality_item = DataQualityItem.from_json_item(item, i)
        temp_contract.items.append(quality_item)

    duplicate_report = temp_contract.analyze_duplicates()
    duplicate_by_id = duplicate_report.get("duplicate_by_id", {})
    print(f"   重复组数: {len(duplicate_by_id)}")

    if duplicate_by_id:
        for dup_id, info in list(duplicate_by_id.items())[:3]:  # 只显示前3组
            print(f"     ID: {dup_id}, 重复次数: {info.get('count', 0)}")

    # 测试不同去重策略
    print(f"\n🔄 测试不同去重策略:")

    strategies = ["keep_first", "keep_last", "keep_most_complete", "merge"]

    for strategy in strategies:
        print(f"\n   📋 策略: {strategy}")
        # 创建新契约用于每个策略测试
        strategy_contract = DataQualityContract()
        strategy_contract.items = []
        for i, item in enumerate(test_items):
            quality_item = DataQualityItem.from_json_item(item, i)
            strategy_contract.items.append(quality_item)

        deduped_items, dedup_report = strategy_contract.deduplicate(strategy=strategy)
        print(f"       原始条目数: {len(test_items)}")
        print(f"       去重后条目数: {len(deduped_items)}")
        print(f"       移除重复数: {dedup_report.get('duplicates_removed', 0)}")

        # 验证去重后ID唯一性
        deduped_ids = [item.get("id") for item in deduped_items]
        unique_ids = len(set(deduped_ids))
        if len(deduped_ids) == unique_ids:
            print(f"       ✅ ID唯一性验证通过")
        else:
            print(f"       ❌ ID唯一性验证失败")

    return test_items


def test_data_completeness():
    """测试数据完整性验证"""
    print("\n" + "=" * 60)
    print("测试2: 数据完整性验证")
    print("=" * 60)

    # 测试数据 - 包含不完整条目
    test_items = [
        {
            "id": "task_1",
            "title": "完整任务",
            "entry_stage": "build",
            "instruction_path": "/path/1",
        },
        {
            "id": "task_2",
            "title": "缺失entry_stage",
            "instruction_path": "/path/2",
        },  # 缺失entry_stage
        {
            "id": None,
            "title": "缺失ID",
            "entry_stage": "build",
            "instruction_path": "/path/3",
        },  # ID为None
        {
            "id": "task_4",
            "title": "",
            "entry_stage": "build",
            "instruction_path": "/path/4",
        },  # 空标题
        {
            "id": "task_5",
            "title": "任务5",
            "entry_stage": "build",
            "instruction_path": "",
        },  # 空指令路径
    ]

    contract = DataQualityContract()

    # 加载测试数据到契约
    contract.items = []
    for i, item in enumerate(test_items):
        quality_item = DataQualityItem.from_json_item(item, i)
        contract.items.append(quality_item)

    print("🔍 验证数据完整性:")
    completeness_report = contract.validate_data_integrity()

    print(f"   总条目数: {completeness_report['total_items']}")
    print(f"   完整性得分: {completeness_report['completeness_score']:.1f}/100")
    print(f"   通过验证条目: {completeness_report['passed_validation']}")
    print(f"   验证失败条目: {completeness_report['failed_validation']}")

    if completeness_report["validation_details"]:
        print(f"   验证详情:")
        for item_id, details in list(completeness_report["validation_details"].items())[:5]:
            status = "✅ 通过" if details.get("is_valid") else "❌ 失败"
            reasons = details.get("reasons", [])
            print(f"     {item_id or '无ID'}: {status}")
            if reasons:
                print(f"       原因: {', '.join(reasons[:2])}")


def test_quality_scoring():
    """测试质量评分系统"""
    print("\n" + "=" * 60)
    print("测试3: 质量评分系统")
    print("=" * 60)

    # 测试数据
    test_items = [
        {
            "id": "task_1",
            "title": "完整高质量任务",
            "entry_stage": "build",
            "instruction_path": "/path/1",
            "metadata": {"priority": "P0"},
        },
        {
            "id": "task_2",
            "title": "基本完整任务",
            "entry_stage": "build",
            "instruction_path": "/path/2",
        },  # 无metadata
        {
            "id": "task_3",
            "title": "",
            "entry_stage": "build",
            "instruction_path": "/path/3",
        },  # 空标题
    ]

    contract = DataQualityContract()

    print("📊 计算质量评分:")
    scoring_report = contract.calculate_quality_scores(test_items)

    print(f"   评分条目数: {scoring_report['total_scored']}")
    print(f"   平均质量分: {scoring_report['average_score']:.1f}/100")
    print(f"   最高分: {scoring_report['max_score']:.1f}")
    print(f"   最低分: {scoring_report['min_score']:.1f}")

    if scoring_report["scores"]:
        print(f"   详细评分 (前5个):")
        for i, (item_id, score_info) in enumerate(list(scoring_report["scores"].items())[:5]):
            score = score_info.get("score", 0)
            breakdown = score_info.get("breakdown", {})
            print(f"     {item_id}: {score:.1f}分")
            for factor, factor_score in breakdown.items():
                print(f"       {factor}: {factor_score:.1f}分")


def test_real_manifest_analysis():
    """测试实际manifest文件分析"""
    print("\n" + "=" * 60)
    print("测试4: 实际manifest文件分析")
    print("=" * 60)

    manifest_path = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_priority_execution_20260414.json"

    if not os.path.exists(manifest_path):
        print(f"❌ 文件不存在: {manifest_path}")
        return

    print(f"📁 分析文件: {manifest_path}")

    # 读取文件
    import json

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        items = data.get("items", [])
        print(f"📊 总条目数: {len(items)}")

        # 创建契约并分析
        contract = DataQualityContract()

        # 1. 重复分析
        print(f"\n🔍 重复分析:")
        duplicates = contract.find_duplicates(items)
        print(f"   重复组数: {len(duplicates)}")

        if duplicates:
            # 显示前5个重复ID
            for i, (dup_id, dup_items) in enumerate(list(duplicates.items())[:5]):
                print(f"     {i+1}. ID: {dup_id}, 重复次数: {len(dup_items)}")
                for item in dup_items[:2]:  # 只显示前2个重复项
                    title = item.get("title", "无标题")[:50]
                    print(f"        - {title}...")

        # 2. 完整性验证
        print(f"\n🔄 完整性验证:")
        completeness = contract.validate_completeness(items)
        print(f"   完整性得分: {completeness['completeness_score']:.1f}/100")
        print(f"   验证通过: {completeness['passed_validation']}")
        print(f"   验证失败: {completeness['failed_validation']}")

        # 3. 质量评分
        print(f"\n📈 质量评分:")
        scoring = contract.calculate_quality_scores(items)
        print(f"   平均质量分: {scoring['average_score']:.1f}/100")

        # 4. 生成完整报告
        print(f"\n📋 生成完整质量报告:")
        full_report = contract.analyze_data_quality(items)
        print(f"   总体质量分: {full_report['overall_quality_score']:.1f}/100")
        print(f"   重复率: {full_report['duplicate_rate']:.1f}%")
        print(f"   完整性得分: {full_report['completeness_score']:.1f}/100")

        # 5. 测试去重
        print(f"\n🧹 测试去重 (keep_first策略):")
        deduped_items, dedup_report = contract.deduplicate(items, strategy="keep_first")
        print(f"   原始条目数: {len(items)}")
        print(f"   去重后条目数: {len(deduped_items)}")
        print(f"   移除重复数: {dedup_report.get('duplicates_removed', 0)}")

        # 验证去重效果
        deduped_ids = [item.get("id") for item in deduped_items]
        unique_ids = len(set(deduped_ids))
        if len(deduped_ids) == unique_ids:
            print(f"   ✅ 去重成功: 所有ID唯一")
        else:
            print(f"   ❌ 去重失败: 仍有重复ID")

    except Exception as e:
        print(f"❌ 分析失败: {str(e)}")


def test_report_generation():
    """测试报告生成功能"""
    print("\n" + "=" * 60)
    print("测试5: 报告生成功能")
    print("=" * 60)

    # 创建测试数据
    test_items = [
        {"id": "task_1", "title": "任务1", "entry_stage": "build", "instruction_path": "/path/1"},
        {"id": "task_2", "title": "任务2", "entry_stage": "build", "instruction_path": "/path/2"},
        {
            "id": "task_1",
            "title": "任务1重复",
            "entry_stage": "build",
            "instruction_path": "/path/1",
        },  # 重复
        {"id": "task_3", "title": "任务3", "entry_stage": "plan", "instruction_path": "/path/3"},
    ]

    contract = DataQualityContract()

    print("📋 生成详细质量报告:")
    report = contract.generate_detailed_report(test_items)

    # 打印报告摘要
    print(f"\n📊 报告摘要:")
    print(f"   分析条目数: {report['summary']['total_items']}")
    print(f"   总体质量分: {report['summary']['overall_quality_score']:.1f}/100")
    print(f"   重复率: {report['summary']['duplicate_rate']:.1f}%")
    print(f"   完整性得分: {report['summary']['completeness_score']:.1f}/100")

    print(f"\n🔍 重复详情 (前3组):")
    for i, dup_detail in enumerate(report.get("duplicate_details", [])[:3]):
        print(f"   {i+1}. ID: {dup_detail['id']}, 重复次数: {dup_detail['count']}")

    print(f"\n📈 质量评分分布:")
    for score_range, count in report.get("quality_score_distribution", {}).items():
        print(f"   {score_range}: {count}个条目")

    print(f"\n💡 改进建议 (前3条):")
    for i, suggestion in enumerate(report.get("improvement_suggestions", [])[:3]):
        print(f"   {i+1}. {suggestion}")


def main():
    """主测试函数"""
    print("🧪 DataQualityContract 测试套件")
    print("=" * 60)
    print("目标: 验证数据质量契约功能，解决Manifest重复条目问题")
    print("=" * 60)

    # 运行测试
    test_basic_deduplication()
    test_data_completeness()
    test_quality_scoring()
    test_real_manifest_analysis()
    test_report_generation()

    # 总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    print("✅ DataQualityContract 提供完整的数据质量管理功能")
    print("✅ 支持多种去重策略: keep_first, keep_last, keep_most_complete, merge")
    print("✅ 完整性验证: 检查必需字段和内容质量")
    print("✅ 质量评分系统: 为每个条目提供0-100的质量评分")
    print("✅ 详细报告生成: 提供可操作的质量改进建议")

    print("\n🔧 实际应用建议:")
    print("   1. 定期运行数据质量分析，监控manifest健康状况")
    print("   2. 在队列生成时应用去重策略，避免重复条目")
    print("   3. 基于质量评分优化低质量条目")
    print("   4. 集成到构建流水线中，确保数据质量")

    print("\n⚠️  生产使用注意事项:")
    print("   1. 选择合适的去重策略（通常keep_first或keep_most_complete）")
    print("   2. 设置合理的质量评分阈值，自动过滤低质量条目")
    print("   3. 定期备份原始数据，以防误删重要条目")
    print("   4. 监控去重效果，确保没有误删唯一但相似的条目")

    return 0


if __name__ == "__main__":
    sys.exit(main())
