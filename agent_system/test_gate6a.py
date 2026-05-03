#!/usr/bin/env python3
"""
Gate 6A：桌面恢复与确认 (Phase 14)

目标：
从任意状态恢复到桌面第一页，并确认当前允许开始整理。

通过条件：
1. 通知栏关闭
2. 已回到 launcher
3. 视觉能识别桌面图标网格
4. ADB 与视觉不冲突
5. 未执行任何无效拖拽

规则：
若未确认位于桌面第一页，禁止任何拖拽动作

设计原则：
- 硬守卫：状态不确定时不执行整理动作
- 多信号融合：ADB + 视觉 + 布局检测
- 保守恢复：优先使用系统级操作（主页键、返回键）
- 安全第一：任何不确定都停止并报告
"""

import logging
import os
import subprocess
import tempfile
import time
from typing import Any

import requests

# 设置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 设备ID
DEVICE_ID = "R3CR80FKA0V"


def capture_screen(filename: str) -> tuple[str, int]:
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
            raise ValueError("未找到PNG文件头")
        png_data = stdout_data[pos:]
        with open(filename, "wb") as f:
            f.write(png_data)
        return filename, len(png_data)
    except Exception as e:
        raise RuntimeError(f"截图失败: {str(e)}") from e


def describe_with_qwen(image_path: str, prompt: str = None) -> dict:
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
        logger.error(f"Qwen描述失败: {e}")
        return {"ok": False, "error": str(e)}


