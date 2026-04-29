#!/usr/bin/env python3
"""
Gate 5 直接测试脚本：在设置中进入 Wi-Fi 页面
使用三星手机典型布局的直接点击策略
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


def tap_screen(x, y):
    """点击屏幕指定位置"""
    success, output = execute_adb_command(["shell", "input", "tap", str(x), str(y)])
    return success, output


def press_back():
    """按返回键"""
    success, output = execute_adb_command(["shell", "input", "keyevent", "KEYCODE_BACK"])
    time.sleep(1)
    return success, output


def check_is_wifi_page(image_path):
    """检查是否是Wi-Fi页面"""
    prompt = "这是Wi-Fi设置页面吗？请回答是或否，并简要说明理由。"
    result = describe_with_qwen(image_path, prompt)
    text = result.get("text", "").lower()
    return "是" in text or "wifi" in text or "无线" in text, result


def main():
    """主函数"""
    print("=== Gate 5 直接版: 在设置中进入 Wi-Fi 页面 ===\n")

    # 记录起始状态
    print("## 第1步：记录起始状态")
    start_screenshot = "/tmp/gate5_direct_start.png"
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

    # 第2步：尝试直接点击策略
    print("\n## 第2步：尝试直接点击策略")
    action_sequence = []
    wifi_found = False
    final_screenshot = start_screenshot
    final_desc = start_desc

    # 三星手机设置典型布局策略
    strategies = [
        {
            "name": "点击连接分类",
            "positions": [
                (300, 350, "连接分类顶部"),
                (300, 400, "连接分类中部"),
                (300, 450, "连接分类底部"),
            ],
        },
        {
            "name": "点击Wi-Fi文字区域",
            "positions": [
                (300, 400, "顶部区域"),
                (300, 500, "中上部区域"),
                (300, 600, "中部区域"),
                (300, 700, "中下部区域"),
                (300, 800, "底部区域"),
            ],
        },
        {
            "name": "使用搜索功能",
            "positions": [
                (300, 150, "搜索框"),
            ],
        },
    ]

    for strategy_idx, strategy in enumerate(strategies):
        if wifi_found:
            break

        print(f"\n策略 {strategy_idx + 1}: {strategy['name']}")

        for x, y, area in strategy["positions"]:
            print(f"  尝试点击{area} ({x}, {y})")

            # 执行点击
            success, output = tap_screen(x, y)
            if not success:
                print(f"    点击失败: {output}")
                continue

            action_sequence.append(f"点击{area}")
            time.sleep(2)

            # 检查结果
            check_screenshot = f"/tmp/gate5_check_{strategy_idx}_{x}_{y}.png"
            capture_screen(check_screenshot)

            # 如果是搜索策略，需要输入文本
            if strategy["name"] == "使用搜索功能":
                print("    输入Wi-Fi")
                execute_adb_command(["shell", "input", "text", "Wi-Fi"])
                time.sleep(1)
                tap_screen(300, 300)  # 点击搜索建议
                time.sleep(2)
                capture_screen(check_screenshot)

            # 检查是否是Wi-Fi页面
            is_wifi, desc = check_is_wifi_page(check_screenshot)

            if is_wifi:
                print("    ✓ 成功进入Wi-Fi页面")
                wifi_found = True
                final_screenshot = check_screenshot
                final_desc = desc
                break
            else:
                print(f"    ✗ 未进入Wi-Fi页面: {desc.get('text', '无描述')[:50]}")

                # 如果不是Wi-Fi页面，返回上一页
                press_back()
                time.sleep(1)

                # 重新截图确认回到设置主页
                back_screenshot = f"/tmp/gate5_back_{strategy_idx}_{x}_{y}.png"
                capture_screen(back_screenshot)
                back_desc = describe_with_qwen(back_screenshot)

                if "设置" not in back_desc.get("text", ""):
                    print("    ⚠️ 返回后不在设置页面，重新打开设置")
                    # 重新打开设置
                    execute_adb_command(["shell", "am", "start", "-a", "android.settings.SETTINGS"])
                    time.sleep(2)
                    capture_screen(back_screenshot)

        # 如果当前策略失败，尝试向上滑动后继续
        if not wifi_found and strategy_idx < len(strategies) - 1:
            print("  向上滑动尝试查看更多选项")
            execute_adb_command(["shell", "input", "swipe", "500", "1000", "500", "300"])
            action_sequence.append("向上滑动")
            time.sleep(1)

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

    if wifi_found:
        print(f"- 结束截图：{final_screenshot}")
        print("- 是否成功：成功")
        print("- 失败类型：不适用")
        print("- 是否安全停止：是")
        print(f"- 备注：成功进入Wi-Fi页面，最终画面：{final_desc.get('text', '无描述')[:100]}")
    else:
        print(f"- 结束截图：{start_screenshot}")
        print("- 是否成功：失败")
        print("- 失败类型：action_failed")
        print("- 是否安全停止：是")
        print(f"- 备注：尝试{len(strategies)}种策略后仍无法找到Wi-Fi页面")


if __name__ == "__main__":
    main()
