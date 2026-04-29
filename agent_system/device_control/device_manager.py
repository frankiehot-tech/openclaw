"""
Device Manager - 设备管理器

管理多个 Android 设备，支持：
- 设备注册与切换
- 设备状态监控
- 设备信息查询
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from .adb_client import ADBClient

# 配置日志
logger = logging.getLogger(__name__)


@dataclass
class DeviceInfo:
    """设备信息"""

    device_id: str
    status: str = "unknown"
    screen_size: tuple = (0, 0)
    model: str = ""
    last_seen: datetime = field(default_factory=datetime.now)
    is_active: bool = False


class DeviceManager:
    """设备管理器"""

    # 设备代号映射
    DEVICE_CODENAME = {
        "zflip3": "Samsung Galaxy Z Flip3",
        "zfold3": "Samsung Galaxy Z Fold3",
        "s21": "Samsung Galaxy S21",
    }

    def __init__(self):
        """初始化设备管理器"""
        self.devices: Dict[str, DeviceInfo] = {}
        self.active_device: Optional[str] = None
        self._adb_client = ADBClient()

    def discover_devices(self) -> List[DeviceInfo]:
        """
        发现并更新设备列表

        Returns:
            设备信息列表
        """
        device_list = self._adb_client.list_devices()

        # 更新设备信息
        for dev in device_list:
            device_id = dev["id"]
            status = dev["status"]

            if device_id not in self.devices:
                self.devices[device_id] = DeviceInfo(device_id=device_id, status=status)
            else:
                self.devices[device_id].status = status
                self.devices[device_id].last_seen = datetime.now()

            # 如果设备在线，获取更多信息
            if status == "device":
                self._update_device_info(device_id)

        # 移除不在线的设备
        offline_devices = [d_id for d_id, d in self.devices.items() if d.status != "device"]
        for d_id in offline_devices:
            del self.devices[d_id]

        logger.info(f"发现 {len(self.devices)} 个在线设备")
        return list(self.devices.values())

    def _update_device_info(self, device_id: str):
        """更新设备详细信息"""
        client = ADBClient(device_id)

        # 获取屏幕尺寸
        size = client.get_screen_size()
        if size:
            self.devices[device_id].screen_size = size

        # 获取设备型号
        # success, output = client._run_command("shell getprop ro.product.model")
        # if success:
        #     self.devices[device_id].model = output.strip()

    def register_device(self, device_id: str, codename: Optional[str] = None):
        """
        注册设备

        Args:
            device_id: 设备序列号
            codename: 设备代号（如 zflip3）
        """
        if device_id not in self.devices:
            self.devices[device_id] = DeviceInfo(device_id=device_id, status="registered")

        if codename:
            self.devices[device_id].model = self.DEVICE_CODENAME.get(codename, codename)

        logger.info(f"注册设备: {device_id}")

    def set_active_device(self, device_id: str) -> bool:
        """
        设置活动设备

        Args:
            device_id: 设备序列号

        Returns:
            是否成功
        """
        if device_id in self.devices:
            # 取消之前活动设备的状态
            if self.active_device and self.active_device in self.devices:
                self.devices[self.active_device].is_active = False

            self.active_device = device_id
            self.devices[device_id].is_active = True

            logger.info(f"设置活动设备: {device_id}")
            return True
        else:
            logger.error(f"设备不存在: {device_id}")
            return False

    def get_active_device(self) -> Optional[str]:
        """
        获取当前活动设备

        Returns:
            设备序列号或 None
        """
        return self.active_device

    def get_device_by_codename(self, codename: str) -> Optional[str]:
        """
        通过代号获取设备

        Args:
            codename: 设备代号

        Returns:
            设备序列号或 None
        """
        for device_id, info in self.devices.items():
            if info.model and codename.lower() in info.model.lower():
                return device_id

        # 如果没有精确匹配，返回第一个在线设备
        if self.devices:
            return list(self.devices.keys())[0]

        return None

    def get_device_info(self, device_id: str) -> Optional[DeviceInfo]:
        """
        获取设备信息

        Args:
            device_id: 设备序列号

        Returns:
            设备信息或 None
        """
        return self.devices.get(device_id)

    def list_devices(self) -> List[DeviceInfo]:
        """
        列出所有设备

        Returns:
            设备信息列表
        """
        return list(self.devices.values())

    def ensure_device_available(self, device_id: Optional[str] = None) -> Optional[str]:
        """
        确保设备可用

        Args:
            device_id: 指定设备ID，None 则使用活动设备

        Returns:
            可用的设备ID或None
        """
        # 如果指定了设备
        if device_id:
            if device_id in self.devices:
                return device_id
            else:
                logger.warning(f"指定设备不可用: {device_id}")
                return None

        # 使用活动设备
        if self.active_device and self.active_device in self.devices:
            return self.active_device

        # 尝试发现设备
        self.discover_devices()

        if self.devices:
            # 设置第一个设备为活动设备
            first_device = list(self.devices.keys())[0]
            self.set_active_device(first_device)
            return first_device

        return None


# 全局设备管理器实例
_manager: Optional[DeviceManager] = None

# 设备超时配置
DEVICE_TIMEOUT = 30  # 设备操作超时（秒）
MAX_DEVICE_CHECK_RETRIES = 3  # 设备检查最大重试次数


def get_device_manager() -> DeviceManager:
    """获取全局设备管理器"""
    global _manager
    if _manager is None:
        _manager = DeviceManager()
    return _manager


def reset_device_manager():
    """重置设备管理器"""
    global _manager
    _manager = None


def check_device_health(device_id: str) -> bool:
    """
    检查设备健康状态

    Args:
        device_id: 设备序列号

    Returns:
        是否健康
    """
    try:
        client = ADBClient(device_id)

        # 尝试获取设备状态
        devices = client.list_devices()

        for dev in devices:
            if dev["id"] == device_id and dev["status"] == "device":
                return True

        return False

    except Exception as e:
        logger.error(f"设备健康检查失败: {device_id}, {str(e)}")
        return False


def get_device_with_timeout(device_id: Optional[str] = None) -> Optional[str]:
    """
    获取设备（带超时控制）

    Args:
        device_id: 指定设备ID

    Returns:
        可用的设备ID或None
    """
    manager = get_device_manager()

    # 尝试多次
    for attempt in range(MAX_DEVICE_CHECK_RETRIES):
        # 刷新设备列表
        manager.discover_devices()

        # 尝试获取设备
        available_device = manager.ensure_device_available(device_id)

        if available_device and check_device_health(available_device):
            return available_device

        logger.warning(f"设备检查失败 (尝试 {attempt + 1}/{MAX_DEVICE_CHECK_RETRIES})")

    return None


if __name__ == "__main__":
    # 测试代码
    print("=== Device Manager 测试 ===")

    manager = get_device_manager()

    # 发现设备
    devices = manager.discover_devices()
    print(f"在线设备: {[d.device_id for d in devices]}")

    if devices:
        # 设置活动设备
        manager.set_active_device(devices[0].device_id)
        print(f"活动设备: {manager.get_active_device()}")

        # 获取设备信息
        info = manager.get_device_info(devices[0].device_id)
        print(f"设备信息: {info}")
