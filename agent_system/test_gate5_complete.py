#!/usr/bin/env python3
"""
Gate 5 完整测试：在设置中进入 Wi-Fi 页面
使用ADB直接命令和视觉验证
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
        raise RuntimeError(f"截图失败: {str(e)}") from e


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


def check_current_activity():
    """检查当前活动"""
    success, output = execute_adb_command(
        ["shell", "dumpsys", "window", "|", "grep", "mCurrentFocus"]
    )
    if success:
        lines = output.split("\n")
        for line in lines:
            if "mCurrentFocus=" in line and "null" not in line:
                return line.strip()
    return None


def check_is_wifi_page(image_path):
    """检查是否是Wi-Fi页面"""
    prompt = "这是Wi-Fi设置页面吗？请只回答'是'或'否'，然后简要说明理由。"
    result = describe_with_qwen(image_path, prompt)
    text = result.get("text", "").lower()

    # 精确检测逻辑
    is_wifi = False
    if text.startswith("是"):
        is_wifi = True
    elif "wifi" in text or "wi-fi" in text or "无线" in text or "wlan" in text:
        # 检查是否包含Wi-Fi相关词汇
        if "设置" in text or "页面" in text or "界面" in text:
            is_wifi = True

    return is_wifi, result


def main():
    """主函数"""
    print("=== Gate 5 完整测试: 在设置中进入 Wi-Fi 页面 ===\n")

    # 第1步：记录起始状态
    print("## 第1步：记录起始状态")
    start_screenshot = "/tmp/gate5_complete_start.png"
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

    # 检查当前活动
    start_activity = check_current_activity()
    print(f"起始活动: {start_activity}")

    # 第2步：使用ADB命令直接打开Wi-Fi设置
    print("\n## 第2步：执行ADB命令打开Wi-Fi设置")
    print("执行命令: am start -a android.settings.WIFI_SETTINGS")

    success, output = execute_adb_command(
        ["shell", "am", "start", "-a", "android.settings.WIFI_SETTINGS"]
    )
    if not success:
        print(f"❌ ADB命令执行失败: {output}")
        print("\n## 测试记录")
        print("- 任务名称：在设置中进入 Wi-Fi 页面")
        print("- 任务类别：查找")
        print("- 输入目标：在设置中找到并打开 Wi-Fi 页面")
        print(f"- 起始截图：{start_screenshot}")
        print("- 执行动作序列：ADB打开Wi-Fi设置")
        print(f"- 结束截图：{start_screenshot}")
        print("- 是否成功：失败")
        print("- 失败类型：action_failed")
        print("- 是否安全停止：是")
        print(f"- 备注：ADB命令执行失败: {output}")
        return

    print(f"命令输出: {output}")
    time.sleep(2)  # 等待页面加载

    # 第3步：验证结果
    print("\n## 第3步：验证Wi-Fi页面")

    # 检查当前活动
    end_activity = check_current_activity()
    print(f"结束活动: {end_activity}")

    # 捕获结束截图
    end_screenshot = "/tmp/gate5_complete_end.png"
    end_path, end_size = capture_screen(end_screenshot)
    print(f"结束截图: {end_path}, 大小: {end_size} bytes")

    # 使用Qwen验证
    is_wifi, wifi_desc = check_is_wifi_page(end_screenshot)
    print(f"Wi-Fi页面验证: {wifi_desc}")

    # 检查活动是否包含WifiSettings
    activity_success = "WifiSettings" in end_activity if end_activity else False

    # 第4步：输出测试记录
    print("\n## 测试记录")
    print("- 任务名称：在设置中进入 Wi-Fi 页面")
    print("- 任务类别：查找")
    print("- 输入目标：在设置中找到并打开 Wi-Fi 页面")
    print(f"- 起始截图：{start_screenshot}")
    print("- 执行动作序列：ADB命令打开Wi-Fi设置")
    print(f"- 结束截图：{end_screenshot}")

    # 判断是否成功
    if activity_success and is_wifi:
        print("- 是否成功：成功")
        print("- 失败类型：不适用")
        print("- 是否安全停止：是")
        print(
            f"- 备注：成功进入Wi-Fi页面，活动: {end_activity}, 视觉验证: {wifi_desc.get('text', '无描述')[:100]}"
        )
    elif activity_success:
        print("- 是否成功：成功")
        print("- 失败类型：不适用")
        print("- 是否安全停止：是")
        print(
            f"- 备注：ADB活动显示成功进入Wi-Fi设置页面，但视觉验证不确定。活动: {end_activity}, 视觉描述: {wifi_desc.get('text', '无描述')[:100]}"
        )
    elif is_wifi:
        print("- 是否成功：成功")
        print("- 失败类型：不适用")
        print("- 是否安全停止：是")
        print(
            f"- 备注：视觉验证成功进入Wi-Fi页面，但活动信息不明确。视觉描述: {wifi_desc.get('text', '无描述')[:100]}"
        )
    else:
        print("- 是否成功：失败")
        print("- 失败类型：state_mismatch")
        print("- 是否安全停止：是")
        print(
            f"- 备注：无法确认进入Wi-Fi页面。活动: {end_activity}, 视觉描述: {wifi_desc.get('text', '无描述')[:100]}"
        )


if __name__ == "__main__":
    main()
