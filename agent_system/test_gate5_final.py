#!/usr/bin/env python3
"""
Gate 5 最终版：在设置中进入 Wi-Fi 页面
使用更精确的Wi-Fi检测逻辑
"""

import json
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
    """检查是否是Wi-Fi页面 - 更精确的检测"""
    prompt = "这是Wi-Fi设置页面吗？请只回答'是'或'否'，然后简要说明理由。"
    result = describe_with_qwen(image_path, prompt)
    text = result.get("text", "").lower()

    # 更精确的检测逻辑
    is_wifi = False
    if text.startswith("是"):
        is_wifi = True
    elif "wifi" in text or "wi-fi" in text or "无线" in text or "wlan" in text:
        # 检查是否包含Wi-Fi相关词汇
        if "设置" in text or "页面" in text or "界面" in text:
            is_wifi = True

    return is_wifi, result


def analyze_setting_layout(image_path):
    """分析设置页面布局"""
    prompt = """请分析这个设置页面的布局，回答以下问题：
1. 是否有搜索框？
2. 是否有"连接"或"网络"分类？
3. 是否有"Wi-Fi"或"无线网络"选项？
4. 页面顶部显示什么内容？
请用JSON格式回答：{"has_search_box": true/false, "has_connection_category": true/false, "has_wifi_option": true/false, "top_content": "描述"}"""

    result = describe_with_qwen(image_path, prompt)
    text = result.get("text", "")

    # 尝试解析JSON
    try:
        # 查找JSON部分
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            json_str = text[start:end]
            layout = json.loads(json_str)
            return layout
    except:
        pass

    # 如果解析失败，返回默认值
    return {
        "has_search_box": False,
        "has_connection_category": False,
        "has_wifi_option": False,
        "top_content": "未知",
    }


def main():
    """主函数"""
    print("=== Gate 5 最终版: 在设置中进入 Wi-Fi 页面 ===\n")

    # 记录起始状态
    print("## 第1步：记录起始状态")
    start_screenshot = "/tmp/gate5_final_start.png"
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

    # 分析设置布局
    print("\n## 第2步：分析设置页面布局")
    layout = analyze_setting_layout(start_screenshot)
    print(f"布局分析结果: {json.dumps(layout, ensure_ascii=False)}")

    # 第3步：尝试进入Wi-Fi页面
    print("\n## 第3步：尝试进入Wi-Fi页面")
    action_sequence = []
    wifi_found = False
    final_screenshot = start_screenshot
    final_desc = start_desc

    # 根据布局选择策略
    if layout.get("has_wifi_option"):
        print("布局显示有Wi-Fi选项，尝试点击Wi-Fi区域")
        # 尝试点击Wi-Fi区域（假设在页面中部）
        for y in [400, 500, 600, 700]:
            print(f"  尝试点击中部区域 (300, {y})")
            success, output = tap_screen(300, y)
            if success:
                action_sequence.append(f"点击中部区域({y})")
                time.sleep(2)

                # 检查结果
                check_screenshot = f"/tmp/gate5_wifi_check_{y}.png"
                capture_screen(check_screenshot)
                is_wifi, desc = check_is_wifi_page(check_screenshot)

                if is_wifi:
                    print("    ✓ 成功进入Wi-Fi页面")
                    wifi_found = True
                    final_screenshot = check_screenshot
                    final_desc = desc
                    break
                else:
                    print(f"    ✗ 未进入Wi-Fi页面: {desc.get('text', '无描述')[:50]}")
                    press_back()
                    time.sleep(1)

    if not wifi_found and layout.get("has_connection_category"):
        print("布局显示有连接分类，尝试点击连接分类")
        # 尝试点击连接分类区域
        for y in [350, 400, 450]:
            print(f"  尝试点击连接分类区域 (300, {y})")
            success, output = tap_screen(300, y)
            if success:
                action_sequence.append(f"点击连接分类({y})")
                time.sleep(2)

                # 检查是否进入连接设置页面
                check_screenshot = f"/tmp/gate5_connection_check_{y}.png"
                capture_screen(check_screenshot)
                check_desc = describe_with_qwen(check_screenshot, "这是网络或连接设置页面吗？")

                if "网络" in check_desc.get("text", "") or "连接" in check_desc.get("text", ""):
                    print("    ✓ 进入连接设置页面，尝试查找Wi-Fi")
                    # 在连接页面中查找Wi-Fi
                    for wifi_y in [400, 500, 600]:
                        print(f"      尝试点击Wi-Fi选项 (300, {wifi_y})")
                        tap_screen(300, wifi_y)
                        time.sleep(2)

                        wifi_check_screenshot = f"/tmp/gate5_wifi_in_connection_{wifi_y}.png"
                        capture_screen(wifi_check_screenshot)
                        is_wifi, desc = check_is_wifi_page(wifi_check_screenshot)

                        if is_wifi:
                            print("        ✓ 成功进入Wi-Fi页面")
                            wifi_found = True
                            final_screenshot = wifi_check_screenshot
                            final_desc = desc
                            action_sequence.append(f"点击Wi-Fi选项({wifi_y})")
                            break
                        else:
                            press_back()
                            time.sleep(1)

                    if wifi_found:
                        break

                # 如果不是连接页面，返回
                press_back()
                time.sleep(1)

    if not wifi_found and layout.get("has_search_box"):
        print("布局显示有搜索框，尝试使用搜索功能")
        # 点击搜索框
        print("  点击搜索框 (300, 150)")
        success, output = tap_screen(300, 150)
        if success:
            action_sequence.append("点击搜索框")
            time.sleep(1)

            # 输入Wi-Fi
            print("  输入Wi-Fi")
            execute_adb_command(["shell", "input", "text", "Wi-Fi"])
            time.sleep(1)

            # 点击搜索建议
            print("  点击搜索建议 (300, 300)")
            tap_screen(300, 300)
            time.sleep(2)

            # 检查结果
            search_screenshot = "/tmp/gate5_search_result.png"
            capture_screen(search_screenshot)
            is_wifi, desc = check_is_wifi_page(search_screenshot)

            if is_wifi:
                print("    ✓ 通过搜索成功进入Wi-Fi页面")
                wifi_found = True
                final_screenshot = search_screenshot
                final_desc = desc
            else:
                print(f"    ✗ 搜索未找到Wi-Fi页面: {desc.get('text', '无描述')[:50]}")
                press_back()
                time.sleep(1)

    # 如果以上策略都失败，尝试系统性的点击
    if not wifi_found:
        print("标准策略失败，尝试系统性点击")
        # 从顶部到底部系统性点击
        for y in range(300, 1000, 100):
            print(f"  尝试系统性点击 (300, {y})")
            success, output = tap_screen(300, y)
            if success:
                action_sequence.append(f"系统性点击({y})")
                time.sleep(2)

                # 检查结果
                sys_screenshot = f"/tmp/gate5_systematic_{y}.png"
                capture_screen(sys_screenshot)
                is_wifi, desc = check_is_wifi_page(sys_screenshot)

                if is_wifi:
                    print("    ✓ 系统性点击成功进入Wi-Fi页面")
                    wifi_found = True
                    final_screenshot = sys_screenshot
                    final_desc = desc
                    break
                else:
                    print("    ✗ 未进入Wi-Fi页面")
                    press_back()
                    time.sleep(1)

            # 每点击3次后向上滑动
            if y % 300 == 0:
                print("  向上滑动查看更多选项")
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
        print(
            f"- 备注：尝试多种策略后仍无法找到Wi-Fi页面，布局分析：{json.dumps(layout, ensure_ascii=False)}"
        )


if __name__ == "__main__":
    main()
