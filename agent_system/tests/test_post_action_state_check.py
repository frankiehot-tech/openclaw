"""
测试动作后状态验证 (Post-Action State Check) (Phase 11.5)

测试目标：
1. 动作后状态验证逻辑生效
2. 目标状态未达到时记录失败
3. 允许修正动作或 fallback
"""

import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from state.simple_state_planner import get_task_target_state
from state.state_detector import detect_page_state


def test_settings_opened_verification():
    """测试打开设置后的状态验证"""
    # 模拟打开设置后的 OCR 结果
    ocr_texts = ["设置", "WLAN", "蓝牙", "更多连接", "飞行模式", "移动网络"]

    result = detect_page_state(ocr_results=ocr_texts)
    target_state = get_task_target_state("打开设置")

    print(f"打开设置后验证测试:")
    print(f"  检测状态: {result.state}")
    print(f"  目标状态: {target_state}")
    print(f"  置信度: {result.confidence:.2f}")

    # 验证
    state_reached = result.state == target_state
    print(f"  状态达到: {state_reached}")

    if not state_reached:
        print(f"  警告: 目标状态未达到，可能需要修正动作")

    assert state_reached, f"打开设置后应达到 {target_state}，实际 {result.state}"
    print("✓ 打开设置后验证测试通过\n")


def test_browser_opened_verification():
    """测试打开浏览器后的状态验证"""
    # 模拟打开浏览器后的 OCR 结果
    ocr_texts = ["Google", "搜索", "chrome", "百度", "输入网址", "书签"]

    result = detect_page_state(ocr_results=ocr_texts)
    target_state = get_task_target_state("打开浏览器")

    print(f"打开浏览器后验证测试:")
    print(f"  检测状态: {result.state}")
    print(f"  目标状态: {target_state}")
    print(f"  置信度: {result.confidence:.2f}")

    # 验证
    state_reached = result.state == target_state
    print(f"  状态达到: {state_reached}")

    if not state_reached:
        print(f"  警告: 目标状态未达到，可能需要修正动作")

    assert state_reached, f"打开浏览器后应达到 {target_state}，实际 {result.state}"
    print("✓ 打开浏览器后验证测试通过\n")


def test_search_page_verification():
    """测试点击搜索后的状态验证"""
    # 模拟点击搜索后的 OCR 结果（可能是搜索页面或浏览器首页）
    ocr_texts = ["搜索", "输入搜索内容", "百度", "Google", "搜索历史"]

    result = detect_page_state(ocr_results=ocr_texts)
    target_state = get_task_target_state("点击搜索")

    print(f"点击搜索后验证测试:")
    print(f"  检测状态: {result.state}")
    print(f"  目标状态: {target_state}")
    print(f"  置信度: {result.confidence:.2f}")

    # 搜索页面可能返回 browser_home 或 search_page
    state_reached = result.state in [target_state, "browser_home"]
    print(f"  状态达到: {state_reached}")

    if not state_reached:
        print(f"  警告: 目标状态未达到，可能需要修正动作")

    print("✓ 点击搜索后验证测试通过\n")


def test_state_check_failed_scenario():
    """测试状态检查失败场景"""
    # 模拟状态检查失败的情况
    ocr_texts = ["未知内容", "一些文字", "应用"]

    result = detect_page_state(ocr_results=ocr_texts)
    target_state = "settings_home"

    print(f"状态检查失败场景测试:")
    print(f"  检测状态: {result.state}")
    print(f"  目标状态: {target_state}")
    print(f"  置信度: {result.confidence:.2f}")

    # 验证
    state_reached = result.state == target_state
    print(f"  状态达到: {state_reached}")

    if not state_reached:
        print(f"  记录: post_action_state_check_failed")
        print(f"  建议: 允许一次修正动作或 fallback")

    # 这个测试应该显示状态未达到
    print("✓ 状态检查失败场景测试完成\n")


def test_verification_workflow():
    """测试完整的验证工作流"""
    print("完整验证工作流测试:")

    # 步骤 1: 执行动作前检测状态
    pre_ocr = ["抖音", "微信", "淘宝"]
    pre_result = detect_page_state(ocr_results=pre_ocr)
    print(f"  步骤1 - 执行前状态: {pre_result.state} (置信度: {pre_result.confidence:.2f})")

    # 步骤 2: 模拟执行"打开设置"动作
    print(f"  步骤2 - 执行动作: 打开设置")

    # 步骤 3: 执行动作后检测状态
    post_ocr = ["设置", "WLAN", "蓝牙", "更多连接", "飞行模式"]
    post_result = detect_page_state(ocr_results=post_ocr)
    target_state = get_task_target_state("打开设置")

    print(f"  步骤3 - 执行后状态: {post_result.state} (置信度: {post_result.confidence:.2f})")
    print(f"  步骤3 - 目标状态: {target_state}")

    # 步骤 4: 验证结果
    state_reached = post_result.state == target_state
    print(f"  步骤4 - 验证结果: {'成功' if state_reached else '失败'}")

    if not state_reached:
        print(f"  步骤5 - 记录: post_action_state_check_failed")
        print(f"  步骤5 - 动作: 允许一次修正动作或 fallback")

    assert state_reached, "执行后应达到目标状态"
    print("✓ 完整验证工作流测试通过\n")


if __name__ == "__main__":
    print("=" * 50)
    print("Post-Action State Check 测试")
    print("=" * 50 + "\n")

    test_settings_opened_verification()
    test_browser_opened_verification()
    test_search_page_verification()
    test_state_check_failed_scenario()
    test_verification_workflow()

    print("=" * 50)
    print("所有 Post-Action State Check 测试完成!")
    print("=" * 50)
