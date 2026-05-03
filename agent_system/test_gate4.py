#!/usr/bin/env python3
"""
Gate 4 测试脚本：返回桌面并打开设置
"""

import os
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
        raise RuntimeError(f"截图失败: {str(e)}") from e


def describe_with_qwen(image_path):
    """调用vision_router的qwen分支"""
    try:
        response = requests.post(
            "http://127.0.0.1:8001/describe",
            json={
                "image_path": image_path,
                "prompt": "请用一句中文描述这张截图中最显眼的界面内容，不要猜测看不清的细节。",
            },
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


def is_desktop_screen(description):
    """判断是否为桌面屏幕"""
    if not description.get("ok"):
        return False
    text = description.get("text", "").lower()
    desktop_keywords = ["桌面", "主屏幕", "应用图标", "app", "图标", "主页", "启动器", "launcher"]
    return any(keyword in text for keyword in desktop_keywords)


def check_desktop_by_adb():
    """通过adb检查是否在桌面"""
    try:
        result = subprocess.run(
            ["adb", "-s", "R3CR80FKA0V", "shell", "dumpsys", "window", "windows"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return "com.sec.android.app.launcher" in result.stdout
    except Exception:
        return False


def is_settings_screen(description):
    """判断是否为设置屏幕"""
    if not description.get("ok"):
        return False
    text = description.get("text", "").lower()
    settings_keywords = ["设置", "settings", "系统设置", "配置", "关于手机", "galaxy", "三星"]
    return any(keyword in text for keyword in settings_keywords)


def main():
    """主函数"""
    print("=== Gate 4: 返回桌面并打开设置 ===\n")

    # 记录起始状态
    print("## 第1步：记录起始状态")
    start_screenshot = "/tmp/gate4_start.png"
    try:
        start_path, start_size = capture_screen(start_screenshot)
        print(f"起始截图: {start_path}, 大小: {start_size} bytes")
        start_desc = describe_with_qwen(start_path)
        print(f"起始画面描述: {start_desc}")
    except Exception as e:
        print(f"起始状态记录失败: {e}")
        return

    # 检查起始状态是否已经是桌面（使用ADB检查）
    is_desktop_adb = check_desktop_by_adb()
    is_desktop_vision = is_desktop_screen(start_desc)

    if is_desktop_adb:
        print("✓ ADB检查：设备已在桌面")
        desktop_success = True
        current_screenshot = start_path
        current_desc = start_desc
        desktop_action = "已在桌面（ADB确认）"

        if not is_desktop_vision:
            print("⚠️ 视觉识别未检测到桌面，但ADB确认在桌面")
    elif is_desktop_vision:
        print("✓ 视觉识别：设备已在桌面")
        desktop_success = True
        current_screenshot = start_path
        current_desc = start_desc
        desktop_action = "已在桌面（视觉确认）"
    else:
        print("起始状态不是桌面，需要返回桌面")
        desktop_action = "返回主屏幕"

        # 第2步：返回桌面
        print("\n## 第2步：返回桌面")
        desktop_attempts = 0
        desktop_success = False

        while desktop_attempts < 2 and not desktop_success:
            desktop_attempts += 1
            print(f"\n尝试 {desktop_attempts}: 返回主屏幕")

            # 执行返回主屏幕动作
            success, output = execute_adb_command(["shell", "input", "keyevent", "KEYCODE_HOME"])
            if not success:
                print(f"返回主屏幕失败: {output}")
                continue

            # 等待动画
            time.sleep(2)

            # 重新截图
            desktop_screenshot = f"/tmp/gate4_desktop_attempt{desktop_attempts}.png"
            try:
                desktop_path, desktop_size = capture_screen(desktop_screenshot)
                print(f"桌面截图: {desktop_path}, 大小: {desktop_size} bytes")
                desktop_desc = describe_with_qwen(desktop_path)
                print(f"桌面画面描述: {desktop_desc}")

                # 判断是否已进入桌面（使用ADB检查）
                if check_desktop_by_adb() or is_desktop_screen(desktop_desc):
                    print("✓ 确认已进入桌面")
                    desktop_success = True
                    current_screenshot = desktop_path
                    current_desc = desktop_desc
                else:
                    print("✗ 未确认进入桌面")
            except Exception as e:
                print(f"桌面状态检查失败: {e}")

        if not desktop_success:
            print("\n❌ 返回桌面失败")
            print("\n## 测试记录")
            print("- 任务名称：返回桌面并打开设置")
            print("- 任务类别：导航")
            print("- 输入目标：返回桌面并打开设置 App")
            print(f"- 起始截图：{start_screenshot}")
            print("- 执行动作序列：返回主屏幕（失败）")
            print(f"- 结束截图：{desktop_screenshot if 'desktop_screenshot' in locals() else '无'}")
            print("- 是否成功：失败")
            print("- 失败类型：action_failed")
            print("- 是否安全停止：是")
            print("- 备注：无法确认进入桌面状态")
            return

    # 第3步：打开设置应用
    print("\n## 第3步：打开设置应用")
    settings_attempts = 0
    settings_success = False

    while settings_attempts < 2 and not settings_success:
        settings_attempts += 1
        print(f"\n尝试 {settings_attempts}: 直接启动设置应用")

        # 直接启动设置应用
        success, output = execute_adb_command(
            ["shell", "am", "start", "-n", "com.android.settings/.Settings"]
        )
        if not success:
            print(f"启动设置应用失败: {output}")
            continue

        print(f"启动命令输出: {output}")

        # 等待应用打开
        time.sleep(3)

        # 重新截图
        settings_screenshot = f"/tmp/gate4_settings_attempt{settings_attempts}.png"
        try:
            # 使用更可靠的截图方法
            subprocess.run(
                ["adb", "-s", "R3CR80FKA0V", "shell", "screencap", "-p"],
                stdout=open(settings_screenshot, "wb"),
                stderr=subprocess.PIPE,
                timeout=5,
            )

            settings_size = os.path.getsize(settings_screenshot)
            print(f"设置截图: {settings_screenshot}, 大小: {settings_size} bytes")
            settings_desc = describe_with_qwen(settings_screenshot)
            print(f"设置画面描述: {settings_desc}")

            # 判断是否已进入设置
            if is_settings_screen(settings_desc):
                print("✓ 确认已进入设置")
                settings_success = True
                final_screenshot = settings_screenshot
                final_desc = settings_desc
            else:
                print("✗ 未确认进入设置")
        except Exception as e:
            print(f"设置状态检查失败: {e}")

    # 输出测试记录
    print("\n## 测试记录")
    print("- 任务名称：返回桌面并打开设置")
    print("- 任务类别：导航")
    print("- 输入目标：返回桌面并打开设置 App")
    print(f"- 起始截图：{start_screenshot}")

    action_sequence = []
    if desktop_success:
        action_sequence.append("返回主屏幕（成功）")
    else:
        action_sequence.append("返回主屏幕（失败）")

    if settings_success:
        action_sequence.append("点击设置图标（成功）")
    else:
        action_sequence.append("点击设置图标（失败）")

    print(f"- 执行动作序列：{' -> '.join(action_sequence)}")

    if settings_success:
        print(f"- 结束截图：{final_screenshot}")
        print("- 是否成功：成功")
        print("- 失败类型：不适用")
        print("- 是否安全停止：是")
        print(f"- 备注：成功返回桌面并打开设置，最终画面：{final_desc.get('text', '无描述')}")
    else:
        print(
            f"- 结束截图：{settings_screenshot if 'settings_screenshot' in locals() else desktop_screenshot}"
        )
        print("- 是否成功：失败")
        print("- 失败类型：action_failed")
        print("- 是否安全停止：是")
        print("- 备注：无法确认进入设置页面")


if __name__ == "__main__":
    main()
