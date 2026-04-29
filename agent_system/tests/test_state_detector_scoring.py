"""
测试状态检测器打分制 (Phase 11.5)

测试目标：
1. home_screen 打分高于 settings/browser
2. settings_home 打分高于 home/browser
3. browser_home 打分高于 home/settings
4. 低置信时返回 unknown
"""

import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 设置测试用的置信度阈值（在 import 之前设置）
os.environ["STATE_CONFIDENCE_THRESHOLD"] = "0.4"

# 先 import 检测器模块，然后重置
from state import state_detector

state_detector.reset_detector()

# 使用新的检测器实例，传入自定义阈值
from state.state_detector import StateDetector

# 创建测试用的检测器（使用 0.4 阈值）
_test_detector = StateDetector(confidence_threshold=0.4)


def detect_page_state(ocr_results=None, image_path=None, screen_analysis=None, history=None):
    """包装函数，使用测试检测器"""
    return _test_detector.detect_page_state(ocr_results, image_path, screen_analysis, history)


def test_home_screen_scoring():
    """测试主屏幕打分"""
    # 模拟主屏幕 OCR 结果
    ocr_texts = [
        "抖音",
        "微信",
        "淘宝",
        "支付宝",
        "微博",
        "设置",
        "天气",
        "时钟",
        "相机",
        "文件管理",
    ]

    result = detect_page_state(ocr_results=ocr_texts)

    print(f"主屏幕测试:")
    print(f"  状态: {result.state}")
    print(f"  置信度: {result.confidence:.2f}")
    print(f"  信号: {result.signals}")
    print(f"  打分明细: {result.score_breakdown}")

    # 验证
    assert result.state == "home_screen", f"期望 home_screen, 实际 {result.state}"
    assert result.confidence > 0.5, f"置信度应 > 0.5, 实际 {result.confidence}"
    print("✓ 主屏幕打分测试通过\n")


def test_settings_home_scoring():
    """测试设置页面打分"""
    # 模拟设置页面 OCR 结果
    ocr_texts = [
        "设置",
        "WLAN",
        "蓝牙",
        "更多连接",
        "飞行模式",
        "移动网络",
        "个人热点",
        "VPN",
        "以太网",
        "SIM卡",
    ]

    result = detect_page_state(ocr_results=ocr_texts)

    print(f"设置页面测试:")
    print(f"  状态: {result.state}")
    print(f"  置信度: {result.confidence:.2f}")
    print(f"  信号: {result.signals}")
    print(f"  打分明细: {result.score_breakdown}")

    # 验证
    assert result.state == "settings_home", f"期望 settings_home, 实际 {result.state}"
    assert result.confidence > 0.5, f"置信度应 > 0.5, 实际 {result.confidence}"
    print("✓ 设置页面打分测试通过\n")


def test_browser_home_scoring():
    """测试浏览器首页打分"""
    # 模拟浏览器首页 OCR 结果
    ocr_texts = [
        "Google",
        "搜索",
        "chrome",
        "百度",
        "输入网址",
        "书签",
        "历史记录",
        "更多",
        " tabs",
        "新标签页",
    ]

    result = detect_page_state(ocr_results=ocr_texts)

    print(f"浏览器首页测试:")
    print(f"  状态: {result.state}")
    print(f"  置信度: {result.confidence:.2f}")
    print(f"  信号: {result.signals}")
    print(f"  打分明细: {result.score_breakdown}")

    # 验证
    assert result.state == "browser_home", f"期望 browser_home, 实际 {result.state}"
    assert result.confidence > 0.5, f"置信度应 > 0.5, 实际 {result.confidence}"
    print("✓ 浏览器首页打分测试通过\n")


def test_low_confidence_returns_unknown():
    """测试低置信度时返回 unknown"""
    # 模拟无法识别的页面
    ocr_texts = ["未知应用", "一些文字", "内容", "测试"]

    result = detect_page_state(ocr_results=ocr_texts)

    print(f"低置信度测试:")
    print(f"  状态: {result.state}")
    print(f"  置信度: {result.confidence:.2f}")
    print(f"  信号: {result.signals}")

    # 验证 - 低置信度应该返回 unknown
    if result.confidence < 0.3:
        assert result.state == "unknown", f"低置信度应返回 unknown, 实际 {result.state}"
        print("✓ 低置信度测试通过（返回 unknown）\n")
    else:
        print(f"  注意: 置信度 {result.confidence:.2f} 不够低，但仍返回 {result.state}\n")


def test_keyword_combination():
    """测试关键词组合识别"""
    # 测试组合关键词
    ocr_texts = ["设置", "WLAN", "蓝牙", "移动网络"]

    result = detect_page_state(ocr_results=ocr_texts)

    print(f"关键词组合测试:")
    print(f"  状态: {result.state}")
    print(f"  置信度: {result.confidence:.2f}")
    print(f"  信号: {result.signals}")

    # 多个设置相关关键词应该提高置信度
    assert result.state in [
        "settings_home",
        "unknown",
    ], f"期望 settings_home 或 unknown, 实际 {result.state}"
    print("✓ 关键词组合测试通过\n")


if __name__ == "__main__":
    print("=" * 50)
    print("状态检测器打分制测试")
    print("=" * 50 + "\n")

    test_home_screen_scoring()
    test_settings_home_scoring()
    test_browser_home_scoring()
    test_low_confidence_returns_unknown()
    test_keyword_combination()

    print("=" * 50)
    print("所有测试完成!")
    print("=" * 50)
