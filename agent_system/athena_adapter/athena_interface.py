"""
Athena Interface - Athena 接口

Athena 与 AutoGLM Bridge 之间的主要接口
确保 Athena 不能直接访问 ADB，只能通过 bridge 间接控制设备
"""

import logging
import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from athena_adapter.task_router import TaskRouter
from autoglm_bridge.agent_loop import AgentLoop

# 配置日志
logger = logging.getLogger(__name__)

# 日志文件
ATHENA_LOG = "os.path.join(os.path.dirname(os.path.abspath(__file__)), '../logs/athena.log')"

# 配置日志
file_handler = logging.FileHandler(ATHENA_LOG)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(file_handler)


class AthenaInterface:
    """Athena 接口"""

    def __init__(self, device_id: str | None = None):
        """
        初始化 Athena 接口

        Args:
            device_id: 设备序列号
        """
        self.device_id = device_id
        self.router = TaskRouter()
        self.agent_loop = AgentLoop(device_id=device_id)

        logger.info(f"AthenaInterface 初始化, device_id={device_id}")

    def run_task(
        self,
        task: str,
        device: str = "zflip3",
        context: str | None = None,
        max_steps: int = 10,
        use_mock: bool = True,
    ) -> dict:
        """
        运行任务

        Args:
            task: 任务描述
            device: 目标设备
            context: 额外上下文
            max_steps: 最大步数
            use_mock: 是否使用 mock 模式

        Returns:
            执行结果:
            {
                "success": True/False,
                "task": "...",
                "steps": [...],
                "final_state": "..."
            }
        """
        logger.info(f"开始执行任务: {task}")

        # 路由任务
        protocol = self.router.route(task, device, context)

        # 执行任务
        try:
            # 设置 mock 模式
            self.agent_loop.set_mock_mode(use_mock)

            result = self.agent_loop.run_task(
                task=protocol["task"], max_steps=max_steps, device_id=self.device_id
            )

            # 添加 success 字段
            result["success"] = result.get("final_result") == "completed"

            logger.info(f"任务完成: success={result.get('success', False)}")
            return result

        except Exception as e:
            logger.error(f"任务执行失败: {str(e)}")
            return {"success": False, "task": task, "error": str(e), "steps": []}

    def get_status(self) -> dict:
        """
        获取状态

        Returns:
            状态信息
        """
        return {
            "device_id": self.device_id,
            "agent_loop": "running" if self.agent_loop else "stopped",
        }


def run_task(
    task: str,
    device: str = "zflip3",
    context: str | None = None,
    max_steps: int = 10,
    use_mock: bool = True,
    device_id: str | None = None,
) -> dict:
    """
    快捷任务执行函数

    Args:
        task: 任务描述
        device: 目标设备
        context: 额外上下文
        max_steps: 最大步数
        use_mock: 是否使用 mock 模式
        device_id: 设备序列号

    Returns:
        执行结果
    """
    interface = AthenaInterface(device_id)
    return interface.run_task(task, device, context, max_steps, use_mock)


if __name__ == "__main__":
    # 测试代码
    print("=== Athena Interface 测试 ===")

    # 创建接口
    interface = AthenaInterface()

    # 测试任务
    test_tasks = [
        "打开设置",
        "返回",
        "主页",
    ]

    print("\n执行测试任务 (mock 模式):")
    for task in test_tasks:
        print(f"\n>>> {task}")
        result = interface.run_task(task, use_mock=True, max_steps=3)
        print(f"结果: success={result.get('success', False)}")
        print(f"步数: {len(result.get('steps', []))}")
