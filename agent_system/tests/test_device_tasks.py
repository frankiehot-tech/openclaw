#!/usr/bin/env python3
"""
真机低风险任务验证脚本

执行低风险任务：
1. 打开设置
2. 打开浏览器
3. 点击搜索
4. 返回上一级
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
from vision.screen_analyzer import ScreenAnalyzer

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def execute_task_with_ocr(task_name: str, target_text: str, adb: ADBClient, screen_size: tuple):
    """
    使用 OCR grounding 执行任务

    Returns:
        (success: bool, method: str, details: str)
    """
    print(f"\n{'='*50}")
    print(f"任务: {task_name}")
    print(f"目标文本: {target_text}")
    print(f"{'='*50}")

    # 1. 截图
    screenshot_path = capture_screen(device_id=adb.device_id)
    if not screenshot_path:
        print(f"  ✗ 截图失败")
        return False, "screenshot_failed", "无法截取屏幕"
    print(f"  截图: {os.path.basename(screenshot_path)}")

    # 2. 初始化 OCR
    ocr_engine = get_ocr_engine(provider="easyocr")

    # 3. 执行 OCR
    ocr_results = ocr_engine.extract_text(screenshot_path)
    print(f"  OCR 识别到 {len(ocr_results)} 个文本块")

    # 4. 使用 ScreenAnalyzer 进行 UI Grounding
    analyzer = ScreenAnalyzer(ocr_provider="easyocr", screen_size=screen_size)

    analysis = analyzer.analyze_screen(screenshot_path, expected_targets=[target_text])

    # 5. 判断是否使用 OCR grounding
    if analysis.target_found:
        target = analysis.grounding_target
        center = target.get("center")
        confidence = target.get("confidence", 0)

        print(f"  ✓ OCR Grounding 命中!")
        print(f"    目标: {target.get('text')}")
        print(f"    位置: {center}")
        print(f"    置信度: {confidence:.2f}")

        # 执行点击
        x, y = center
        success = adb.tap(x, y)

        if success:
            print(f"  ✓ 点击成功: ({x}, {y})")
            return True, "ocr_grounding", f"OCR grounding 命中 {target_text} at {center}"
        else:
            print(f"  ✗ 点击失败")
            return False, "ocr_grounding", f"点击失败 at {center}"
    else:
        # 回退到 model inference
        print(f"  ○ OCR Grounding 未命中，回退到 model inference")

        # 尝试使用模型推断位置（这里简化为使用默认位置）
        # 实际使用时应该调用 LLM 来推断位置
        print(f"  ✗ Model inference 未实现，使用 fallback")
        return False, "model_inference_fallback", "OCR grounding 未命中，model inference 未实现"


def test_device_tasks():
    """测试真机低风险任务"""

    print("=" * 60)
    print("真机低风险任务验证")
    print("=" * 60)

    # 1. 初始化 ADB
    print("\n[1] 初始化 ADB...")
    device_id = get_default_device()
    if not device_id:
        print("  ✗ 未找到设备")
        return False

    adb = ADBClient(device_id)
    screen_size = adb.get_screen_size()
    print(f"  设备: {device_id}")
    print(f"  屏幕: {screen_size}")

    # 2. 唤醒屏幕
    print("\n[2] 唤醒屏幕...")
    adb.wake_screen()
    time.sleep(1)

    # 3. 回到主屏幕
    print("\n[3] 回到主屏幕...")
    adb.press_home()
    time.sleep(1)

    # 4. 执行任务
    results = []

    # 任务 1: 打开设置
    success, method, details = execute_task_with_ocr("打开设置", "设置", adb, screen_size)
    results.append({"task": "打开设置", "success": success, "method": method, "details": details})

    time.sleep(2)

    # 任务 2: 打开浏览器
    success, method, details = execute_task_with_ocr("打开浏览器", "浏览器", adb, screen_size)
    results.append({"task": "打开浏览器", "success": success, "method": method, "details": details})

    time.sleep(2)

    # 任务 3: 点击搜索
    success, method, details = execute_task_with_ocr("点击搜索", "搜索", adb, screen_size)
    results.append({"task": "点击搜索", "success": success, "method": method, "details": details})

    time.sleep(1)

    # 任务 4: 返回上一级
    print(f"\n{'='*50}")
    print("任务: 返回上一级")
    print(f"{'='*50}")
    success = adb.press_back()
    if success:
        print(f"  ✓ 返回成功")
        results.append(
            {
                "task": "返回上一级",
                "success": True,
                "method": "system_action",
                "details": "使用 ADB press_back",
            }
        )
    else:
        print(f"  ✗ 返回失败")
        results.append(
            {
                "task": "返回上一级",
                "success": False,
                "method": "system_action",
                "details": "ADB press_back 失败",
            }
        )

    # 5. 总结
    print("\n" + "=" * 60)
    print("任务执行总结")
    print("=" * 60)

    for r in results:
        status = "✓" if r["success"] else "✗"
        print(f"{status} {r['task']}")
        print(f"    方法: {r['method']}")
        print(f"    详情: {r['details']}")

    success_count = sum(1 for r in results if r["success"])
    print(f"\n成功: {success_count}/{len(results)}")

    # 6. 统计方法
    ocr_count = sum(1 for r in results if r["method"] == "ocr_grounding")
    model_count = sum(1 for r in results if r["method"] == "model_inference_fallback")
    system_count = sum(1 for r in results if r["method"] == "system_action")

    print(f"\n方法统计:")
    print(f"  - OCR Grounding: {ocr_count}")
    print(f"  - Model Inference: {model_count}")
    print(f"  - System Action: {system_count}")

    return success_count > 0


if __name__ == "__main__":
    try:
        success = test_device_tasks()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
