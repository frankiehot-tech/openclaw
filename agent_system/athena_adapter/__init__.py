"""
Athena Adapter - Athena 接入层

Athena 与 AutoGLM Bridge 之间的桥梁
确保 Athena 不能直接访问 ADB，只能通过 bridge 间接控制设备
"""

from .athena_interface import AthenaInterface, run_task
from .task_router import TaskRouter, route_task

__all__ = [
    "run_task",
    "AthenaInterface",
    "TaskRouter",
    "route_task",
]
