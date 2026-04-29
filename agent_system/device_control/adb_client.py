"""
ADB Client - ADB 命令封装层

提供对 Android 设备的 ADB 操作封装：
- 设备列表查询
- 点击、滑动、输入
- 返回、主页
"""

import logging
import subprocess
import time
from typing import List, Optional, Tuple

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 日志文件
DEVICE_LOG = "os.path.join(os.path.dirname(os.path.abspath(__file__)), '../logs/device.log')"

# 配置日志文件
file_handler = logging.FileHandler(DEVICE_LOG)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(file_handler)


class ADBClient:
    """ADB 客户端封装类"""

    def __init__(self, device_id: Optional[str] = None):
        """
        初始化 ADB 客户端

        Args:
            device_id: 设备序列号，如果为 None 则使用第一个设备
        """
        self.device_id = device_id
        self._device_id_arg = f"-s {device_id}" if device_id else ""

    def _run_command(self, command: str, timeout: int = 30) -> Tuple[bool, str]:
        """
        执行 ADB 命令

        Args:
            command: ADB 命令
            timeout: 超时时间（秒）

        Returns:
            (成功标志, 输出内容)
        """
        full_command = f"adb {self._device_id_arg} {command}"
        logger.info(f"执行命令: {full_command}")

        try:
            result = subprocess.run(
                full_command, shell=True, capture_output=True, text=True, timeout=timeout
            )

            if result.returncode == 0:
                logger.info(f"命令成功: {result.stdout}")
                return True, result.stdout
            else:
                logger.error(f"命令失败: {result.stderr}")
                return False, result.stderr

        except subprocess.TimeoutExpired:
            logger.error(f"命令超时: {command}")
            return False, "Command timeout"
        except Exception as e:
            logger.error(f"命令异常: {str(e)}")
            return False, str(e)

    def list_devices(self) -> List[dict]:
        """
        获取设备列表

        Returns:
            设备信息列表 [{"id": "xxx", "status": "device"}]
        """
        success, output = self._run_command("devices -l")

        if not success:
            logger.error("获取设备列表失败")
            return []

        devices = []
        lines = output.strip().split("\n")[1:]  # 跳过标题行

        for line in lines:
            if line.strip():
                parts = line.split()
                if len(parts) >= 2:
                    device_id = parts[0]
                    status = parts[1]
                    devices.append({"id": device_id, "status": status})

        logger.info(f"发现 {len(devices)} 个设备")
        return devices

    def get_screen_size(self) -> Optional[Tuple[int, int]]:
        """
        获取设备屏幕分辨率

        Returns:
            (宽度, 高度) 或 None
        """
        success, output = self._run_command("shell wm size")

        if not success:
            return None

        # 解析输出: Physical size: 1080x2640
        try:
            size_str = output.strip().split(":")[-1].strip()
            width, height = map(int, size_str.split("x"))
            logger.info(f"屏幕分辨率: {width}x{height}")
            return (width, height)
        except Exception as e:
            logger.error(f"解析屏幕尺寸失败: {e}")
            return None

    def tap(self, x: int, y: int) -> bool:
        """
        点击指定坐标

        Args:
            x: X 坐标
            y: Y 坐标

        Returns:
            是否成功
        """
        success, output = self._run_command(f"shell input tap {x} {y}")

        if success:
            logger.info(f"点击坐标: ({x}, {y})")
        else:
            logger.error(f"点击失败: {output}")

        return success

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> bool:
        """
        滑动操作

        Args:
            x1: 起始 X 坐标
            y1: 起始 Y 坐标
            x2: 结束 X 坐标
            y2: 结束 Y 坐标
            duration: 持续时间（毫秒）

        Returns:
            是否成功
        """
        success, output = self._run_command(f"shell input swipe {x1} {y1} {x2} {y2} {duration}")

        if success:
            logger.info(f"滑动: ({x1}, {y1}) -> ({x2}, {y2}), 耗时: {duration}ms")
        else:
            logger.error(f"滑动失败: {output}")

        return success

    def input_text(self, text: str) -> bool:
        """
        输入文本

        Args:
            text: 要输入的文本

        Returns:
            是否成功
        """
        # 转义特殊字符
        escaped_text = text.replace(" ", "%s")
        success, output = self._run_command(f"shell input text {escaped_text}")

        if success:
            logger.info(f"输入文本: {text}")
        else:
            logger.error(f"输入失败: {output}")

        return success

    def press_back(self) -> bool:
        """
        按返回键

        Returns:
            是否成功
        """
        success, output = self._run_command("shell input keyevent 4")

        if success:
            logger.info("按下返回键")
        else:
            logger.error(f"返回键失败: {output}")

        return success

    def press_home(self) -> bool:
        """
        按主页键

        Returns:
            是否成功
        """
        success, output = self._run_command("shell input keyevent 3")

        if success:
            logger.info("按下主页键")
        else:
            logger.error(f"主页键失败: {output}")

        return success

    def press_enter(self) -> bool:
        """
        按回车键

        Returns:
            是否成功
        """
        success, output = self._run_command("shell input keyevent 66")

        if success:
            logger.info("按下回车键")
        else:
            logger.error(f"回车键失败: {output}")

        return success

    def wake_screen(self) -> bool:
        """
        唤醒屏幕

        Returns:
            是否成功
        """
        success, output = self._run_command("shell input keyevent 26")

        if success:
            logger.info("屏幕已唤醒")
        else:
            logger.error(f"唤醒屏幕失败: {output}")

        return success

    def is_screen_on(self) -> bool:
        """
        检查屏幕是否亮着

        Returns:
            屏幕状态
        """
        success, output = self._run_command("shell dumpsys power | grep 'Display Power'")

        if success and "ON" in output:
            return True
        return False


# 便捷函数
def get_default_device() -> Optional[str]:
    """
    获取默认设备（第一个在线设备）

    Returns:
        设备序列号或 None
    """
    client = ADBClient()
    devices = client.list_devices()

    for device in devices:
        if device["status"] == "device":
            return device["id"]

    return None


if __name__ == "__main__":
    # 测试代码
    print("=== ADB Client 测试 ===")

    # 列出设备
    client = ADBClient()
    devices = client.list_devices()
    print(f"设备列表: {devices}")

    if devices:
        # 使用第一个设备
        client = ADBClient(devices[0]["id"])

        # 获取屏幕尺寸
        size = client.get_screen_size()
        print(f"屏幕尺寸: {size}")

        # 检查屏幕状态
        print(f"屏幕亮着: {client.is_screen_on()}")
