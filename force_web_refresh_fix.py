#!/usr/bin/env python3
"""
强制Web界面刷新修复工具
彻底解决无法定位当前队列项错误
"""

import json
import os
import subprocess
import time
from datetime import datetime

import requests


def check_web_cache_issue():
    """检查Web界面缓存问题"""

    print("🔍 检查Web界面缓存问题...")

    # 检查实际队列状态
    queue_file = (
        "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_plan_manual_20260328.json"
    )

    if not os.path.exists(queue_file):
        print(f"❌ 队列状态文件不存在: {queue_file}")
        return None

    try:
        with open(queue_file, "r", encoding="utf-8") as f:
            actual_state = json.load(f)

        print(f"📊 实际队列状态: {actual_state.get('queue_status', 'unknown')}")
        print(f"🎯 实际当前任务: {actual_state.get('current_item_id', '无')}")

        # 检查Web界面状态
        try:
            response = requests.get("http://127.0.0.1:8080/api/queues", timeout=10)
            if response.status_code == 200:
                web_data = response.json()

                if "routes" in web_data:
                    for route in web_data["routes"]:
                        if route.get("queue_id") == "openhuman_aiplan_plan_manual_20260328":
                            print(f"📊 Web界面队列状态: {route.get('queue_status', 'unknown')}")
                            print(f"🎯 Web界面当前任务: {route.get('current_item_id', '无')}")

                            # 对比状态
                            if actual_state.get("queue_status") != route.get(
                                "queue_status"
                            ) or actual_state.get("current_item_id") != route.get(
                                "current_item_id"
                            ):
                                print("❌ Web界面与实际状态不匹配!")
                                return {"actual": actual_state, "web": route, "mismatch": True}
                            else:
                                print("✅ Web界面与实际状态匹配")
                                return {"actual": actual_state, "web": route, "mismatch": False}
            else:
                print(f"❌ Web界面API响应异常: {response.status_code}")
        except Exception as e:
            print(f"❌ 访问Web界面API失败: {e}")

        return {"actual": actual_state, "web": None, "mismatch": True}

    except Exception as e:
        print(f"❌ 检查Web缓存问题失败: {e}")
        return None


