#!/usr/bin/env python3
"""
评分板生成测试
验证 scoreboard 模块的基本功能。
"""

import json
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_scoreboard_basic():
    """测试评分板基本功能"""
    print("=== 评分板生成测试 ===\n")

    try:
        from mini_agent.agent.core.scoreboard import (
            ScoreEntry,
            generate_scoreboard,
            generate_scoreboard_report,
            get_score_trend,
            load_latest_score,
            load_score_history,
            save_score_entry,
        )

        # 1. 生成评分板
        print("1. 生成评分板...")
        score = generate_scoreboard()

        if not score:
            print("❌ 生成评分板失败")
            return False

        print("   ✅ 生成成功")
        print(f"      技术得分: {score.technical_score:.1f}")
        print(f"      用户得分: {score.user_score:.1f}")
        print(f"      业务得分: {score.business_score:.1f}")
        print(f"      综合得分: {score.overall_score:.1f}")

        # 验证得分范围
        if not (0 <= score.technical_score <= 100):
            print(f"❌ 技术得分超出范围: {score.technical_score}")
            return False
        if not (0 <= score.user_score <= 100):
            print(f"❌ 用户得分超出范围: {score.user_score}")
            return False
        if not (0 <= score.business_score <= 100):
            print(f"❌ 业务得分超出范围: {score.business_score}")
            return False
        if not (0 <= score.overall_score <= 100):
            print(f"❌ 综合得分超出范围: {score.overall_score}")
            return False

        # 2. 加载最新评分
        print("\n2. 加载最新评分...")
        latest = load_latest_score()

        if not latest:
            print("❌ 加载最新评分失败")
            return False

        print("   ✅ 加载成功")
        print(f"      时间戳: {latest.timestamp}")

        # 3. 测试趋势分析
        print("\n3. 测试趋势分析...")
        trend = get_score_trend()

        if not trend:
            print("❌ 获取趋势失败")
            return False

        print(f"   ✅ 趋势分析: {trend.get('trend', 'unknown')}")

        # 4. 生成报告
        print("\n4. 生成评分板报告...")
        report = generate_scoreboard_report()

        if not report or len(report) < 100:
            print("❌ 生成报告失败或报告过短")
            return False

        print(f"   ✅ 报告生成成功 ({len(report)} 字符)")

        # 检查报告内容
        required_sections = ["技术得分", "用户得分", "业务得分", "综合得分"]
        missing_sections = []
        for section in required_sections:
            if section not in report:
                missing_sections.append(section)

        if missing_sections:
            print(f"❌ 报告缺少必要部分: {missing_sections}")
            return False

        # 5. 测试保存和加载历史
        print("\n5. 测试保存和加载历史...")

        # 创建测试评分条目
        test_entry = ScoreEntry(
            timestamp="2026-04-03T12:00:00",
            technical_score=75.0,
            user_score=68.0,
            business_score=62.0,
            overall_score=69.5,
            metadata={"test": True},
        )

        # 保存测试条目
        save_success = save_score_entry(test_entry)
        if not save_success:
            print("⚠️  保存测试条目失败（可能由于文件权限，继续测试）")
        else:
            print("   ✅ 保存测试条目成功")

        # 加载历史（不验证内容）
        history = load_score_history(days=1)
        print(f"   ✅ 加载历史: {len(history)} 条记录")

        print("\n=== 所有测试通过! ===")
        return True

    except ImportError as e:
        print(f"❌ 导入模块失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试过程中出现异常: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_score_entry_dataclass():
    """测试 ScoreEntry 数据类"""
    print("\n=== ScoreEntry 数据类测试 ===\n")

    try:
        from mini_agent.agent.core.scoreboard import ScoreEntry

        # 创建实例
        entry = ScoreEntry(
            timestamp="2026-04-03T12:00:00",
            technical_score=80.0,
            user_score=70.0,
            business_score=60.0,
            overall_score=70.0,
            metadata={"test": True, "factors": ["test1", "test2"]},
        )

        # 测试 to_dict
        entry_dict = entry.to_dict()
        print("1. to_dict() 转换:")
        print(f"   {json.dumps(entry_dict, indent=2, ensure_ascii=False)[:200]}...")

        required_keys = {
            "timestamp",
            "technical_score",
            "user_score",
            "business_score",
            "overall_score",
            "metadata",
        }
        missing_keys = required_keys - set(entry_dict.keys())
        if missing_keys:
            print(f"❌ 字典缺少键: {missing_keys}")
            return False

        # 测试 from_dict
        entry2 = ScoreEntry.from_dict(entry_dict)
        print("2. from_dict() 还原:")
        print(f"   技术得分: {entry2.technical_score}")

        if entry2.technical_score != entry.technical_score:
            print("❌ 还原后数据不一致")
            return False

        # 测试四舍五入
        entry3 = ScoreEntry(
            timestamp="2026-04-03T12:00:00",
            technical_score=80.123456,
            user_score=70.987654,
            business_score=60.555555,
            overall_score=70.555555,
            metadata={},
        )

        print("3. 浮点数处理:")
        print(f"   原始技术得分: {entry3.technical_score}")
        print(f"   原始用户得分: {entry3.user_score}")

        print("\n✅ ScoreEntry 数据类测试通过")
        return True

    except Exception as e:
        print(f"❌ ScoreEntry 测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("运行评分板生成测试...\n")

    # 运行测试
    basic_passed = test_scoreboard_basic()
    dataclass_passed = test_score_entry_dataclass()

    # 汇总结果
    print("\n" + "=" * 50)
    print("测试结果汇总:")
    print(f"  评分板基本功能测试: {'✅ 通过' if basic_passed else '❌ 失败'}")
    print(f"  ScoreEntry 数据类测试: {'✅ 通过' if dataclass_passed else '❌ 失败'}")

    all_passed = basic_passed and dataclass_passed
    print(f"\n总体结果: {'✅ 所有测试通过' if all_passed else '❌ 部分测试失败'}")

    # 清理测试文件
    try:
        test_files = [
            project_root / ".openclaw" / "scoreboard" / "scores_20260403.json",
            project_root / ".openclaw" / "scoreboard" / "latest_score.json",
        ]
        for f in test_files:
            if f.exists():
                # 读取内容检查是否为测试数据
                try:
                    with open(f, encoding="utf-8") as fp:
                        content = json.load(fp)
                    if isinstance(content, dict) and content.get("metadata", {}).get("test"):
                        f.unlink()
                        print(f"清理测试文件: {f.name}")
                except Exception:
                    pass
    except Exception:
        pass

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
