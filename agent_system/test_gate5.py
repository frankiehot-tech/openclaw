#!/usr/bin/env python3
"""
Gate 5 测试脚本：在设置中进入 Wi-Fi 页面
"""

import subprocess
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


def is_settings_screen(description):
    """判断是否为设置屏幕"""
    if not description.get("ok"):
        return False
    text = description.get("text", "").lower()
    settings_keywords = ["设置", "settings", "系统设置", "配置", "关于手机", "galaxy", "三星"]
    return any(keyword in text for keyword in settings_keywords)


def is_wifi_screen(description):
    """判断是否为Wi-Fi页面"""
    if not description.get("ok"):
        return False
    text = description.get("text", "").lower()
    wifi_keywords = ["wifi", "wi-fi", "无线网络", "无线局域网", "wlan", "网络设置", "连接"]
    return any(keyword in text for keyword in wifi_keywords)


def find_wifi_entry(description):
    """基于视觉描述查找Wi-Fi入口"""
    if not description.get("ok"):
        return None, "视觉描述失败"

    description.get("text", "")

    # 尝试使用更具体的提示词获取Wi-Fi位置
    return None, "需要进一步分析"


def check_current_activity():
    """通过adb检查当前活动"""
    try:
        result = subprocess.run(
            ["adb", "-s", "R3CR80FKA0V", "shell", "dumpsys", "window", "windows"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        output = result.stdout

        # 查找当前活动
        if "com.android.settings" in output:
            return "settings"
        elif "wifi" in output.lower() or "wlan" in output.lower():
            return "wifi"
        return "unknown"
    except:
        return "error"


def tap_screen(x, y):
    """点击屏幕指定位置"""
    success, output = execute_adb_command(["shell", "input", "tap", str(x), str(y)])
    return success, output


def swipe_up():
    """向上滑动（用于滚动查找）"""
    success, output = execute_adb_command(["shell", "input", "swipe", "500", "1000", "500", "300"])
    return success, output


def main():
    """主函数"""
    print("=== Gate 5: 在设置中进入 Wi-Fi 页面 ===\n")

    # 记录起始状态
    print("## 第1步：记录起始状态")
    start_screenshot = "/tmp/gate5_start.png"
    try:
        start_path, start_size = capture_screen(start_screenshot)
        print(f"起始截图: {start_path}, 大小: {start_size} bytes")
        start_desc = describe_with_qwen(start_path)
        print(f"起始画面描述: {start_desc}")
    except Exception as e:
        print(f"起始状态记录失败: {e}")
        return

    # 检查起始状态是否在设置应用内
    if not is_settings_screen(start_desc):
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

    # 第2步：查找Wi-Fi入口
    print("\n## 第2步：查找Wi-Fi入口")
    wifi_attempts = 0
    wifi_success = False
    action_sequence = []

    while wifi_attempts < 2 and not wifi_success:
        wifi_attempts += 1
        print(f"\n尝试 {wifi_attempts}: 查找Wi-Fi入口")

        # 方法1：尝试直接搜索Wi-Fi文本
        print("方法1: 尝试点击Wi-Fi文本区域")

        # 使用更具体的提示词获取Wi-Fi位置信息
        wifi_prompt = "请描述这张设置页面截图，特别指出Wi-Fi、无线网络或类似选项的位置和文字"
        wifi_desc = describe_with_qwen(start_path, wifi_prompt)
        print(f"Wi-Fi定位描述: {wifi_desc}")

        # 尝试点击常见的Wi-Fi位置（基于三星手机设置布局）
        # 这些是经验坐标，可能需要调整
        common_wifi_positions = [
            (300, 400),  # 顶部附近
            (300, 600),  # 中部
            (300, 800),  # 中下部
        ]

        for pos_idx, (x, y) in enumerate(common_wifi_positions):
            print(f"  尝试点击位置 ({x}, {y})")
            success, output = tap_screen(x, y)
            if not success:
                print(f"  点击失败: {output}")
                continue

            action_sequence.append(f"点击位置({x},{y})")

            # 等待页面响应
            time.sleep(2)

            # 重新截图
            attempt_screenshot = f"/tmp/gate5_wifi_attempt{wifi_attempts}_pos{pos_idx}.png"
            try:
                attempt_path, attempt_size = capture_screen(attempt_screenshot)
                print(f"  尝试后截图: {attempt_path}, 大小: {attempt_size} bytes")
                attempt_desc = describe_with_qwen(attempt_path)
                print(f"  尝试后画面描述: {attempt_desc}")

                # 检查是否进入Wi-Fi页面
                if is_wifi_screen(attempt_desc):
                    print("  ✓ 确认已进入Wi-Fi页面")
                    wifi_success = True
                    final_screenshot = attempt_path
                    final_desc = attempt_desc
                    break
                else:
                    print("  ✗ 未进入Wi-Fi页面")

                    # 检查当前活动作为辅助验证
                    activity = check_current_activity()
                    if activity == "wifi":
                        print(f"  ⚠️ ADB检测到Wi-Fi活动: {activity}")
                        wifi_success = True
                        final_screenshot = attempt_path
                        final_desc = attempt_desc
                        break

                    # 返回上一页继续尝试
                    print("  返回上一页继续尝试")
                    execute_adb_command(["shell", "input", "keyevent", "KEYCODE_BACK"])
                    time.sleep(1)

            except Exception as e:
                print(f"  状态检查失败: {e}")

        if wifi_success:
            break

        # 方法2：尝试向上滑动后再次查找
        if wifi_attempts < 2:
            print("方法2: 向上滑动后重新查找")
            swipe_up()
            time.sleep(1)

            # 重新截图
            start_path, start_size = capture_screen(start_screenshot)
            start_desc = describe_with_qwen(start_path)
            action_sequence.append("向上滑动")

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
        print("- 备注：无法找到或进入Wi-Fi页面，尝试2次后失败")


if __name__ == "__main__":
    main()
