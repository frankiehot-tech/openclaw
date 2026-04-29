"""
Screen Capture - 屏幕截图模块

使用 ADB exec-out screencap 获取设备屏幕截图
包含页面状态检测功能
"""

import hashlib
import logging
import os
import subprocess
from datetime import datetime

# 配置日志
logger = logging.getLogger(__name__)

# 截图保存目录
SCREENSHOT_DIR = "os.path.join(os.path.dirname(os.path.abspath(__file__)), '../logs/screenshots')"


def ensure_screenshot_dir() -> str:
    """确保截图目录存在"""
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    return SCREENSHOT_DIR


def capture_screen(device_id: str | None = None, save: bool = True) -> str | None:
    """
    获取设备屏幕截图

    Args:
        device_id: 设备序列号
        save: 是否保存到文件

    Returns:
        图片路径或 None
    """
    # 确保目录存在
    screenshot_dir = ensure_screenshot_dir()

    # 构建命令
    device_arg = f"-s {device_id}" if device_id else ""

    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"screenshot_{timestamp}.png"
    filepath = os.path.join(screenshot_dir, filename)

    # 使用 adb shell screencap + pull 方式（兼容折叠屏）
    device_arg = f"-s {device_id}" if device_id else ""

    # 先截图到设备临时目录
    temp_path = "/sdcard/screen_temp.png"
    cmd1 = f"adb {device_arg} shell screencap -p {temp_path}"
    cmd2 = f"adb {device_arg} pull {temp_path} {filepath}"
    cmd3 = f"adb {device_arg} shell rm {temp_path}"

    logger.info(f"执行截图: {cmd1} && {cmd2}")

    try:
        # 执行截图命令
        result1 = subprocess.run(cmd1, shell=True, capture_output=True, timeout=30)
        if result1.returncode != 0:
            logger.error(
                f"截图命令失败: {result1.stderr.decode() if result1.stderr else 'Unknown'}"
            )
            return None

        # 拉取文件
        result2 = subprocess.run(cmd2, shell=True, capture_output=True, timeout=30)
        if result2.returncode != 0:
            logger.error(
                f"拉取截图失败: {result2.stderr.decode() if result2.stderr else 'Unknown'}"
            )
            return None

        # 清理设备端临时文件
        subprocess.run(cmd3, shell=True, capture_output=True, timeout=10)

        # 检查文件是否有效
        if os.path.getsize(filepath) > 0:
            logger.info(f"截图成功: {filepath}, 大小: {os.path.getsize(filepath)} bytes")
            return filepath
        else:
            logger.error("截图文件为空")
            os.remove(filepath)
            return None

    except subprocess.TimeoutExpired:
        logger.error("截图超时")
        return None
    except Exception as e:
        logger.error(f"截图异常: {str(e)}")
        return None


def capture_screen_to_bytes(device_id: str | None = None) -> bytes | None:
    """
    获取设备屏幕截图（返回字节数据）

    Args:
        device_id: 设备序列号

    Returns:
        PNG 字节数据或 None
    """
    device_arg = f"-s {device_id}" if device_id else ""
    command = f"adb {device_arg} exec-out screencap -p"

    try:
        result = subprocess.run(command, shell=True, capture_output=True, timeout=30)

        if result.returncode == 0 and len(result.stdout) > 0:
            logger.info(f"截图成功，大小: {len(result.stdout)} bytes")
            return result.stdout
        else:
            logger.error("截图失败")
            return None

    except Exception as e:
        logger.error(f"截图异常: {str(e)}")
        return None


def get_screen_hash(image_path: str) -> str | None:
    """
    获取图片的哈希值（用于检测页面变化）

    Args:
        image_path: 图片路径

    Returns:
        MD5 哈希值或 None
    """
    try:
        with open(image_path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception as e:
        logger.error(f"计算图片哈希失败: {str(e)}")
        return None


def is_screen_changed(
    prev_image_path: str | None, current_image_path: str | None, threshold: float = 0.95
) -> bool:
    """
    检测屏幕是否发生变化

    Args:
        prev_image_path: 上一张图片路径
        current_image_path: 当前图片路径
        threshold: 相似度阈值（0-1），低于此值认为发生变化

    Returns:
        是否发生变化
    """
    if not prev_image_path or not current_image_path:
        return True

    prev_hash = get_screen_hash(prev_image_path)
    current_hash = get_screen_hash(current_image_path)

    if not prev_hash or not current_hash:
        return True

    # 如果哈希相同，认为没有变化
    if prev_hash == current_hash:
        logger.info("屏幕未发生变化（哈希相同）")
        return False

    logger.info(f"屏幕发生变化: {prev_hash[:8]}... -> {current_hash[:8]}...")
    return True


def get_latest_screenshot() -> str | None:
    """
    获取最新的截图文件路径

    Returns:
        最新截图路径或 None
    """
    screenshot_dir = ensure_screenshot_dir()

    try:
        files = [
            os.path.join(screenshot_dir, f)
            for f in os.listdir(screenshot_dir)
            if f.endswith(".png")
        ]

        if files:
            latest = max(files, key=os.path.getmtime)
            return latest

    except Exception as e:
        logger.error(f"获取最新截图失败: {str(e)}")

    return None


def cleanup_old_screenshots(max_count: int = 50) -> int:
    """
    清理旧截图，保留最新的 N 张

    Args:
        max_count: 保留的最大截图数量

    Returns:
        删除的文件数量
    """
    screenshot_dir = ensure_screenshot_dir()

    try:
        files = [
            (os.path.join(screenshot_dir, f), os.path.getmtime(os.path.join(screenshot_dir, f)))
            for f in os.listdir(screenshot_dir)
            if f.endswith(".png")
        ]

        # 按时间排序
        files.sort(key=lambda x: x[1], reverse=True)

        # 删除多余的
        deleted = 0
        for filepath, _ in files[max_count:]:
            try:
                os.remove(filepath)
                deleted += 1
            except Exception as e:
                logger.error(f"删除截图失败: {filepath}, {str(e)}")

        if deleted > 0:
            logger.info(f"清理了 {deleted} 张旧截图")

        return deleted

    except Exception as e:
        logger.error(f"清理截图失败: {str(e)}")
        return 0


if __name__ == "__main__":
    # 测试代码
    print("=== Screen Capture 测试 ===")

    # 截图
    filepath = capture_screen()
    print(f"截图路径: {filepath}")

    # 获取最新截图
    latest = get_latest_screenshot()
    print(f"最新截图: {latest}")

    # 测试哈希
    if latest:
        hash_val = get_screen_hash(latest)
        print(f"图片哈希: {hash_val}")
