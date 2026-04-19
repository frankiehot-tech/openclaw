#!/usr/bin/env python3
"""
反馈状态流转测试
验证 feedback_intake 模块的状态流转功能。
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mini_agent.agent.core.feedback_intake import (
    FEEDBACK_SOURCE_INTERNAL,
    FEEDBACK_STATE_ACCEPTED,
    FEEDBACK_STATE_FIXED,
    FEEDBACK_STATE_NEW,
    FEEDBACK_STATE_TRIAGED,
    FEEDBACK_STATE_VERIFIED,
    FEEDBACK_TYPE_BUG,
    accept_feedback,
    create_feedback,
    get_feedback_stats,
    load_feedback,
    mark_fixed,
    triage_feedback,
    update_feedback_state,
    verify_feedback,
)


def test_feedback_lifecycle():
    """测试反馈完整生命周期"""
    print("=== 反馈状态流转测试 ===\n")

    # 清理可能存在的测试数据
    test_feedback = None

    try:
        # 1. 创建反馈
        print("1. 创建新反馈...")
        feedback = create_feedback(
            title="测试反馈状态流转",
            description="这是一个测试反馈，用于验证状态流转功能。",
            source=FEEDBACK_SOURCE_INTERNAL,
            feedback_type=FEEDBACK_TYPE_BUG,
            priority=2,
            metadata={"test": True},
        )

        if not feedback:
            print("❌ 创建反馈失败")
            return False

        print(f"   ✅ 创建成功: {feedback.feedback_id}")
        print(f"      状态: {feedback.state} (应为 {FEEDBACK_STATE_NEW})")
        print(f"      标题: {feedback.title}")

        # 验证初始状态
        if feedback.state != FEEDBACK_STATE_NEW:
            print(f"❌ 初始状态不正确: {feedback.state}")
            return False

        # 2. 分诊反馈
        print("\n2. 分诊反馈 (new → triaged)...")
        success = triage_feedback(feedback.feedback_id, priority=3, assigned_to="tester")

        if not success:
            print("❌ 分诊失败")
            return False

        feedback = load_feedback(feedback.feedback_id)
        print(f"   ✅ 分诊成功")
        print(f"      状态: {feedback.state} (应为 {FEEDBACK_STATE_TRIAGED})")
        print(f"      优先级: {feedback.priority} (应为 3)")
        print(f"      分配给: {feedback.assigned_to} (应为 tester)")

        if feedback.state != FEEDBACK_STATE_TRIAGED:
            print(f"❌ 分诊后状态不正确: {feedback.state}")
            return False
        if feedback.priority != 3:
            print(f"❌ 分诊后优先级不正确: {feedback.priority}")
            return False

        # 3. 接受反馈
        print("\n3. 接受反馈 (triaged → accepted)...")
        success = accept_feedback(feedback.feedback_id, related_task_id="task_test_001")

        if not success:
            print("❌ 接受失败")
            return False

        feedback = load_feedback(feedback.feedback_id)
        print(f"   ✅ 接受成功")
        print(f"      状态: {feedback.state} (应为 {FEEDBACK_STATE_ACCEPTED})")
        print(f"      关联任务: {feedback.related_task_id} (应为 task_test_001)")

        if feedback.state != FEEDBACK_STATE_ACCEPTED:
            print(f"❌ 接受后状态不正确: {feedback.state}")
            return False

        # 4. 标记为已修复
        print("\n4. 标记为已修复 (accepted → fixed)...")
        success = mark_fixed(
            feedback.feedback_id,
            artifact_paths=["/tmp/fix.patch", "/tmp/test_results.json"],
        )

        if not success:
            print("❌ 标记修复失败")
            return False

        feedback = load_feedback(feedback.feedback_id)
        print(f"   ✅ 标记修复成功")
        print(f"      状态: {feedback.state} (应为 {FEEDBACK_STATE_FIXED})")
        print(f"      产物数: {len(feedback.artifacts)} (应为 2)")

        if feedback.state != FEEDBACK_STATE_FIXED:
            print(f"❌ 标记修复后状态不正确: {feedback.state}")
            return False
        if len(feedback.artifacts) != 2:
            print(f"❌ 产物数量不正确: {len(feedback.artifacts)}")
            return False

        # 5. 验证反馈
        print("\n5. 验证反馈 (fixed → verified)...")
        success = verify_feedback(
            feedback.feedback_id, verification_notes="测试验证通过，所有功能正常。"
        )

        if not success:
            print("❌ 验证失败")
            return False

        feedback = load_feedback(feedback.feedback_id)
        print(f"   ✅ 验证成功")
        print(f"      状态: {feedback.state} (应为 {FEEDBACK_STATE_VERIFIED})")
        print(f"      验证备注: {feedback.metadata.get('verification_notes', 'N/A')}")

        if feedback.state != FEEDBACK_STATE_VERIFIED:
            print(f"❌ 验证后状态不正确: {feedback.state}")
            return False

        # 6. 测试状态统计
        print("\n6. 测试状态统计...")
        stats = get_feedback_stats()
        print(f"   统计结果:")
        for state, count in stats.items():
            print(f"     {state}: {count}")

        # 验证统计中包含我们的测试反馈
        if stats.get(FEEDBACK_STATE_VERIFIED, 0) < 1:
            print("❌ 验证状态统计不正确")
            return False

        # 7. 测试非法状态转换
        print("\n7. 测试非法状态转换...")

        # 尝试从 verified 回到 new（应失败）
        success = update_feedback_state(feedback.feedback_id, FEEDBACK_STATE_NEW)
        if success:
            print("❌ 非法状态转换应失败但成功了")
            return False
        print("   ✅ 非法状态转换被正确拒绝")

        # 验证状态仍为 verified
        feedback = load_feedback(feedback.feedback_id)
        if feedback.state != FEEDBACK_STATE_VERIFIED:
            print(f"❌ 状态被非法更改: {feedback.state}")
            return False

        print("\n=== 所有测试通过! ===")
        return True

    except Exception as e:
        print(f"\n❌ 测试过程中出现异常: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        # 清理测试数据
        if test_feedback:
            try:
                feedback_file = (
                    project_root
                    / ".openclaw"
                    / "feedback_state"
                    / f"{test_feedback.feedback_id}.json"
                )
                if feedback_file.exists():
                    feedback_file.unlink()
            except:
                pass


def test_multiple_feedbacks():
    """测试多个反馈的创建和列表"""
    print("\n=== 多反馈测试 ===\n")

    feedback_ids = []

    try:
        # 创建多个测试反馈
        for i in range(3):
            feedback = create_feedback(
                title=f"多反馈测试 {i + 1}",
                description=f"第 {i + 1} 个测试反馈",
                priority=i,
                metadata={"test_multiple": True, "index": i},
            )
            if feedback:
                feedback_ids.append(feedback.feedback_id)
                print(f"  创建反馈 {i + 1}: {feedback.feedback_id}")

        print(f"\n  共创建 {len(feedback_ids)} 个反馈")

        # 测试列表功能
        from mini_agent.agent.core.feedback_intake import list_feedback

        all_feedbacks = list_feedback(limit=10)

        test_feedbacks = [f for f in all_feedbacks if f.feedback_id in feedback_ids]
        print(f"  列表功能返回 {len(test_feedbacks)} 个测试反馈")

        if len(test_feedbacks) != len(feedback_ids):
            print(f"❌ 列表功能不完整: 期望 {len(feedback_ids)}，实际 {len(test_feedbacks)}")
            return False

        # 测试状态过滤
        new_feedbacks = list_feedback(state_filter=FEEDBACK_STATE_NEW, limit=10)
        print(f"  状态过滤 (NEW): {len(new_feedbacks)} 个")

        # 至少应有我们的测试反馈
        test_new = [f for f in new_feedbacks if f.feedback_id in feedback_ids]
        if len(test_new) != len(feedback_ids):
            print(f"❌ 状态过滤不正确: 期望 {len(feedback_ids)} 个NEW，实际 {len(test_new)} 个")
            return False

        print("\n✅ 多反馈测试通过")
        return True

    except Exception as e:
        print(f"\n❌ 多反馈测试失败: {e}")
        return False
    finally:
        # 清理测试数据
        for fid in feedback_ids:
            try:
                feedback_file = project_root / ".openclaw" / "feedback_state" / f"{fid}.json"
                if feedback_file.exists():
                    feedback_file.unlink()
            except:
                pass


def main():
    """主测试函数"""
    print("运行反馈状态流转测试...\n")

    # 运行测试
    lifecycle_passed = test_feedback_lifecycle()
    multiple_passed = test_multiple_feedbacks()

    # 汇总结果
    print("\n" + "=" * 50)
    print("测试结果汇总:")
    print(f"  反馈生命周期测试: {'✅ 通过' if lifecycle_passed else '❌ 失败'}")
    print(f"  多反馈功能测试: {'✅ 通过' if multiple_passed else '❌ 失败'}")

    all_passed = lifecycle_passed and multiple_passed
    print(f"\n总体结果: {'✅ 所有测试通过' if all_passed else '❌ 部分测试失败'}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
