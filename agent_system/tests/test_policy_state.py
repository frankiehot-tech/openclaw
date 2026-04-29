"""
测试 Policy + State 模块集成

验证：
1. 白名单检查
2. 页面状态检测
3. 状态规划
4. 完整执行链路
"""

import logging
import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

from policy.task_whitelist import is_task_allowed, reject_if_not_allowed
from state.simple_state_planner import PlanResult, plan_next_step
from state.state_detector import DetectionResult, detect_page_state


def test_whitelist():
    """测试白名单"""
    print("\n" + "=" * 50)
    print("测试 1: 白名单检查")
    print("=" * 50)

    # 测试允许的任务
    allowed_tasks = [
        "打开设置",
        "打开浏览器",
        "点击搜索",
        "返回上一级",
        "打开相机",
    ]

    for task in allowed_tasks:
        result = is_task_allowed(task)
        print(f"  {task}: {'✓ 允许' if result else '✗ 拒绝'}")

    # 测试拒绝的任务
    denied_tasks = [
        "删除所有照片",
        "发送短信给 10086",
        "打开支付宝转账",
        "卸载微信",
    ]

    for task in denied_tasks:
        result = is_task_allowed(task)
        if not result:
            reject = reject_if_not_allowed(task)
            print(f"  {task}: ✗ 拒绝 - {reject.get('reason', 'unknown')}")
        else:
            print(f"  {task}: ✓ 允许 (意外)")


def test_state_detection():
    """测试页面状态检测"""
    print("\n" + "=" * 50)
    print("测试 2: 页面状态检测")
    print("=" * 50)

    # 模拟 OCR 结果
    test_cases = [
        {"name": "主屏幕", "ocr_results": ["设置", "Google", "相机", "天气", "时钟", "应用"]},
        {"name": "设置首页", "ocr_results": ["设置", "Wi-Fi", "蓝牙", "显示", "声音", "应用程序"]},
        {"name": "浏览器首页", "ocr_results": ["Google", "chrome", "浏览器", "搜索", "地址"]},
        {"name": "未知页面", "ocr_results": ["未知内容", "abc", "123"]},
    ]

    for case in test_cases:
        result = detect_page_state(ocr_results=case["ocr_results"])
        print(f"  {case['name']}:")
        print(f"    状态: {result.state}")
        print(f"    置信度: {result.confidence:.2f}")
        print(f"    信号: {result.signals}")


def test_state_planner():
    """测试状态规划"""
    print("\n" + "=" * 50)
    print("测试 3: 状态规划")
    print("=" * 50)

    # 测试不同任务 + 状态组合
    test_cases = [
        {"task": "打开设置", "state": "home_screen"},
        {"task": "打开设置", "state": "settings_home"},
        {"task": "打开浏览器", "state": "home_screen"},
        {"task": "打开浏览器", "state": "browser_home"},
        {"task": "点击搜索", "state": "browser_home"},
        {"task": "返回上一级", "state": "settings_home"},
    ]

    for case in test_cases:
        result = plan_next_step(case["task"], case["state"])
        print(f"  任务: {case['task']}, 状态: {case['state']}")
        print(f"    规划类型: {result.plan_type}")
        print(f"    原因: {result.reason}")
        if result.requires_precondition:
            print(f"    前置动作: {result.precondition_action}")
        print()


def test_full_flow():
    """测试完整流程"""
    print("\n" + "=" * 50)
    print("测试 4: 完整流程")
    print("=" * 50)

    task = "打开设置"

    # 1. 白名单检查
    if not is_task_allowed(task):
        reject = reject_if_not_allowed(task)
        print(f"  任务被拒绝: {reject}")
        return

    print(f"  ✓ 白名单检查通过: {task}")

    # 2. 模拟页面状态检测
    ocr_results = ["设置", "Google", "相机", "天气"]
    state_result = detect_page_state(ocr_results=ocr_results)
    print(f"  ✓ 页面状态: {state_result.state} (置信度: {state_result.confidence:.2f})")

    # 3. 状态规划
    plan_result = plan_next_step(task, state_result.state)
    print(f"  ✓ 规划类型: {plan_result.plan_type}")
    print(f"  ✓ 规划原因: {plan_result.reason}")

    if plan_result.requires_precondition:
        print(f"  ✓ 需要前置动作: {plan_result.precondition_action}")

    print("\n  完整流程测试通过!")


if __name__ == "__main__":
    print("=" * 50)
    print("Policy + State 模块测试")
    print("=" * 50)

    test_whitelist()
    test_state_detection()
    test_state_planner()
    test_full_flow()

    print("\n" + "=" * 50)
    print("所有测试完成!")
    print("=" * 50)
