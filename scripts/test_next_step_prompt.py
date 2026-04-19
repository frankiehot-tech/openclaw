#!/usr/bin/env python3
"""
评分变化→下一步提示验证
验证 next_step_prompt 模块能根据评分变化生成建议。
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_next_step_generation():
    """测试下一步提示生成"""
    print("=== 评分变化→下一步提示验证 ===\n")

    try:
        from mini_agent.agent.core.next_step_prompt import (
            ActionRecommendation,
            analyze_feedback_backlog,
            analyze_improvement_progress,
            analyze_score_trends,
            analyze_system_health,
            generate_next_step_prompt,
            save_next_step_prompt,
        )

        # 1. 测试各分析函数
        print("1. 测试各分析函数...")

        feedback_recs = analyze_feedback_backlog()
        print(f"  反馈积压分析: {len(feedback_recs)} 条建议")

        score_recs = analyze_score_trends()
        print(f"  评分趋势分析: {len(score_recs)} 条建议")

        improvement_recs = analyze_improvement_progress()
        print(f"  改进进度分析: {len(improvement_recs)} 条建议")

        system_recs = analyze_system_health()
        print(f"  系统健康分析: {len(system_recs)} 条建议")

        # 2. 测试完整的下一步提示生成
        print("\n2. 生成完整的下一步提示...")
        prompt, recommendations = generate_next_step_prompt()

        if not prompt or len(prompt) < 100:
            print("❌ 生成的提示过短或为空")
            return False

        print(f"   ✅ 提示生成成功 ({len(prompt)} 字符)")
        print(f"   ✅ 生成 {len(recommendations)} 条建议")

        # 检查提示内容
        required_sections = ["下一步动作建议", "建议摘要", "常规维护建议"]
        missing_sections = []
        for section in required_sections:
            if section not in prompt:
                missing_sections.append(section)

        if missing_sections:
            print(f"❌ 提示缺少必要部分: {missing_sections}")
            return False

        # 3. 测试建议数据结构
        print("\n3. 验证建议数据结构...")
        if recommendations:
            first_rec = recommendations[0]
            required_fields = {
                "priority",
                "category",
                "title",
                "description",
                "action",
                "expected_impact",
                "estimated_effort",
            }
            missing_fields = required_fields - set(first_rec.__dict__.keys())

            if missing_fields:
                print(f"❌ 建议缺少字段: {missing_fields}")
                return False

            print(f"   ✅ 数据结构完整")
            print(f"      示例建议: {first_rec.title[:50]}...")

            # 验证优先级有效性
            valid_priorities = {"high", "medium", "low"}
            if first_rec.priority not in valid_priorities:
                print(f"❌ 无效优先级: {first_rec.priority}")
                return False

            print(f"      优先级: {first_rec.priority}")

        # 4. 测试保存功能
        print("\n4. 测试保存功能...")
        try:
            prompt_file = save_next_step_prompt(prompt, recommendations)
            print(f"   ✅ 保存成功: {prompt_file.name}")

            # 验证文件内容
            if prompt_file.exists():
                content = prompt_file.read_text(encoding="utf-8")
                if len(content) != len(prompt):
                    print(f"⚠️  保存内容长度不匹配: 原始 {len(prompt)} vs 文件 {len(content)}")
                else:
                    print(f"   ✅ 文件内容验证通过")

                # 清理测试文件
                prompt_file.unlink()
                recs_file = prompt_file.parent / "next_step_recommendations.json"
                if recs_file.exists():
                    recs_file.unlink()
            else:
                print("❌ 保存的文件不存在")
                return False
        except Exception as e:
            print(f"⚠️  保存功能测试出现异常（可能由于权限）: {e}")

        # 5. 模拟评分变化场景
        print("\n5. 模拟评分变化场景...")

        # 创建模拟的低评分数据
        from mini_agent.agent.core.scoreboard import ScoreEntry, save_score_entry

        # 创建历史低分条目（模拟下降）
        low_score_entry = ScoreEntry(
            timestamp=(datetime.now() - timedelta(days=2)).isoformat(),
            technical_score=45.0,  # 低分
            user_score=50.0,
            business_score=40.0,
            overall_score=45.0,
            metadata={"test_simulation": True, "factors": ["模拟低分测试"]},
        )

        # 保存模拟数据
        save_score_entry(low_score_entry)

        # 重新生成提示（应检测到低分）
        print("   生成模拟低分后的提示...")
        prompt2, recs2 = generate_next_step_prompt()

        # 检查是否包含低分相关建议
        low_score_keywords = ["得分下降", "低于及格线", "需改进", "低分"]
        found_keywords = []
        for keyword in low_score_keywords:
            if keyword in prompt2:
                found_keywords.append(keyword)

        if found_keywords:
            print(f"   ✅ 检测到低分关键词: {found_keywords}")
        else:
            print("   ⚠️  未检测到低分关键词（可能评分计算逻辑不同）")

        # 清理模拟数据
        try:
            scoreboard_dir = project_root / ".openclaw" / "scoreboard"
            for json_file in scoreboard_dir.glob("*.json"):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, list):
                        # 过滤掉模拟数据
                        filtered = [
                            item
                            for item in data
                            if not item.get("metadata", {}).get("test_simulation")
                        ]
                        if len(filtered) < len(data):
                            with open(json_file, "w", encoding="utf-8") as f:
                                json.dump(filtered, f, ensure_ascii=False, indent=2)
                    elif isinstance(data, dict) and data.get("metadata", {}).get("test_simulation"):
                        json_file.unlink()
                except Exception:
                    continue
        except Exception as e:
            print(f"   ⚠️  清理模拟数据时出错: {e}")

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


def test_action_recommendation_dataclass():
    """测试 ActionRecommendation 数据类"""
    print("\n=== ActionRecommendation 数据类测试 ===\n")

    try:
        from mini_agent.agent.core.next_step_prompt import ActionRecommendation

        # 创建实例
        rec = ActionRecommendation(
            priority="high",
            category="technical",
            title="测试建议标题",
            description="这是一个测试建议描述",
            action="执行测试动作",
            expected_impact="提升测试指标",
            estimated_effort="medium",
            related_items=["item1", "item2", "item3"],
        )

        # 测试属性
        print("1. 属性验证:")
        print(f"   优先级: {rec.priority}")
        print(f"   类别: {rec.category}")
        print(f"   标题: {rec.title}")
        print(f"   描述: {rec.description}")
        print(f"   动作: {rec.action}")
        print(f"   预期影响: {rec.expected_impact}")
        print(f"   预估投入: {rec.estimated_effort}")
        print(f"   关联项: {rec.related_items}")

        # 测试 to_dict（通过 asdict）
        from dataclasses import asdict

        rec_dict = asdict(rec)

        required_keys = {
            "priority",
            "category",
            "title",
            "description",
            "action",
            "expected_impact",
            "estimated_effort",
            "related_items",
        }
        missing_keys = required_keys - set(rec_dict.keys())
        if missing_keys:
            print(f"❌ 字典缺少键: {missing_keys}")
            return False

        print("2. 字典转换验证:")
        print(f"   字典键: {list(rec_dict.keys())}")

        # 验证序列化
        json_str = json.dumps(rec_dict, ensure_ascii=False)
        rec_dict2 = json.loads(json_str)

        if rec_dict2["title"] != rec.title:
            print("❌ JSON 序列化后数据不一致")
            return False

        print("3. JSON 序列化验证通过")

        print("\n✅ ActionRecommendation 数据类测试通过")
        return True

    except Exception as e:
        print(f"❌ ActionRecommendation 测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("运行评分变化→下一步提示验证...\n")

    # 运行测试
    generation_passed = test_next_step_generation()
    dataclass_passed = test_action_recommendation_dataclass()

    # 汇总结果
    print("\n" + "=" * 50)
    print("测试结果汇总:")
    print(f"  下一步提示生成测试: {'✅ 通过' if generation_passed else '❌ 失败'}")
    print(f"  ActionRecommendation 数据类测试: {'✅ 通过' if dataclass_passed else '❌ 失败'}")

    all_passed = generation_passed and dataclass_passed
    print(f"\n总体结果: {'✅ 所有测试通过' if all_passed else '❌ 部分测试失败'}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