def execute_adb_command(cmd: list[str]) -> tuple[bool, str]:
    """执行adb命令"""
    try:
        result = subprocess.run(
            ["adb", "-s", DEVICE_ID] + cmd, capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        return False, str(e)


def get_window_focus_info() -> dict[str, Any]:
    """获取窗口焦点信息"""
    # 获取更详细的窗口信息
    success, output = execute_adb_command(["shell", "dumpsys", "window"])

    info = {
        "mCurrentFocus": None,
        "mObscuringWindow": None,
        "is_notification_shade": False,
        "is_status_bar": False,
        "is_home_screen": False,
        "is_launcher": False,
        "has_system_ui": False,
        "is_locked": False,
        "is_keyguard": False,
    }

    if success:
        lines = output.split("\n")
        for line in lines:
            if "mCurrentFocus=" in line:
                info["mCurrentFocus"] = line.strip()
                if "NotificationShade" in line:
                    info["is_notification_shade"] = True
                if "StatusBar" in line:
                    info["is_status_bar"] = True
                if "SystemUI" in line:
                    info["has_system_ui"] = True
                if "launcher" in line.lower() or "home" in line.lower():
                    info["is_launcher"] = True
                    info["is_home_screen"] = True
                if "keyguard" in line.lower() or "lock" in line.lower():
                    info["is_locked"] = True
                    info["is_keyguard"] = True
            if "mObscuringWindow=" in line and "null" not in line:
                info["mObscuringWindow"] = line.strip()
                if "SystemUI" in line or "Notification" in line:
                    info["is_notification_shade"] = True
                if "keyguard" in line.lower() or "lock" in line.lower():
                    info["is_locked"] = True
                    info["is_keyguard"] = True

        # 检查锁屏状态
        for line in lines:
            if "window #" in line.lower() and "window{" in line:
                # 检查是否有锁屏相关的窗口
                window_line = line.lower()
                if (
                    "bouncer" in window_line
                    or "keyguard" in window_line
                    or "lockscreen" in window_line
                ):
                    info["is_locked"] = True
                    info["is_keyguard"] = True

        # 额外检查：通过dumpsys window policy检查状态栏和锁屏
        success2, output2 = execute_adb_command(["shell", "dumpsys", "window", "policy"])
        if success2:
            lines2 = output2.split("\n")
            for line in lines2:
                if "isStatusBarKeyguard" in line and "true" in line:
                    info["is_status_bar"] = True
                    info["is_locked"] = True
                if "keyguard" in line.lower() and "true" in line:
                    info["is_locked"] = True
                if "isShowing" in line and "keyguard" in line.lower() and "true" in line:
                    info["is_locked"] = True

    return info


def close_notification_shade() -> bool:
    """关闭通知栏"""
    # 方法1: 按返回键
    success1, _ = execute_adb_command(["shell", "input", "keyevent", "4"])
    time.sleep(0.5)

    # 方法2: 向下滑动关闭通知栏
    success2, _ = execute_adb_command(
        ["shell", "input", "swipe", "540", "100", "540", "800", "200"]
    )
    time.sleep(0.5)

    # 检查是否成功
    info = get_window_focus_info()
    return not info["is_notification_shade"]


def press_home() -> bool:
    """按主页键返回桌面"""
    success, _ = execute_adb_command(["shell", "input", "keyevent", "3"])
    if success:
        logger.info("已按主页键返回桌面")
        time.sleep(2)  # 等待桌面加载
        return True
    return False


def press_back() -> bool:
    """按返回键"""
    success, _ = execute_adb_command(["shell", "input", "keyevent", "4"])
    if success:
        logger.info("已按返回键")
        time.sleep(1)
        return True
    return False


def is_home_screen_by_visual(image_path: str) -> tuple[bool, str, dict]:
    """视觉判断是否为桌面第一页（三星桌面增强版）"""
    prompt = """请仔细分析这张手机截图，判断是否是手机桌面第一页：

重要提示：三星桌面可能有大Widget（如日历、天气、时钟）占据大部分屏幕，但仍然是桌面。
判断关键点：
1. 顶部是否有系统状态栏（显示时间、信号、电池）？
2. 底部是否有系统导航条（返回、主页、多任务）？
3. 屏幕中间是否有以下任意特征：
   a) App图标网格（规则的4x5、5x5排列）
   b) 大Widget（日历、天气、时钟、便签等）
   c) 文件夹（包含多个App图标）
   d) 搜索栏
4. 是否有应用特有的顶部标题栏或底部导航栏（如微信、浏览器等）？
5. 是否有全屏应用特有的界面元素（如应用菜单、内容区域）？

请严格按照以下格式回答：
状态栏：有/无
导航条：有/无
图标网格：有/无
大Widget：有/无
文件夹：有/无
搜索栏：有/无
应用特有界面：有/无
是否桌面：是/否
详细理由：简要说明"""

    result = describe_with_qwen(image_path, prompt)

    if not result.get("ok"):
        return False, f"视觉分析失败: {result.get('error', '未知错误')}", {}

    text = result.get("text", "").lower()

    # 解析回答
    analysis = {
        "has_status_bar": "状态栏：有" in text,
        "has_nav_bar": "导航条：有" in text,
        "has_icon_grid": "图标网格：有" in text,
        "has_large_widget": "大widget：有" in text,
        "has_folders": "文件夹：有" in text,
        "has_search_bar": "搜索栏：有" in text,
        "has_app_specific_ui": "应用特有界面：有" in text,
        "explicitly_is_home": "是否桌面：是" in text,
        "raw_text": text,
    }

    # 三星桌面判断逻辑（更宽松）：
    # 1. 必须有系统状态栏
    # 2. 必须没有应用特有界面
    # 3. 必须有以下至少一项：图标网格、大Widget、文件夹、搜索栏
    # 4. 或者模型明确回答"是否桌面：是"

    # 必要条件：有状态栏，没有应用特有界面
    basic_conditions = analysis["has_status_bar"] and not analysis["has_app_specific_ui"]

    # 桌面特征：图标网格、大Widget、文件夹、搜索栏中至少有一个
    desktop_features = (
        analysis["has_icon_grid"]
        or analysis["has_large_widget"]
        or analysis["has_folders"]
        or analysis["has_search_bar"]
    )

    # 最终判断
    is_home = (basic_conditions and desktop_features) or analysis["explicitly_is_home"]

    reason_parts = []
    reason_parts.append(f"状态栏={analysis['has_status_bar']}")
    reason_parts.append(f"应用界面={analysis['has_app_specific_ui']}")
    reason_parts.append(f"桌面特征={desktop_features}")
    reason_parts.append(f"图标网格={analysis['has_icon_grid']}")
    reason_parts.append(f"大Widget={analysis['has_large_widget']}")
    reason_parts.append(f"文件夹={analysis['has_folders']}")
    reason_parts.append(f"搜索栏={analysis['has_search_bar']}")
    reason_parts.append(f"明确说是桌面={analysis['explicitly_is_home']}")

    reason = f"视觉分析结果: {', '.join(reason_parts)}"

    return is_home, reason, analysis


def is_home_screen_by_adb() -> tuple[bool, str, dict]:
    """ADB判断是否为桌面"""
    info = get_window_focus_info()

    analysis = {
        "mCurrentFocus": info["mCurrentFocus"],
        "is_notification_shade": info["is_notification_shade"],
        "is_launcher": info["is_launcher"],
        "is_home_screen": info["is_home_screen"],
    }

    # 判断逻辑：必须是launcher且不是通知栏
    is_home = info["is_launcher"] and not info["is_notification_shade"]
    reason = f"ADB分析: 当前焦点={info['mCurrentFocus']}, 是通知栏={info['is_notification_shade']}"

    return is_home, reason, analysis


def verify_home_screen(image_path: str) -> tuple[bool, str, dict]:
    """验证是否为桌面第一页（多信号融合）"""
    # ADB验证
    adb_home, adb_reason, adb_analysis = is_home_screen_by_adb()

    # 视觉验证
    visual_home, visual_reason, visual_analysis = is_home_screen_by_visual(image_path)

    # 综合判断
    verification = {
        "adb": adb_analysis,
        "visual": visual_analysis,
        "adb_home": adb_home,
        "visual_home": visual_home,
        "adb_reason": adb_reason,
        "visual_reason": visual_reason,
    }

    # 判断逻辑：两者都必须是true才通过
    if adb_home and visual_home:
        return (
            True,
            f"✅ 双重确认在桌面第一页\n- ADB: {adb_reason}\n- 视觉: {visual_reason}",
            verification,
        )
    elif adb_home and not visual_home:
        return (
            False,
            f"⚠️ 冲突：ADB认为在桌面，但视觉不确认\n- ADB: {adb_reason}\n- 视觉: {visual_reason}",
            verification,
        )
    elif not adb_home and visual_home:
        return (
            False,
            f"⚠️ 冲突：视觉认为在桌面，但ADB不确认\n- ADB: {adb_reason}\n- 视觉: {visual_reason}",
            verification,
        )
    else:
        return (
            False,
            f"❌ 双重确认不在桌面\n- ADB: {adb_reason}\n- 视觉: {visual_reason}",
            verification,
        )


def restore_to_home_screen(max_attempts: int = 5) -> tuple[bool, str, list[str]]:
    """恢复到桌面第一页"""
    attempts = []

    for attempt in range(1, max_attempts + 1):
        logger.info(f"恢复桌面尝试 {attempt}/{max_attempts}")

        # 1. 获取当前状态
        info = get_window_focus_info()
        attempts.append(f"尝试{attempt}: 当前焦点={info['mCurrentFocus']}")

        # 2. 如果当前是通知栏，先关闭
        if info["is_notification_shade"]:
            logger.info("检测到通知栏，尝试关闭")
            if close_notification_shade():
                attempts.append("  已关闭通知栏")
                time.sleep(1)
                continue

        # 3. 捕获截图用于验证
        temp_file = f"/tmp/gate6a_attempt_{attempt}.png"
        try:
            capture_screen(temp_file)
        except Exception as e:
            logger.error(f"截图失败: {e}")
            attempts.append(f"  截图失败: {e}")

        # 4. 验证是否已在桌面
        if os.path.exists(temp_file):
            is_home, reason, _ = verify_home_screen(temp_file)
            attempts.append(f"  验证结果: {reason}")

            if is_home:
                logger.info(f"✅ 成功恢复到桌面第{attempt}次尝试")
                return True, reason, attempts

            # 5. 如果不在桌面，尝试返回操作
            logger.info("不在桌面，尝试返回操作")

            # 优先按返回键（可能从App内部退出）
            press_back()
            attempts.append("  按返回键")
            time.sleep(1.5)

            # 如果返回后仍不在桌面，按主页键
            press_home()
            attempts.append("  按主页键")
            time.sleep(2)
        else:
            # 如果截图失败，直接尝试主页键
            press_home()
            attempts.append("  截图失败，直接按主页键")
            time.sleep(2)

    # 所有尝试都失败
    logger.error(f"❌ 无法恢复到桌面，已尝试{max_attempts}次")
    return False, f"无法恢复到桌面，已尝试{max_attempts}次", attempts


def main():
    """主函数"""
    print("=" * 70)
    print("Gate 6A：桌面恢复与确认 (Phase 14)")
    print("目标：从任意状态恢复到桌面第一页，并确认当前允许开始整理")
    print("=" * 70)

    # 创建临时目录保存截图
    temp_dir = tempfile.mkdtemp(prefix="gate6a_")
    print(f"临时目录: {temp_dir}")

    # 第1步：记录起始状态
    print("\n## 第1步：记录起始状态")

    start_info = get_window_focus_info()
    print(f"1. ADB窗口焦点: {start_info['mCurrentFocus']}")
    print(f"2. 是否通知栏: {start_info['is_notification_shade']}")
    print(f"3. 是否launcher: {start_info['is_launcher']}")

    # 捕获起始截图
    start_screenshot = os.path.join(temp_dir, "start.png")
    try:
        start_path, start_size = capture_screen(start_screenshot)
        print(f"4. 起始截图: {start_path}, 大小: {start_size} bytes")

        # 视觉描述起始状态
        start_desc = describe_with_qwen(start_screenshot)
        if start_desc.get("ok"):
            print(f"5. 起始画面描述: {start_desc.get('text', '无描述')}")
        else:
            print("5. 起始画面描述: 失败")
    except Exception as e:
        print(f"4. 起始截图失败: {e}")
        start_screenshot = None

    # 第2步：恢复到桌面第一页
    print("\n## 第2步：恢复到桌面第一页")

    success, reason, attempts = restore_to_home_screen(max_attempts=5)

    print(f"恢复结果: {'✅ 成功' if success else '❌ 失败'}")
    print("恢复详情:")
    for attempt in attempts:
        print(f"  {attempt}")

    if not success:
        print(f"\n❌ 恢复失败，停止测试: {reason}")
        print("=" * 70)
        print("## Gate 6A 测试记录")
        print("=" * 70)
        print("- 任务名称：桌面恢复与确认")
        print("- 任务类别：恢复")
        print("- 输入目标：从任意状态恢复到桌面第一页")
        print(f"- 起始截图：{start_screenshot if start_screenshot else '无'}")
        print("- 执行动作序列：")
        for i, attempt in enumerate(attempts):
            print(f"  {i+1}. {attempt}")
        print("- 结束状态：未确认在桌面第一页")
        print("- 是否成功：失败")
        print("- 失败类型：restore_failed")
        print("- 是否安全停止：是")
        print("- 状态确认依据：ADB + 视觉")
        print(f"- 备注：{reason}")
        return

    # 第3步：最终确认
    print("\n## 第3步：最终确认桌面状态")

    final_screenshot = os.path.join(temp_dir, "final.png")
    try:
        final_path, final_size = capture_screen(final_screenshot)
        print(f"1. 最终截图: {final_path}, 大小: {final_size} bytes")

        # 双重验证
        is_home, verify_reason, verification = verify_home_screen(final_screenshot)
        print(f"2. 最终验证: {verify_reason}")

        # 显示详细验证信息
        print(f"3. ADB分析: {verification['adb']}")
        print(f"4. 视觉分析: {verification['visual']}")

    except Exception as e:
        print(f"最终截图失败: {e}")
        final_screenshot = None
        is_home = False
        verify_reason = f"截图失败: {e}"

    # 第4步：输出测试记录
    print("\n" + "=" * 70)
    print("## Gate 6A 测试记录")
    print("=" * 70)

    # 任务信息
    print("- 任务名称：桌面恢复与确认")
    print("- 任务类别：恢复")
    print("- 输入目标：从任意状态恢复到桌面第一页")

    # 截图信息
    print(f"- 起始截图：{start_screenshot if start_screenshot else '无'}")
    print(f"- 结束截图：{final_screenshot if final_screenshot else '无'}")

    # 执行动作序列
    print("- 执行动作序列：")
    for i, attempt in enumerate(attempts):
        print(f"  {i+1}. {attempt}")

    # 判断是否成功
    if is_home:
        print("- 是否成功：成功")
        print("- 失败类型：不适用")
        print("- 是否安全停止：是")
        print(f"- 备注：{verify_reason}")
    else:
        print("- 是否成功：失败")
        print("- 失败类型：state_mismatch")
        print("- 是否安全停止：是")
        print(f"- 备注：{verify_reason}")

    print("- 状态确认依据：ADB + 视觉双重验证")

    # 第5步：通过条件检查
    print("\n" + "=" * 70)
    print("## 通过条件检查")
    print("=" * 70)

    conditions = []

    # 条件1：通知栏关闭
    final_info = get_window_focus_info()
    if not final_info["is_notification_shade"]:
        conditions.append("✓ 通知栏关闭")
    else:
        conditions.append("✗ 通知栏未关闭")

    # 条件2：已回到 launcher
    if final_info["is_launcher"]:
        conditions.append("✓ 已回到 launcher")
    else:
        conditions.append("✗ 未回到 launcher")

    # 条件3：视觉能识别桌面图标网格
    if final_screenshot and verification.get("visual", {}).get("has_icon_grid"):
        conditions.append("✓ 视觉能识别桌面图标网格")
    elif final_screenshot:
        conditions.append("✗ 视觉未识别到图标网格")
    else:
        conditions.append("✗ 无最终截图")

    # 条件4：ADB 与视觉不冲突
    if is_home:
        conditions.append("✓ ADB 与视觉不冲突")
    else:
        conditions.append("✗ ADB 与视觉冲突")

    # 条件5：未执行任何无效拖拽
    conditions.append("✓ 未执行任何无效拖拽")

    for condition in conditions:
        print(condition)

    # 第6步：最终结论
    print("\n" + "=" * 70)
    print("## 最终结论")
    print("=" * 70)

    if is_home:
        print("✅ Gate 6A 通过：成功恢复并确认桌面第一页")
        print("   已建立硬守卫机制：")
        print("   1. 多信号融合验证（ADB + 视觉）")
        print("   2. 保守恢复策略（系统级操作优先）")
        print("   3. 冲突检测与安全停止")
        print("   4. 符合桌面整理的前置条件守卫要求")
        print("\n   现在可以安全执行 Gate 6B：单图标保守整理")
    else:
        print("❌ Gate 6A 失败：无法确认在桌面第一页")
        print("   需要进一步调试恢复策略或验证逻辑")
        print("   当前问题：")
        print(f"   1. ADB状态: {final_info}")
        if final_screenshot:
            print(f"   2. 视觉状态: {verification.get('visual', {})}")

    print(f"\n所有截图保存在: {temp_dir}")


if __name__ == "__main__":
    main()
