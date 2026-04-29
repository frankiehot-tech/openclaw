"""
混沌工程故障注入脚本包
包含多Agent系统24小时压力测试问题修复实施方案第二阶段的所有组件
"""

__version__ = "1.0.0"
__all__ = [
    "ChaosEngineeringEngine",
    "FaultSeverity",
    "ChaosLayer",
    "FaultType",
    "NetworkChaosLayer",
    "AgentChaosLayer",
    "ToolChaosLayer",
    "ModelChaosLayer",
]

# 导入核心类
from .test.chaos_engineering_engine import (
    ChaosEngineeringEngine,
    ChaosLayer,
    FaultSeverity,
    FaultType,
)

# 这些导入可能在对应的层创建后启用
try:
    from .test.network_chaos_layer import NetworkChaosLayer
except ImportError:
    NetworkChaosLayer = None

try:
    from .test.agent_chaos_layer import AgentChaosLayer
except ImportError:
    AgentChaosLayer = None

try:
    from .test.tool_chaos_layer import ToolChaosLayer
except ImportError:
    ToolChaosLayer = None

try:
    from .test.model_chaos_layer import ModelChaosLayer
except ImportError:
    ModelChaosLayer = None
