#!/usr/bin/env python3
"""
EasyOCR 真机验证脚本

测试 EasyOCR 在真机截图上的 OCR 识别能力
"""

import logging
import os
import sys
import time

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from device_control.adb_client import ADBClient, get_default_device
from device_control.screen_capture import capture_screen
from vision.ocr_engine import get_ocr_engine

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def test_easyocr_on_device():
    """测试 EasyOCR 在真机上的 OCR 能力"""

    print("=" * 60)
    print("EasyOCR 真机验证测试")
    print("=" * 60)

    # 1. 初始化 ADB
    print("\n[1] 初始化 ADB 客户端...")
    device_id = get_default_device()
    if not device_id:
        print("    未找到设备!")
        return False

    adb = ADBClient(device_id)
    devices = adb.list_devices()
    print(f"    设备序列号: {device_id}")
    print(f"    设备状态: {devices[0]['status'] if devices else 'Unknown'}")

    # 获取屏幕尺寸
    screen_size = adb.get_screen_size()
    print(f"    屏幕分辨率: {screen_size}")

    # 2. 截图
    print("\n[2] 截取屏幕...")
    screenshot_path = capture_screen(device_id=device_id)
    if not screenshot_path:
        print("    截图失败!")
        return False
    print(f"    截图保存至: {screenshot_path}")

    # 3. 初始化 EasyOCR
    print("\n[3] 初始化 EasyOCR...")
    ocr_engine = get_ocr_engine(provider="easyocr")
    print(f"    OCR Engine: {type(ocr_engine).__name__}")

    # 4. 执行 OCR
    print("\n[4] 执行 OCR 识别...")
    start_time = time.time()
    ocr_results = ocr_engine.extract_text(screenshot_path)
    elapsed = time.time() - start_time

    print(f"    识别耗时: {elapsed:.2f} 秒")
    print(f"    识别到 {len(ocr_results)} 个文本块")

    # 5. 显示结果
    print("\n[5] OCR 识别结果:")
    if ocr_results:
        for i, result in enumerate(ocr_results[:10]):  # 只显示前10个
            text = result.text[:30] + "..." if len(result.text) > 30 else result.text
            conf = result.confidence
            print(f"    {i+1}. [{conf:.2f}] {text}")
    else:
        print("    未识别到任何文本")

    # 6. 测试 UI Grounding
    print("\n[6] 测试 UI Grounding...")
    from vision.screen_analyzer import ScreenAnalyzer

    # 初始化 ScreenAnalyzer
    analyzer = ScreenAnalyzer(ocr_provider="easyocr", screen_size=screen_size or (1080, 2640))

    # 分析屏幕
    analysis = analyzer.analyze_screen(
        screenshot_path, expected_targets=["设置", "搜索", "浏览器", "返回"]
    )

    print(f"    文本块数量: {analysis.ocr_blocks_count}")
    print(f"    目标找到: {analysis.target_found}")

    if analysis.grounding_target:
        target = analysis.grounding_target
        print(f"    目标文本: {target.get('text', 'N/A')}")
        print(f"    目标位置: {target.get('center', 'N/A')}")
        print(f"    置信度: {target.get('confidence', 0):.2f}")

    # 7. 总结
    print("\n" + "=" * 60)
    print("测试结果总结")
    print("=" * 60)

    if len(ocr_results) > 0:
        print("✓ EasyOCR 工作正常")
        print(f"  - 识别到 {len(ocr_results)} 个文本")
        print(f"  - 识别耗时 {elapsed:.2f} 秒")
    else:
        print("✗ EasyOCR 未识别到文本")

    if analysis.target_found:
        print("✓ UI Grounding 工作正常")
        print(f"  - 目标: {analysis.grounding_target.get('text')}")
    else:
        print("○ UI Grounding 未找到目标（可能需要调整阈值）")

    return len(ocr_results) > 0


if __name__ == "__main__":
    try:
        success = test_easyocr_on_device()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
