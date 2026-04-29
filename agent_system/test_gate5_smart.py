#!/usr/bin/env python3
"""
Gate 5 智能测试脚本：在设置中进入 Wi-Fi 页面
使用更精确的视觉定位和智能搜索策略
"""

import json
import os
import subprocess
import sys
import time

import requests


def capture_screen(filename):
    """捕获屏幕截图"""
    try:
        proc = subprocess.Popen(
            ["adb", "-s", "R3CR80FKA0V", "exec-out", "screencap", "-p"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout_data, stderr_data = proc.communicate()
        png_header = b"\x89PNG\r\n\x1a\n"
        pos = stdout_data.find(png_header)
        if pos == -1:
            raise ValueError("未找到PNG文件头")
        png_data = stdout_data[pos:]
        with open(filename, "wb") as f:
            f.write(png_data)
        return filename, len(png_data)
    except Exception as e:
        raise RuntimeError(f"截图失败: {str(e)}")


def describe_with_qwen(image_path, prompt=None):
    """调用vision_router的qwen分支"""
    if prompt is None:
        prompt = "请用一句中文描述这张截图中最显眼的界面内容，不要猜测看不清的细节。"

    try:
        response = requests.post(
            "http://127.0.0.1:8001/describe",
            json={"image_path": image_path, "prompt": prompt},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}


def execute_adb_command(cmd):
    """执行adb命令"""
    try:
        result = subprocess.run(
            ["adb", "-s", "R3CR80FKA0V"] + cmd, capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        return False, str(e)


def tap_screen(x, y):
    """点击屏幕指定位置"""
    success, output = execute_adb_command(["shell", "input", "tap", str(x), str(y)])
    return success, output


def press_back():
    """按返回键"""
    success, output = execute_adb_command(["shell", "input", "keyevent", "KEYCODE_BACK"])
    time.sleep(1)
    return success, output


def swipe_up():
    """向上滑动（用于滚动查找）"""
    success, output = execute_adb_command(["shell", "input", "swipe", "500", "1000", "500", "300"])
    time.sleep(1)
    return success, output


def analyze_settings_layout(image_path):
    """分析设置页面布局，寻找Wi-Fi相关选项"""
    prompt = """请分析这张设置页面截图，回答以下问题：
1. 页面顶部是否有搜索框？
2. 页面中是否有"Wi-Fi"、"无线网络"、"WLAN"或类似文字？
3. 页面中是否有"连接"、"网络"、"互联网"或类似分类？
4. 如果有Wi-Fi相关选项，请描述它的位置特征（比如在第几个选项，大概在屏幕什么位置）
5. 页面中是否有滚动条，说明页面可以滚动？

请用JSON格式回答，包含以下字段：
- has_search_box: true/false
- has_wifi_text: true/false
- has_connection_category: true/false
- wifi_position: 描述文字，如"顶部第3个选项"、"中部连接分类下"等
- can_scroll: true/false
- description: 简要描述"""

    try:
        response = requests.post(
            "http://127.0.0.1:8001/describe",
            json={"image_path": image_path, "prompt": prompt},
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()

        if result.get("ok"):
            text = result.get("text", "")
            # 尝试解析JSON
            try:
                # 查找JSON部分
                start = text.find("{")
                end = text.rfind("}") + 1
                if start != -1 and end != 0:
                    json_str = text[start:end]
                    return json.loads(json_str)
            except:
                pass

        # 如果无法解析JSON，返回默认值
        return {
            "has_search_box": False,
            "has_wifi_text": False,
            "has_connection_category": False,
            "wifi_position": "未知",
            "can_scroll": True,
            "description": text[:100] if text else "无描述",
        }
    except Exception as e:
        return {
            "has_search_box": False,
            "has_wifi_text": False,
            "has_connection_category": False,
            "wifi_position": "未知",
            "can_scroll": True,
            "description": f"分析失败: {str(e)}",
        }


def find_wifi_by_strategy(image_path, strategy_data):
    """根据分析结果采用不同策略查找Wi-Fi"""
    print(f"布局分析结果: {json.dumps(strategy_data, ensure_ascii=False, indent=2)}")

    # 策略1: 如果有Wi-Fi文字，尝试点击常见位置
    if strategy_data.get("has_wifi_text"):
        print("策略1: 尝试点击Wi-Fi文字区域")
        # 常见Wi-Fi位置（基于三星手机设置布局）
        wifi_positions = [
            (300, 400, "顶部区域"),
            (300, 500, "中上部区域"),
            (300, 600, "中部区域"),
            (300, 700, "中下部区域"),
            (300, 800, "底部区域"),
        ]

        for x, y, area in wifi_positions:
            print(f"  尝试点击{area} ({x}, {y})")
            success, output = tap_screen(x, y)
            if not success:
                print(f"    点击失败: {output}")
                continue

            time.sleep(2)

            # 检查是否进入Wi-Fi页面
            check_screenshot = f"/tmp/gate5_check_{x}_{y}.png"
            capture_screen(check_screenshot)
            check_desc = describe_with_qwen(check_screenshot, "这是Wi-Fi设置页面吗？请回答是或否")

            if (
                "是" in check_desc.get("text", "").lower()
                or "wifi" in check_desc.get("text", "").lower()
            ):
                print(f"    ✓ 成功进入Wi-Fi页面")
                return True, check_screenshot, check_desc

            print(f"    ✗ 未进入Wi-Fi页面，返回上一页")
            press_back()
            time.sleep(1)

    # 策略2: 如果有连接分类，尝试点击连接区域
    if strategy_data.get("has_connection_category"):
        print("策略2: 尝试点击连接分类区域")
        # 连接分类通常在顶部
        connection_positions = [
            (300, 350, "连接分类顶部"),
            (300, 400, "连接分类中部"),
            (300, 450, "连接分类底部"),
        ]

        for x, y, area in connection_positions:
            print(f"  尝试点击{area} ({x}, {y})")
            success, output = tap_screen(x, y)
            if not success:
                print(f"    点击失败: {output}")
                continue

            time.sleep(2)

            # 检查是否进入连接设置页面
            check_screenshot = f"/tmp/gate5_connection_{x}_{y}.png"
            capture_screen(check_screenshot)
            check_desc = describe_with_qwen(
                check_screenshot, "这是网络连接设置页面吗？请回答是或否"
            )

            if (
                "是" in check_desc.get("text", "").lower()
                or "连接" in check_desc.get("text", "").lower()
            ):
                print(f"    ✓ 进入连接设置页面，查找Wi-Fi")
                # 在连接设置页面中查找Wi-Fi
                wifi_in_connection = find_wifi_in_connection(check_screenshot)
                if wifi_in_connection[0]:
                    return wifi_in_connection

            print(f"    ✗ 未进入连接设置页面，返回上一页")
            press_back()
            time.sleep(1)

    # 策略3: 尝试搜索功能
    print("策略3: 尝试使用搜索功能")
    if strategy_data.get("has_search_box"):
        print("  点击搜索框")
        tap_screen(300, 150)  # 搜索框通常在上部

        time.sleep(1)

        # 输入"Wi-Fi"
        print("  输入Wi-Fi")
        execute_adb_command(["shell", "input", "text", "Wi-Fi"])
        time.sleep(1)

        # 点击搜索建议
        print("  点击搜索建议")
        tap_screen(300, 300)
        time.sleep(2)

        # 检查结果
        search_screenshot = "/tmp/gate5_search_result.png"
        capture_screen(search_screenshot)
        search_desc = describe_with_qwen(search_screenshot, "这是Wi-Fi设置页面吗？请回答是或否")

        if (
            "是" in search_desc.get("text", "").lower()
            or "wifi" in search_desc.get("text", "").lower()
        ):
            print(f"    ✓ 通过搜索进入Wi-Fi页面")
            return True, search_screenshot, search_desc

        print(f"    ✗ 搜索未找到Wi-Fi，返回")
        press_back()
        time.sleep(1)

    return False, None, None


def find_wifi_in_connection(image_path):
    """在连接设置页面中查找Wi-Fi"""
    print("在连接设置页面中查找Wi-Fi...")

    # 连接页面中的Wi-Fi通常在上部
    connection_wifi_positions = [
        (300, 300, "连接页面顶部"),
        (300, 400, "连接页面中部"),
        (300, 500, "连接页面下部"),
    ]

    for x, y, area in connection_wifi_positions:
        print(f"  尝试点击{area} ({x}, {y})")
        success, output = tap_screen(x, y)
        if not success:
            print(f"    点击失败: {output}")
            continue

        time.sleep(2)

        # 检查是否进入Wi-Fi页面
        check_screenshot = f"/tmp/gate5_connection_wifi_{x}_{y}.png"
        capture_screen(check_screenshot)
        check_desc = describe_with_qwen(check_screenshot, "这是Wi-Fi设置页面吗？请回答是或否")

        if (
            "是" in check_desc.get("text", "").lower()
            or "wifi" in check_desc.get("text", "").lower()
        ):
            print(f"    ✓ 成功进入Wi-Fi页面")
            return True, check_screenshot, check_desc

        print(f"    ✗ 未进入Wi-Fi页面，返回上一页")
        press_back()
        time.sleep(1)

    return False, None, None


def main():
    """主函数"""
    print("=== Gate 5 智能版: 在设置中进入 Wi-Fi 页面 ===\n")

    # 记录起始状态
    print("## 第1步：记录起始状态")
    start_screenshot = "/tmp/gate5_smart_start.png"
    try:
        start_path, start_size = capture_screen(start_screenshot)
        print(f"起始截图: {start_path}, 大小: {start_size} bytes")
        start_desc = describe_with_qwen(start_path)
        print(f"起始画面描述: {start_desc}")
    except Exception as e:
        print(f"起始状态记录失败: {e}")
        return

    # 检查起始状态是否在设置应用内
    if not start_desc.get("ok") or "设置" not in start_desc.get("text", ""):
        print("❌ 起始状态不在设置应用内")
        print("\n## 测试记录")
        print("- 任务名称：在设置中进入 Wi-Fi 页面")
        print("- 任务类别：查找")
        print("- 输入目标：在设置中找到并打开 Wi-Fi 页面")
        print(f"- 起始截图：{start_screenshot}")
        print("- 执行动作序列：无")
        print(f"- 结束截图：{start_screenshot}")
        print("- 是否成功：失败")
        print("- 失败类型：state_mismatch")
        print("- 是否安全停止：是")
        print("- 备注：起始状态不在设置应用内，无法继续")
        return

    print("✓ 确认当前在设置应用内")

    # 分析设置页面布局
    print("\n## 第2步：分析设置页面布局")
    layout_analysis = analyze_settings_layout(start_screenshot)

    # 第3步：查找Wi-Fi入口
    print("\n## 第3步：查找Wi-Fi入口")
    wifi_attempts = 0
    wifi_success = False
    action_sequence = []

    while wifi_attempts < 2 and not wifi_success:
        wifi_attempts += 1
        print(f"\n尝试 {wifi_attempts}: 查找Wi-Fi入口")

        # 根据分析结果采用策略
        found, wifi_screenshot, wifi_desc = find_wifi_by_strategy(start_screenshot, layout_analysis)

        if found:
            wifi_success = True
            final_screenshot = wifi_screenshot
            final_desc = wifi_desc
            action_sequence.append(f"智能策略找到Wi-Fi")
            break

        # 如果第一次失败，尝试向上滑动后重新分析
        if wifi_attempts < 2 and layout_analysis.get("can_scroll", True):
            print("方法2: 向上滑动后重新分析")
            swipe_up()
            action_sequence.append("向上滑动")

            # 重新截图和分析
            current_screenshot = "/tmp/gate5_after_swipe.png"
            capture_screen(current_screenshot)
            layout_analysis = analyze_settings_layout(current_screenshot)

    # 输出测试记录
    print("\n## 测试记录")
    print("- 任务名称：在设置中进入 Wi-Fi 页面")
    print("- 任务类别：查找")
    print("- 输入目标：在设置中找到并打开 Wi-Fi 页面")
    print(f"- 起始截图：{start_screenshot}")

    if action_sequence:
        print(f"- 执行动作序列：{' -> '.join(action_sequence)}")
    else:
        print("- 执行动作序列：无")

    if wifi_success:
        print(f"- 结束截图：{final_screenshot}")
        print("- 是否成功：成功")
        print("- 失败类型：不适用")
        print("- 是否安全停止：是")
        print(f"- 备注：成功进入Wi-Fi页面，最终画面：{final_desc.get('text', '无描述')}")
    else:
        print(f"- 结束截图：{start_screenshot}")
        print("- 是否成功：失败")
        print("- 失败类型：action_failed")
        print("- 是否安全停止：是")
        print(
            f"- 备注：无法找到或进入Wi-Fi页面，尝试{wifi_attempts}次后失败，布局分析：{layout_analysis.get('description', '无分析结果')}"
        )


if __name__ == "__main__":
    main()
