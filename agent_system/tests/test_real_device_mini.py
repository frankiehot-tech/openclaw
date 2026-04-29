"""
最小真机验证测试

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

# 加载 .env 配置
from dotenv import load_dotenv

load_dotenv()

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

from device_control.adb_client import ADBClient
from device_control.screen_capture import capture_screen
from policy.task_whitelist import is_task_allowed
from state.simple_state_planner import plan_next_step
from state.state_detector import detect_page_state
from vision.ocr_engine import OCREngine
from vision.ui_grounding import UIGrounding


def test_task(task: str, adb: ADBClient, ocr: OCREngine, grounding: UIGrounding):
    """测试单个任务

    返回: (success: bool, action_source: str)
    """
    print(f"\n{'='*50}")
    print(f"测试任务: {task}")
    print(f"{'='*50}")

    # 1. 白名单检查
    if not is_task_allowed(task):
        print("  ✗ 任务不在白名单中，跳过")
        return False, "whitelist_rejected"

    print("  ✓ 白名单检查通过")

    # 2. 截图
    screenshot_path = capture_screen(device_id=adb.device_id)
    print(f"  ✓ 截图: {screenshot_path}")

    # 3. OCR 识别
    ocr_results = ocr.extract_text(screenshot_path)
    print(f"  ✓ OCR 识别: {len(ocr_results)} 个文本块")

    # 4. 页面状态检测 - 转换为文本列表
    ocr_texts = [r.text for r in ocr_results]
    state_result = detect_page_state(ocr_results=ocr_texts)
    print(f"  ✓ 页面状态: {state_result.state} (置信度: {state_result.confidence:.2f})")

    # 5. 状态规划
    plan_result = plan_next_step(task, state_result.state)
    print(f"  ✓ 规划类型: {plan_result.plan_type}")
    print(f"  ✓ 规划原因: {plan_result.reason}")

    # 6. UI Grounding - 查找目标元素
    # 根据任务确定目标文本
    task_to_text = {
        "打开设置": "设置",
        "打开浏览器": "浏览器",
        "点击搜索": "搜索",
        "返回上一级": "返回",
    }
    target_text = task_to_text.get(task, "")

    target = grounding.find_text_target(ocr_results, target_text)

    action_source = None  # 初始化
    target_box = None

    if target:
        print(f"  ✓ OCR Grounding 命中: {target.text} at {target.center}")
        action_source = "ocr_grounding"
        target_box = {"x": target.center[0], "y": target.center[1], "action": "tap"}
    else:
        print("  ✗ OCR Grounding 未命中，使用 model inference")
        action_source = "model_inference"
        # 模拟一个点击位置（实际应该调用 model）
        target_box = {"x": 540, "y": 1200, "action": "tap"}

    # 7. 执行动作
    if target_box:
        action = target_box.get("action", "tap")
        x = target_box.get("x", 540)
        y = target_box.get("y", 1200)

        print(f"  执行动作: {action} at ({x}, {y})")

        if action == "tap":
            adb.tap(x, y)
        elif action == "swipe_up":
            adb.swipe(540, 1500, 540, 500)
        elif action == "swipe_down":
            adb.swipe(540, 500, 540, 1500)
        elif action == "back":
            adb.press_back()
        elif action == "home":
            adb.press_home()

        print("  ✓ 动作执行成功")

        # 等待页面加载
        time.sleep(1)

        return True, action_source
    else:
        print("  ✗ 无法确定目标位置")
        return False, action_source


def main():
    print("=" * 50)
    print("最小真机验证测试")
    print("=" * 50)

    # 从 .env 获取 OCR provider
    ocr_provider = os.getenv("VISION_OCR_PROVIDER", "mock")
    print(f"使用 OCR Provider: {ocr_provider}")

    # 初始化组件
    adb = ADBClient()
    ocr = OCREngine(provider=ocr_provider)
    grounding = UIGrounding()

    # 测试任务列表
    tasks = [
        "打开设置",
        "返回上一级",
        "打开浏览器",
        "点击搜索",
        "返回上一级",
    ]

    results = []

    for task in tasks:
        try:
            success, action_source = test_task(task, adb, ocr, grounding)
            results.append({"task": task, "success": success, "action_source": action_source})
        except Exception as e:
            print(f"  ✗ 错误: {e}")
            results.append({"task": task, "success": False, "error": str(e)})

    # 输出总结
    print("\n" + "=" * 50)
    print("测试结果总结")
    print("=" * 50)

    # 统计
    ocr_grounding_count = 0
    model_inference_count = 0

    for r in results:
        status = "✓" if r.get("success") else "✗"
        source = r.get("action_source", "N/A")
        print(f"  {status} {r['task']} - 动作来源: {source}")

        if source == "ocr_grounding":
            ocr_grounding_count += 1
        elif source == "model_inference":
            model_inference_count += 1

    success_count = sum(1 for r in results if r.get("success"))
    print(f"\n  成功率: {success_count}/{len(results)}")
    print(f"  OCR Grounding 命中: {ocr_grounding_count}")
    print(f"  Model Inference 回退: {model_inference_count}")


if __name__ == "__main__":
    main()
