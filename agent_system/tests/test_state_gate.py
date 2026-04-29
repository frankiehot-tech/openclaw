"""
测试状态置信度门控 (State Gate) (Phase 11.5)

测试目标：
1. 低置信时 planner 走保守策略
2. 高置信时使用正常规划
3. state_gate_used 和 state_gate_reason 正确记录
"""

import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from state.simple_state_planner import (
    STATE_CONFIDENCE_THRESHOLD,
    PlanResult,
    plan_next_step,
)


def test_low_confidence_triggers_gate():
    """测试低置信度触发 state gate"""
    # 模拟低置信度情况
    task = "打开设置"
    current_state = "unknown"
    state_confidence = 0.3  # 低于阈值

    result = plan_next_step(task, current_state, state_confidence)

    print(f"低置信度测试:")
    print(f"  任务: {task}")
    print(f"  当前状态: {current_state}")
    print(f"  置信度: {state_confidence}")
    print(f"  阈值: {STATE_CONFIDENCE_THRESHOLD}")
    print(f"  规划类型: {result.plan_type}")
    print(f"  下一步动作: {result.next_action}")
    print(f"  原因: {result.reason}")
    print(f"  State Gate 触发: {result.state_gate_used}")
    print(f"  Gate 原因: {result.state_gate_reason}")

    # 验证
    assert result.state_gate_used, "低置信度应该触发 state gate"
    assert result.plan_type == "conservative_fallback", f"应使用保守策略，实际 {result.plan_type}"
    assert result.next_action == "home", f"应先回到主屏幕，实际 {result.next_action}"
    print("✓ 低置信度触发 state gate 测试通过\n")


def test_high_confidence_normal_planning():
    """测试高置信度使用正常规划"""
    # 模拟高置信度情况
    task = "打开设置"
    current_state = "home_screen"
    state_confidence = 0.8  # 高于阈值

    result = plan_next_step(task, current_state, state_confidence)

    print(f"高置信度测试:")
    print(f"  任务: {task}")
    print(f"  当前状态: {current_state}")
    print(f"  置信度: {state_confidence}")
    print(f"  规划类型: {result.plan_type}")
    print(f"  下一步动作: {result.next_action}")
    print(f"  原因: {result.reason}")
    print(f"  State Gate 触发: {result.state_gate_used}")

    # 验证 - 高置信度且状态匹配，不需要 state gate
    assert result.plan_type == "direct_execute", f"应直接执行，实际 {result.plan_type}"
    print("✓ 高置信度正常规划测试通过\n")


def test_state_gate_for_browser_task():
    """测试浏览器任务的 state gate"""
    task = "点击搜索"
    current_state = "unknown"
    state_confidence = 0.2  # 低于阈值

    result = plan_next_step(task, current_state, state_confidence)

    print(f"浏览器任务 state gate 测试:")
    print(f"  任务: {task}")
    print(f"  当前状态: {current_state}")
    print(f"  置信度: {state_confidence}")
    print(f"  规划类型: {result.plan_type}")
    print(f"  下一步动作: {result.next_action}")
    print(f"  State Gate 触发: {result.state_gate_used}")

    # 验证
    assert result.state_gate_used, "低置信度应该触发 state gate"
    assert result.plan_type == "conservative_fallback", f"应使用保守策略，实际 {result.plan_type}"
    print("✓ 浏览器任务 state gate 测试通过\n")


def test_threshold_boundary():
    """测试阈值边界"""
    task = "打开设置"
    current_state = "unknown"

    # 测试刚好在阈值上
    confidence_on_threshold = STATE_CONFIDENCE_THRESHOLD
    result_on = plan_next_step(task, current_state, confidence_on_threshold)

    # 测试刚好在阈值下
    confidence_below_threshold = STATE_CONFIDENCE_THRESHOLD - 0.01
    result_below = plan_next_step(task, current_state, confidence_below_threshold)

    print(f"阈值边界测试:")
    print(f"  阈值: {STATE_CONFIDENCE_THRESHOLD}")
    print(
        f"  置信度={confidence_on_threshold}: gate={result_on.state_gate_used}, plan={result_on.plan_type}"
    )
    print(
        f"  置信度={confidence_below_threshold}: gate={result_below.state_gate_used}, plan={result_below.plan_type}"
    )

    # 验证
    assert result_below.state_gate_used, "低于阈值应该触发 gate"
    print("✓ 阈值边界测试通过\n")


def test_no_precondition_task():
    """测试无前置状态要求的任务"""
    task = "向上滑动"
    current_state = "unknown"
    state_confidence = 0.3  # 低置信度

    result = plan_next_step(task, current_state, state_confidence)

    print(f"无前置条件任务测试:")
    print(f"  任务: {task}")
    print(f"  当前状态: {current_state}")
    print(f"  置信度: {state_confidence}")
    print(f"  规划类型: {result.plan_type}")
    print(f"  下一步动作: {result.next_action}")
    print(f"  State Gate 触发: {result.state_gate_used}")

    # 验证 - 无前置条件任务即使低置信度也直接执行
    assert result.plan_type == "direct_execute", f"无前置条件应直接执行，实际 {result.plan_type}"
    print("✓ 无前置条件任务测试通过\n")


if __name__ == "__main__":
    print("=" * 50)
    print("State Gate 测试")
    print("=" * 50 + "\n")

    print(f"当前置信度阈值: {STATE_CONFIDENCE_THRESHOLD}\n")

    test_low_confidence_triggers_gate()
    test_high_confidence_normal_planning()
    test_state_gate_for_browser_task()
    test_threshold_boundary()
    test_no_precondition_task()

    print("=" * 50)
    print("所有 State Gate 测试完成!")
    print("=" * 50)
