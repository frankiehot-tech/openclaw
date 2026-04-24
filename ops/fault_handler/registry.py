"""
故障注册中心 — 所有 Handler 在此注册，支持自动发现和路由
"""

import json
import logging
import os
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type

logger = logging.getLogger(__name__)


class FaultPhase(str, Enum):
    DETECT = "detect"
    DIAGNOSE = "diagnose"
    REPAIR = "repair"
    VERIFY = "verify"
    REPORT = "report"


class FaultSeverity(str, Enum):
    CRITICAL = "critical"  # 系统不可用
    HIGH = "high"          # 主流程受阻
    MEDIUM = "medium"      # 部分功能受损
    LOW = "low"            # 可忽略


@dataclass
class FaultContext:
    """故障上下文，Handler 通过此获取故障信息"""
    fault_type: str
    phase: FaultPhase = FaultPhase.DETECT
    severity: FaultSeverity = FaultSeverity.MEDIUM
    metadata: Dict[str, Any] = field(default_factory=dict)
    queue_id: Optional[str] = None
    task_id: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.now)


@dataclass 
class FaultResult:
    """Handler 执行结果"""
    success: bool
    fault_type: str
    actions: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    duration_ms: float = 0
    escalated: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseFaultHandler:
    """故障处理器基类"""

    fault_type: str = "unknown"
    severity: FaultSeverity = FaultSeverity.MEDIUM
    max_retries: int = 3

    def detect(self, ctx: FaultContext) -> bool:
        """检测故障是否存在 — 子类实现"""
        raise NotImplementedError

    def diagnose(self, ctx: FaultContext) -> Dict[str, Any]:
        """诊断根因 — 子类实现"""
        raise NotImplementedError

    def repair(self, ctx: FaultContext) -> bool:
        """执行修复 — 子类实现"""
        raise NotImplementedError

    def verify(self, ctx: FaultContext) -> bool:
        """验证修复成功 — 子类实现"""
        raise NotImplementedError

    def handle(self, ctx: FaultContext) -> FaultResult:
        """执行完整的 检测→诊断→修复→验证 流程"""
        started = datetime.now()
        result = FaultResult(success=False, fault_type=self.fault_type)

        try:
            ctx.phase = FaultPhase.DETECT
            if not self.detect(ctx):
                result.success = True
                result.actions.append(f"{self.fault_type}: 未检测到故障，跳过")
                return result

            ctx.phase = FaultPhase.DIAGNOSE
            diagnosis = self.diagnose(ctx)
            result.metadata["diagnosis"] = diagnosis

            ctx.phase = FaultPhase.REPAIR
            for attempt in range(1, self.max_retries + 1):
                try:
                    if self.repair(ctx):
                        result.actions.append(f"修复成功 (第{attempt}次尝试)")
                        break
                except Exception as e:
                    result.errors.append(f"修复失败 (第{attempt}次): {e}")
                    if attempt == self.max_retries:
                        result.escalated = True
                        result.actions.append("已升级告警: 自动修复失败")
                        return result

            ctx.phase = FaultPhase.VERIFY
            if self.verify(ctx):
                result.success = True
                result.actions.append("验证通过")
            else:
                result.errors.append("修复后验证失败")
                result.escalated = True

        except Exception as e:
            result.errors.append(f"处理异常: {e}\n{traceback.format_exc()}")

        result.duration_ms = (datetime.now() - started).total_seconds() * 1000
        return result


class FaultRegistry:
    """故障注册中心"""

    _handlers: Dict[str, BaseFaultHandler] = {}

    @classmethod
    def register(cls, handler_class: Type[BaseFaultHandler]):
        """注册一个 Handler"""
        instance = handler_class()
        cls._handlers[instance.fault_type] = instance
        logger.info(f"注册故障处理器: {instance.fault_type}")

    @classmethod
    def get_handler(cls, fault_type: str) -> Optional[BaseFaultHandler]:
        """获取指定类型的 Handler"""
        return cls._handlers.get(fault_type)

    @classmethod
    def list_handlers(cls) -> List[str]:
        """列出所有已注册的 Handler"""
        return list(cls._handlers.keys())

    @classmethod
    def handle(cls, fault_type: str, **metadata) -> FaultResult:
        """处理指定类型的故障"""
        handler = cls.get_handler(fault_type)
        if not handler:
            return FaultResult(success=False, fault_type=fault_type,
                             errors=[f"未找到处理器: {fault_type}"])
        ctx = FaultContext(fault_type=fault_type, metadata=metadata)
        return handler.handle(ctx)

    @classmethod
    def auto_discover(cls):
        """自动发现所有 Handler 子类并注册"""
        import importlib
        import pkgutil

        package_dir = os.path.dirname(__file__)
        handlers_dir = os.path.join(package_dir, "handlers")

        if os.path.isdir(handlers_dir):
            for _, module_name, _ in pkgutil.iter_modules([handlers_dir]):
                importlib.import_module(f"ops.fault_handler.handlers.{module_name}")

        return cls
