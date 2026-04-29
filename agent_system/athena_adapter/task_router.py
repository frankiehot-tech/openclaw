"""
Task Router - 任务路由

将 Athena 输入转换为统一协议格式
"""

import logging
from typing import Dict, Optional

# 配置日志
logger = logging.getLogger(__name__)

# 日志文件
ATHENA_LOG = "os.path.join(os.path.dirname(os.path.abspath(__file__)), '../logs/athena.log')"

# 配置日志
file_handler = logging.FileHandler(ATHENA_LOG)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(file_handler)


class TaskRouter:
    """任务路由器"""

    def __init__(self):
        """初始化任务路由器"""
        logger.info("TaskRouter 初始化")

    def route(
        self,
        task: str,
        device: str = "zflip3",
        context: Optional[str] = None,
        priority: Optional[int] = None,
        constraints: Optional[Dict] = None,
    ) -> Dict:
        """
        路由任务

        Args:
            task: 任务描述
            device: 目标设备
            context: 额外上下文
            priority: 优先级 (1-10)
            constraints: 约束条件

        Returns:
            统一协议格式:
            {
                "task": "...",
                "context": "...",
                "device": "zflip3",
                "priority": 5,
                "constraints": {}
            }
        """
        # 基础校验
        if not task or not task.strip():
            raise ValueError("任务不能为空")

        if not device or not device.strip():
            raise ValueError("设备不能为空")

        # 构建协议
        protocol = {
            "task": task.strip(),
            "context": context or "",
            "device": device.strip(),
            "priority": priority if priority is not None else 5,
            "constraints": constraints or {},
        }

        logger.info(f"路由任务: {protocol}")

        return protocol

    def validate_task(self, task: str) -> bool:
        """
        验证任务是否有效

        Args:
            task: 任务描述

        Returns:
            是否有效
        """
        if not task or not task.strip():
            return False

        # 任务长度限制
        if len(task.strip()) > 1000:
            return False

        return True

    def validate_device(self, device: str) -> bool:
        """
        验证设备是否有效

        Args:
            device: 设备标识

        Returns:
            是否有效
        """
        if not device or not device.strip():
            return False

        # 目前只支持 zflip3
        supported_devices = {"zflip3", "zfold3", "emulator"}
        return device.strip().lower() in supported_devices


def route_task(
    task: str,
    device: str = "zflip3",
    context: Optional[str] = None,
    priority: Optional[int] = None,
    constraints: Optional[Dict] = None,
) -> Dict:
    """
    快捷路由函数

    Args:
        task: 任务描述
        device: 目标设备
        context: 额外上下文
        priority: 优先级
        constraints: 约束条件

    Returns:
        统一协议格式
    """
    router = TaskRouter()
    return router.route(task, device, context, priority, constraints)


if __name__ == "__main__":
    # 测试代码
    print("=== Task Router 测试 ===")

    router = TaskRouter()

    # 测试有效任务
    test_cases = [
        ("打开设置", "zflip3"),
        ("打开浏览器并搜索天气", "zflip3"),
        ("返回主页", "zflip3"),
    ]

    print("\n有效任务测试:")
    for task, device in test_cases:
        try:
            result = router.route(task, device)
            print(f"  ✓ {task} -> {result['device']}")
        except Exception as e:
            print(f"  ✗ {task}: {e}")

    # 测试无效任务
    print("\n无效任务测试:")
    invalid_cases = [
        ("", "zflip3"),  # 空任务
        ("打开设置", ""),  # 空设备
    ]

    for task, device in invalid_cases:
        try:
            result = router.route(task, device)
            print(f"  ✗ 应该失败: {task}")
        except ValueError as e:
            print(f"  ✓ 正确拒绝: {e}")

    # 验证方法
    print("\n验证测试:")
    print(f"  validate_task('打开设置'): {router.validate_task('打开设置')}")
    print(f"  validate_task(''): {router.validate_task('')}")
    print(f"  validate_device('zflip3'): {router.validate_device('zflip3')}")
    print(f"  validate_device('unknown'): {router.validate_device('unknown')}")