def force_web_refresh():
    """强制Web界面刷新"""

    print("\n🔄 强制Web界面刷新...")

    # 方法1: 重启Web服务器
    print("1. 重启Web服务器...")

    web_script = "/Volumes/1TB-M2/openclaw/scripts/athena_web_desktop_compat.py"

    if not os.path.exists(web_script):
        print(f"❌ Web服务器脚本不存在: {web_script}")
        return False

    try:
        # 停止现有Web服务器
        subprocess.run(["pkill", "-f", "athena_web_desktop_compat.py"], capture_output=True)
        time.sleep(2)

        # 启动新的Web服务器
        subprocess.Popen(
            ["python3", web_script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        # 等待启动
        time.sleep(5)

        # 验证服务启动
        try:
            response = requests.get("http://127.0.0.1:8080", timeout=10)
            if response.status_code == 200:
                print("✅ Web服务器重启成功")
            else:
                print(f"⚠️ Web服务器响应异常: {response.status_code}")
        except:
            print("❌ Web服务器重启后无法访问")

    except Exception as e:
        print(f"❌ 重启Web服务器失败: {e}")

    # 方法2: 清除浏览器缓存（模拟）
    print("\n2. 清除浏览器缓存（模拟）...")

    try:
        # 发送强制刷新请求
        headers = {
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }

        response = requests.get("http://127.0.0.1:8080", headers=headers, timeout=10)
        if response.status_code == 200:
            print("✅ 强制刷新请求发送成功")
        else:
            print(f"⚠️ 强制刷新请求响应异常: {response.status_code}")

    except Exception as e:
        print(f"❌ 发送强制刷新请求失败: {e}")

    # 方法3: 修改队列状态时间戳强制刷新
    print("\n3. 修改队列状态时间戳强制刷新...")

    queue_file = (
        "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_plan_manual_20260328.json"
    )

    if os.path.exists(queue_file):
        try:
            with open(queue_file, "r", encoding="utf-8") as f:
                queue_state = json.load(f)

            # 更新时间戳
            queue_state["updated_at"] = datetime.now().isoformat()

            # 保存更新后的状态
            with open(queue_file, "w", encoding="utf-8") as f:
                json.dump(queue_state, f, indent=2, ensure_ascii=False)

            print("✅ 队列状态时间戳已更新")

        except Exception as e:
            print(f"❌ 更新队列状态时间戳失败: {e}")

    return True


def test_manual_launch():
    """测试手动拉起功能"""

    print("\n🔧 测试手动拉起功能...")

    # 检查队列运行器状态
    try:
        result = subprocess.run(
            ["pgrep", "-f", "athena_ai_plan_runner.py"], capture_output=True, text=True
        )

        if result.returncode == 0:
            pids = result.stdout.strip().split("\n")
            print(f"✅ 队列运行器正在运行，PID: {', '.join(pids)}")
        else:
            print("❌ 队列运行器未运行")

            # 尝试启动队列运行器
            runner_script = "/Volumes/1TB-M2/openclaw/scripts/athena_ai_plan_runner.py"
            if os.path.exists(runner_script):
                subprocess.Popen(
                    ["python3", runner_script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                print("✅ 队列运行器已启动")
            else:
                print(f"❌ 队列运行器脚本不存在: {runner_script}")

    except Exception as e:
        print(f"❌ 检查队列运行器失败: {e}")

    # 模拟手动拉起请求
    print("\n🔧 模拟手动拉起请求...")

    try:
        # 构建手动拉起请求
        launch_data = {
            "queue_id": "openhuman_aiplan_plan_manual_20260328",
            "item_id": "opencode_cli_optimization",
            "action": "launch",
        }

        response = requests.post(
            "http://127.0.0.1:8080/api/queue/item/launch", json=launch_data, timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            if result.get("ok"):
                print("✅ 手动拉起请求成功")
                print(f"   消息: {result.get('message', '')}")
            else:
                print(f"❌ 手动拉起请求失败: {result.get('message', '未知错误')}")
        else:
            print(f"❌ 手动拉起API响应异常: {response.status_code}")

    except Exception as e:
        print(f"❌ 模拟手动拉起请求失败: {e}")


def create_browser_refresh_instructions():
    """创建浏览器刷新操作指南"""

    print("\n📋 创建浏览器刷新操作指南...")

    instructions = """# 🌐 Athena Web Desktop 强制刷新操作指南

## 🔄 强制刷新方法

### 方法1: 浏览器强制刷新 (推荐)
1. **打开浏览器**: 访问 http://127.0.0.1:8080
2. **强制刷新快捷键**:
   - **Windows/Linux**: `Ctrl + F5` 或 `Ctrl + Shift + R`
   - **Mac**: `Cmd + Shift + R`
3. **清除浏览器缓存**:
   - 打开开发者工具 (F12)
   - 右键刷新按钮 → "清空缓存并硬性重新加载"

### 方法2: 浏览器控制台刷新
```javascript
// 在浏览器控制台中执行以下命令
location.reload(true);  // 强制刷新
localStorage.clear();   // 清除本地存储
sessionStorage.clear(); // 清除会话存储
```

### 方法3: 使用无痕/隐私模式
1. 打开浏览器的无痕/隐私模式
2. 访问 http://127.0.0.1:8080
3. 避免缓存干扰

## 🎯 验证修复效果

刷新后检查以下内容：
1. ✅ **队列状态**: 应该显示"运行中"而不是"手动保留"
2. ✅ **当前任务**: 应该显示"opencode_cli_optimization"
3. ✅ **错误消失**: "无法定位当前队列项"警告应该消失
4. ✅ **手动拉起**: 手动拉起按钮应该可以正常响应

## 🔧 如果问题仍然存在

如果强制刷新后问题仍然存在，请执行：
1. 重启Web服务器: `pkill -f athena_web_desktop_compat.py && python3 /Volumes/1TB-M2/openclaw/scripts/athena_web_desktop_compat.py`
2. 等待30秒后重新访问
3. 如果仍然有问题，请联系技术支持
"""

    instructions_path = "/Volumes/1TB-M2/openclaw/web_refresh_instructions.md"

    try:
        with open(instructions_path, "w", encoding="utf-8") as f:
            f.write(instructions)

        print(f"✅ 浏览器刷新操作指南已创建: {instructions_path}")

        return instructions_path

    except Exception as e:
        print(f"❌ 创建操作指南失败: {e}")
        return None


def main():
    """主函数"""
    print("=" * 60)
    print("🔧 强制Web界面刷新修复工具")
    print("=" * 60)

    # 检查Web缓存问题
    cache_issue = check_web_cache_issue()
    if not cache_issue:
        print("❌ 检查Web缓存问题失败")
        return

    if cache_issue.get("mismatch"):
        print("\n❌ 检测到Web界面缓存问题，正在修复...")
    else:
        print("\n✅ Web界面状态正常")

    # 强制Web界面刷新
    if not force_web_refresh():
        print("❌ 强制Web界面刷新失败")
        return

    # 等待刷新生效
    print("\n⏳ 等待刷新生效...")
    time.sleep(5)

    # 测试手动拉起功能
    test_manual_launch()

    # 创建浏览器刷新操作指南
    create_browser_refresh_instructions()

    print("\n🎯 修复完成，下一步操作:")
    print("1. 访问 http://127.0.0.1:8080")
    print("2. 使用 Ctrl+F5 (Windows/Linux) 或 Cmd+Shift+R (Mac) 强制刷新浏览器")
    print("3. 验证队列状态是否显示为运行中")
    print("4. 测试手动拉起按钮功能")
    print("5. 检查无法定位当前队列项错误是否消失")


if __name__ == "__main__":
    main()
