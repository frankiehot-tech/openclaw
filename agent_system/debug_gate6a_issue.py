#!/usr/bin/env python3
"""
调试 Gate 6A 问题：ADB vs 视觉冲突

问题：ADB认为在launcher，但视觉看到闹钟/日历
目标：查明真实情况并修复Gate 6A
"""

import os
import subprocess
import tempfile
import time
from typing import Any

DEVICE_ID = "R3CR80FKA0V"


def run_adb(cmd: list[str]) -> tuple[bool, str]:
    """运行adb命令"""
    try:
        result = subprocess.run(
            ["adb", "-s", DEVICE_ID] + cmd, capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        return False, str(e)


def capture_screen(filename: str) -> bool:
    """捕获屏幕截图"""
    try:
        proc = subprocess.Popen(
            ["adb", "-s", DEVICE_ID, "exec-out", "screencap", "-p"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout_data, stderr_data = proc.communicate()
        png_header = b"\x89PNG\r\n\x1a\n"
        pos = stdout_data.find(png_header)
        if pos == -1:
            print("错误: 未找到PNG文件头")
            return False
        png_data = stdout_data[pos:]
        with open(filename, "wb") as f:
            f.write(png_data)
        print(f"截图保存到: {filename}, 大小: {len(png_data)} bytes")
        return True
    except Exception as e:
        print(f"截图失败: {str(e)}")
        return False


def get_detailed_window_info() -> dict[str, Any]:
    """获取详细的窗口信息"""
    info = {
        "mCurrentFocus": None,
        "mFocusedApp": None,
        "mObscuringWindow": None,
        "mFocusedWindow": None,
        "topResumedActivity": None,
        "resumedActivity": None,
        "allWindows": [],
        "dumpsysWindowLines": [],
    }

    # 获取dumpsys window windows
    success, output = run_adb(["shell", "dumpsys", "window", "windows"])
    if success:
        lines = output.split("\n")
        info["dumpsysWindowLines"] = lines[:50]  # 只保存前50行
        for line in lines:
            if "mCurrentFocus=" in line:
                info["mCurrentFocus"] = line.strip()
            if "mFocusedApp=" in line:
                info["mFocusedApp"] = line.strip()
            if "mObscuringWindow=" in line:
                info["mObscuringWindow"] = line.strip()
            if "mFocusedWindow=" in line:
                info["mFocusedWindow"] = line.strip()
            if "Window #" in line:
                info["allWindows"].append(line.strip())

    # 获取dumpsys activity activities
    success2, output2 = run_adb(["shell", "dumpsys", "activity", "activities"])
    if success2:
        for line in output2.split("\n"):
            if "topResumedActivity" in line.lower() and "ActivityRecord" in line:
                info["topResumedActivity"] = line.strip()
            if "mResumedActivity" in line and "ActivityRecord" in line:
                info["resumedActivity"] = line.strip()

    # 获取dumpsys activity top
    success3, output3 = run_adb(["shell", "dumpsys", "activity", "top"])
    if success3:
        info["topActivityRaw"] = output3[:500]

    return info


def get_package_info() -> dict[str, Any]:
    """获取包信息"""
    info = {
        "currentPackage": None,
        "currentActivity": None,
        "currentTask": None,
    }

    # 获取当前包和活动
    success, output = run_adb(
        ["shell", "dumpsys", "window", "|", "grep", "-E", "mCurrentFocus|mFocusedApp"]
    )
    if success:
        for line in output.split("\n"):
            if "mCurrentFocus" in line:
                # 解析包名和活动名
                parts = line.split(" ")
                for part in parts:
                    if "com." in part and "/" in part:
                        package_activity = part.split(" ")
                        if len(package_activity) > 0:
                            full_name = package_activity[0]
                            if "/" in full_name:
                                package, activity = full_name.split("/")
                                info["currentPackage"] = package
                                info["currentActivity"] = activity
                                break

    # 使用简单命令获取当前包名
    success2, output2 = run_adb(["shell", "dumpsys", "window", "|", "grep", "mCurrentFocus"])
    if success2 and "=" in output2:
        # 提取包名
        import re

        match = re.search(r"[a-zA-Z0-9._]+/[\w.]+", output2)
        if match:
            full = match.group(0)
            if "/" in full:
                info["currentPackage"] = full.split("/")[0]
                info["currentActivity"] = full.split("/")[1]

    return info


def check_for_widgets() -> list[str]:
    """检查可能的widget"""
    widgets = []

    # 检查可能覆盖屏幕的widget
    success, output = run_adb(["shell", "dumpsys", "window", "|", "grep", "-i", "widget"])
    if success:
        lines = output.split("\n")
        for line in lines:
            if line.strip():
                widgets.append(line.strip())

    # 检查SystemUI状态
    success2, output2 = run_adb(["shell", "dumpsys", "notification"])
    if success2:
        lines = output2.split("\n")
        for _i, line in enumerate(lines[:20]):
            if "StatusBar" in line or "Notification" in line:
                widgets.append(f"通知相关: {line.strip()}")

    return widgets


def analyze_with_qwen(image_path: str) -> dict[str, Any]:
    """使用Qwen分析图片"""
    import requests

    try:
        prompt = """请仔细分析这张手机截图：
1. 界面顶部是否有状态栏（时间、信号、电池）？
2. 界面底部是否有导航条或应用栏？
3. 屏幕中间是否显示App图标网格（规则的4x5、5x5排列）？
4. 是否有明显的Widget（如天气、日历、时钟）占据大部分屏幕？
5. 这是手机桌面还是某个应用界面？

请用以下格式回答：
状态栏：有/无
底部导航：有/无
图标网格：有/无
大Widget：有/无
界面类型：桌面/应用界面/锁屏/其他
详细描述："""

        response = requests.post(
            "http://127.0.0.1:8001/describe",
            json={"image_path": image_path, "prompt": prompt},
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()

        analysis = {"ok": result.get("ok", False)}
        if result.get("ok"):
            text = result.get("text", "")
            analysis["raw_text"] = text

            # 解析回答
            for line in text.split("\n"):
                line = line.strip()
                if "状态栏：" in line:
                    analysis["has_status_bar"] = "有" in line
                elif "底部导航：" in line:
                    analysis["has_bottom_nav"] = "有" in line
                elif "图标网格：" in line:
                    analysis["has_icon_grid"] = "有" in line
                elif "大Widget：" in line:
                    analysis["has_large_widget"] = "有" in line
                elif "界面类型：" in line:
                    analysis["screen_type"] = line.split("：")[-1].strip()
                elif "详细描述：" in line:
                    analysis["description"] = line.split("：")[-1].strip()

        return analysis

    except Exception as e:
        return {"ok": False, "error": str(e)}


def take_multiple_screenshots(count: int = 3, delay: float = 1.0) -> list[str]:
    """连续多次截图以确认一致性"""
    screenshots = []
    temp_dir = tempfile.mkdtemp(prefix="debug_screens_")

    print(f"\n连续截图{count}次（间隔{delay}秒）:")
    for i in range(count):
        filename = os.path.join(temp_dir, f"screen_{i+1}.png")
        print(f"  第{i+1}次截图...")
        if capture_screen(filename):
            screenshots.append(filename)
            time.sleep(delay)
        else:
            print(f"  第{i+1}次截图失败")

    return screenshots


def compare_screenshots(files: list[str]) -> bool:
    """比较多个截图是否相同（简单哈希）"""
    if len(files) < 2:
        return True

    import hashlib

    hashes = []
    for file in files:
        with open(file, "rb") as f:
            data = f.read()
            file_hash = hashlib.md5(data).hexdigest()
            hashes.append(file_hash)

    # 检查所有哈希是否相同
    first_hash = hashes[0]
    all_same = all(h == first_hash for h in hashes)

    if all_same:
        print(f"所有截图相同（MD5: {first_hash[:8]}...）")
    else:
        print("截图不同！")
        for i, (file, h) in enumerate(zip(files, hashes, strict=False)):
            print(f"  截图{i+1}: {file} -> MD5: {h[:8]}...")

    return all_same


def main():
    print("=" * 80)
    print("Gate 6A 问题调试工具")
    print("=" * 80)

    # 第1步：检查设备连接
    print("\n1. 检查设备连接:")
    success, output = run_adb(["devices"])
    if success:
        print(f"设备列表:\n{output}")
    else:
        print(f"设备检查失败: {output}")

    # 第2步：获取详细窗口信息
    print("\n2. 获取详细窗口信息:")
    window_info = get_detailed_window_info()
    print(f"  mCurrentFocus: {window_info.get('mCurrentFocus')}")
    print(f"  mFocusedApp: {window_info.get('mFocusedApp')}")
    print(f"  mObscuringWindow: {window_info.get('mObscuringWindow')}")
    print(f"  topResumedActivity: {window_info.get('topResumedActivity')}")
    print(f"  resumedActivity: {window_info.get('resumedActivity')}")

    # 显示一些窗口信息
    if window_info.get("allWindows"):
        print("  前5个窗口:")
        for _i, win in enumerate(window_info.get("allWindows", [])[:5]):
            print(f"    {win}")

    # 第3步：获取包信息
    print("\n3. 获取包信息:")
    package_info = get_package_info()
    print(f"  当前包: {package_info.get('currentPackage')}")
    print(f"  当前活动: {package_info.get('currentActivity')}")

    # 第4步：检查widget
    print("\n4. 检查widget和覆盖层:")
    widgets = check_for_widgets()
    if widgets:
        print(f"  发现{len(widgets)}个widget/覆盖层:")
        for w in widgets[:5]:
            print(f"    {w}")
    else:
        print("  未发现widget或覆盖层")

    # 第5步：连续截图
    print("\n5. 连续截图确认一致性:")
    screenshots = take_multiple_screenshots(count=3, delay=1.0)

    if not screenshots:
        print("  截图全部失败，无法继续")
        return

    # 比较截图
    screenshots_consistent = compare_screenshots(screenshots)

    # 第6步：使用Qwen分析
    print("\n6. 视觉分析（使用Qwen）:")
    latest_screenshot = screenshots[-1] if screenshots else None
    if latest_screenshot:
        analysis = analyze_with_qwen(latest_screenshot)

        if analysis.get("ok"):
            print("  Qwen分析结果:")
            print(f"    状态栏: {'有' if analysis.get('has_status_bar') else '无'}")
            print(f"    底部导航: {'有' if analysis.get('has_bottom_nav') else '无'}")
            print(f"    图标网格: {'有' if analysis.get('has_icon_grid') else '无'}")
            print(f"    大Widget: {'有' if analysis.get('has_large_widget') else '无'}")
            print(f"    界面类型: {analysis.get('screen_type', '未知')}")
            if analysis.get("description"):
                print(f"    详细描述: {analysis.get('description')}")

            # 显示原始文本
            if "raw_text" in analysis:
                print("    原始回答:")
                for line in analysis["raw_text"].split("\n"):
                    print(f"      {line}")
        else:
            print(f"  Qwen分析失败: {analysis.get('error', '未知错误')}")

    # 第7步：手动检查建议
    print("\n7. 手动检查建议:")
    print("  如果ADB说在桌面但视觉说不是桌面，请检查:")
    print("  a) 截图是否正确（连续截图确认）")
    print("  b) 是否全屏Widget覆盖（如日历、时钟Widget）")
    print("  c) 是否锁屏或通知面板")
    print("  d) 视觉模型是否理解错误")

    # 第8步：综合判断
    print("\n8. 综合判断:")

    # 从ADB提取是否在launcher
    is_launcher_by_adb = False
    if window_info.get("mCurrentFocus"):
        focus = window_info.get("mCurrentFocus", "")
        is_launcher_by_adb = "launcher" in focus.lower() or "home" in focus.lower()

    # 从包信息提取
    is_launcher_by_package = False
    if package_info.get("currentPackage"):
        pkg = package_info.get("currentPackage", "")
        is_launcher_by_package = "launcher" in pkg.lower()

    # 从视觉分析提取
    is_desktop_by_vision = False
    if latest_screenshot and analysis.get("ok"):
        screen_type = analysis.get("screen_type", "")
        raw_text = analysis.get("raw_text", "")
        has_icon_grid = analysis.get("has_icon_grid", False)
        is_desktop_by_vision = "桌面" in screen_type or ("图标网格" in raw_text and has_icon_grid)

    print(f"  ADB判断在launcher: {is_launcher_by_adb or is_launcher_by_package}")
    print(f"  视觉判断是桌面: {is_desktop_by_vision}")

    if (is_launcher_by_adb or is_launcher_by_package) and not is_desktop_by_vision:
        print("  ⚠️ 冲突检测: ADB认为在launcher但视觉不认为是桌面")
        print("  可能原因:")
        print("    1. 视觉模型误判（明明是桌面但识别为其他）")
        print("    2. 全屏Widget覆盖（看起来不像传统桌面）")
        print("    3. 特殊桌面布局（如三星One UI的简化模式）")
    elif not (is_launcher_by_adb or is_launcher_by_package) and is_desktop_by_vision:
        print("  ⚠️ 冲突检测: 视觉认为是桌面但ADB不认为是launcher")
        print("  可能原因:")
        print("    1. ADB信息提取错误")
        print("    2. 系统UI状态异常")
    elif (is_launcher_by_adb or is_launcher_by_package) and is_desktop_by_vision:
        print("  ✅ 一致: ADB和视觉都确认在桌面")
    else:
        print("  ❌ 一致: ADB和视觉都确认不在桌面")

    # 第9步：修复建议
    print("\n9. 修复建议:")
    if screenshots_consistent and latest_screenshot:
        print(f"  截图文件: {latest_screenshot}")
        print("  建议操作:")
        print("    1. 人工查看截图确认内容")
        print("    2. 如果视觉误判，调整视觉分析prompt")
        print("    3. 如果ADB误判，改进ADB状态检测逻辑")
        print("    4. 如果是特殊界面，更新桌面检测逻辑")

    print(f"\n所有截图保存在: {os.path.dirname(latest_screenshot) if latest_screenshot else '无'}")


if __name__ == "__main__":
    main()
