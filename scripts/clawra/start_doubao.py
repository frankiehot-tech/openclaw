#!/usr/bin/env python3
"""
启动豆包应用并验证状态
"""

import os
import signal
import subprocess
import sys
import time


def run_applescript(script):
    """运行AppleScript命令"""
    try:
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, timeout=15
        )
        return result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return "", "AppleScript执行超时"
    except Exception as e:
        return "", f"AppleScript执行错误: {e}"


def check_app_running(app_name):
    """检查应用是否运行"""
    script = f"""
tell application "System Events"
    set appList to name of every process whose background only is false
    return appList contains "{app_name}"
end tell
"""
    result, error = run_applescript(script)
    if error:
        print(f"❌ 检查应用状态时出错: {error}")
        return False

    return result.lower() == "true"


def launch_app(app_name):
    """启动应用"""
    print(f"启动 {app_name} 应用...")

    # 尝试不同的启动方式
    methods = [
        # 方式1：使用open命令
        f'open -a "{app_name}"',
        # 方式2：使用AppleScript
        f"""osascript -e 'tell application "{app_name}" to activate' """,
        # 方式3：使用open的特定路径
        f'open "/Applications/{app_name}.app"',
    ]

    for method in methods:
        try:
            print(f"尝试: {method}")
            os.system(method)
            time.sleep(3)  # 等待应用启动

            # 检查是否启动成功
            if check_app_running(app_name):
                print(f"✅ {app_name} 启动成功")
                return True

        except Exception as e:
            print(f"尝试失败: {e}")
            continue

    return False


def wait_for_app_ready(app_name, timeout=30):
    """等待应用完全就绪"""
    print(f"等待 {app_name} 应用就绪...")

    start_time = time.time()
    while time.time() - start_time < timeout:
        # 检查应用是否在前台
        script = f"""
tell application "System Events"
    if exists process "{app_name}" then
        set frontmost of process "{app_name}" to true
        return "ready"
    else
        return "not running"
    end if
end tell
"""
        result, error = run_applescript(script)

        if "ready" in result:
            print(f"✅ {app_name} 已就绪并在前台")
            return True

        print(f"等待中... ({int(time.time() - start_time)}秒)")
        time.sleep(2)

    print(f"⚠️ 应用启动超时 ({timeout}秒)")
    return False


def check_doubao_specifics():
    """检查豆包特定状态"""
    print("\n检查豆包特定状态...")

    # 检查豆包窗口标题
    script = """
tell application "System Events"
    tell process "豆包"
        set windowCount to count of windows
        if windowCount > 0 then
            set windowNames to name of every window
            return "窗口数量: " & windowCount & ", 窗口标题: " & (windowNames as text)
        else
            return "无窗口"
        end if
    end tell
end tell
"""
    result, error = run_applescript(script)

    if error:
        print(f"❌ 检查窗口时出错: {error}")
    else:
        print(f"窗口状态: {result}")

        # 检查是否有"登录"或"聊天"相关元素
        if "登录" in result or "login" in result.lower():
            print("⚠️ 检测到登录界面，可能需要登录")
            return "login_needed"
        elif "聊天" in result or "chat" in result.lower() or "对话" in result:
            print("✅ 检测到聊天界面")
            return "chat_ready"
        else:
            print("⚠️ 无法确定界面类型")
            return "unknown"


def main():
    print("=" * 60)
    print("豆包应用启动器")
    print("=" * 60)

    app_names = ["豆包", "Doubao", "Doubao AI"]

    # 首先检查是否已运行
    for app_name in app_names:
        if check_app_running(app_name):
            print(f"✅ {app_name} 已在运行")

            # 确保应用在前台
            script = f"""
tell application "System Events"
    tell process "{app_name}"
        set frontmost to true
    end tell
end tell
"""
            run_applescript(script)
            print(f"已将 {app_name} 置于前台")

            status = check_doubao_specifics()
            print(f"\n启动状态: {status}")

            # 根据状态提供建议
            if status == "login_needed":
                print("\n📝 下一步:")
                print("1. 手动登录豆包账户")
                print("2. 进入AI聊天界面")
                print("3. 然后重新运行自动化脚本")
            elif status == "chat_ready":
                print("\n📝 下一步:")
                print("1. 保持豆包窗口打开")
                print("2. 运行自动化测试脚本")
                print("3. 监控执行过程")

            return True

    # 如果没有运行，尝试启动
    print("豆包应用未运行，尝试启动...")

    for app_name in app_names:
        print(f"\n尝试使用名称: {app_name}")
        if launch_app(app_name):
            if wait_for_app_ready(app_name):
                status = check_doubao_specifics()
                print(f"\n启动完成，状态: {status}")

                # 提供具体建议
                if status == "login_needed":
                    print("\n⚠️ 重要：请手动完成以下步骤:")
                    print("1. 在豆包界面中登录账户")
                    print("2. 进入AI聊天界面")
                    print("3. 确保聊天输入框可见")
                    print("4. 然后重新运行自动化测试")
                elif status == "chat_ready":
                    print("\n✅ 准备就绪:")
                    print("1. 豆包已启动并在前台")
                    print("2. 聊天界面可用")
                    print("3. 可以运行自动化测试")
                else:
                    print("\n⚠️ 状态未知，建议手动检查:")
                    print("1. 查看豆包窗口内容")
                    print("2. 确认是否可以发送消息")
                    print("3. 然后继续自动化测试")

                return True

    print("\n❌ 无法启动豆包应用")
    print("\n📝 手动启动指南:")
    print("1. 打开Finder，前往应用程序文件夹")
    print("2. 查找'豆包'或'Doubao'应用")
    print("3. 双击启动应用")
    print("4. 等待完全启动")
    print("5. 登录账户（如果需要）")
    print("6. 进入AI聊天界面")

    return False


if __name__ == "__main__":
    success = main()

    if success:
        print("\n✅ 豆包启动验证完成")
        sys.exit(0)
    else:
        print("\n❌ 豆包启动失败，需要手动干预")
        sys.exit(1)
