"""
Contracts模块 - 提供状态同步、进程生命周期等契约接口
"""

from .athena_state_sync_adapter import (
    AthenaStateSyncAdapter,
    get_athena_state_sync_adapter,
)
from .data_quality import DataQualityContract
from .process_lifecycle import ProcessLifecycleContract

# 从各模块导入契约类
from .state_sync import StateSyncContract

__all__ = [
    "StateSyncContract",
    "AthenaStateSyncAdapter",
    "DataQualityContract",
    "ProcessLifecycleContract",
    "get_athena_state_sync_adapter",
]
