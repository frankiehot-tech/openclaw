#!/usr/bin/env python3
"""
混沌工程引擎 - 四层故障注入实现
基于《多Agent系统24小时压力测试问题修复实施方案》第二阶段设计
"""

import logging
import threading
import time
from datetime import datetime
from enum import Enum

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FaultSeverity(Enum):
    """故障严重程度"""

    LOW = "low"  # 轻微故障
    MEDIUM = "medium"  # 中等故障
    HIGH = "high"  # 严重故障


class ChaosLayer(Enum):
    """混沌注入层"""

    NETWORK = "network"  # 网络层
    AGENT = "agent"  # Agent层
    TOOL = "tool"  # 工具层
    MODEL = "model"  # 模型层


class FaultType(Enum):
    """故障类型"""

    # 网络层故障
    NETWORK_LATENCY = "network_latency"  # 网络延迟
    NETWORK_PACKET_LOSS = "network_packet_loss"  # 网络丢包
    NETWORK_PARTITION = "network_partition"  # 网络分区

    # Agent层故障
    AGENT_CRASH = "agent_crash"  # Agent崩溃
    AGENT_MEMORY_PRESSURE = "agent_memory_pressure"  # 内存压力
    AGENT_CPU_PRESSURE = "agent_cpu_pressure"  # CPU压力

    # 工具层故障
    TOOL_API_ERROR = "tool_api_error"  # API错误
    TOOL_TIMEOUT = "tool_timeout"  # 超时错误
    TOOL_DEGRADATION = "tool_degradation"  # 性能降级

    # 模型层故障
    MODEL_LATENCY = "model_latency"  # 响应延迟
    MODEL_QUALITY_DEGRADATION = "model_quality_degradation"  # 输出质量劣化
    MODEL_HALLUCINATION = "model_hallucination"  # 幻觉生成


class ChaosEngineeringEngine:
    """混沌工程引擎 - 四层故障注入"""

    def __init__(self, safe_mode: bool = True):
        """
        初始化混沌工程引擎

        Args:
            safe_mode: 安全模式，为True时避免真实系统破坏
        """
        self.safe_mode = safe_mode
        self.active_faults: list[dict] = []
        self.recovery_threads: dict[str, threading.Thread] = {}

        # 各层故障注入器
        self.network_layer = None
        self.agent_layer = None
        self.tool_layer = None
        self.model_layer = None

        # 初始化各层
        self._initialize_layers()

        logger.info(f"混沌工程引擎初始化完成 (安全模式: {'启用' if safe_mode else '禁用'})")

    def _initialize_layers(self):
        """初始化各层故障注入器"""
        try:
            # 直接导入模块，不使用相对导入
            from network_chaos_layer import NetworkChaosLayer

            self.network_layer = NetworkChaosLayer(safe_mode=self.safe_mode)
            logger.info("网络层故障注入器初始化成功")
        except ImportError as e:
            logger.warning(f"网络层故障注入器初始化失败: {e}")

        try:
            from agent_chaos_layer import AgentChaosLayer

            self.agent_layer = AgentChaosLayer(safe_mode=self.safe_mode)
            logger.info("Agent层故障注入器初始化成功")
        except ImportError as e:
            logger.warning(f"Agent层故障注入器初始化失败: {e}")

        try:
            from tool_chaos_layer import ToolChaosLayer

            self.tool_layer = ToolChaosLayer(safe_mode=self.safe_mode)
            logger.info("工具层故障注入器初始化成功")
        except ImportError as e:
            logger.warning(f"工具层故障注入器初始化失败: {e}")

        try:
            from model_chaos_layer import ModelChaosLayer

            self.model_layer = ModelChaosLayer(safe_mode=self.safe_mode)
            logger.info("模型层故障注入器初始化成功")
        except ImportError as e:
            logger.warning(f"模型层故障注入器初始化失败: {e}")

    def inject_fault(
        self,
        layer: ChaosLayer,
        fault_type: FaultType,
        severity: FaultSeverity,
        duration_seconds: int = 60,
    ) -> dict:
        """
        注入故障

        Args:
            layer: 故障注入层
            fault_type: 故障类型
            severity: 故障严重程度
            duration_seconds: 故障持续时间（秒）

        Returns:
            故障注入结果
        """
        fault_id = f"{layer.value}_{fault_type.value}_{severity.value}_{int(time.time())}"

        fault_info = {
            "id": fault_id,
            "layer": layer.value,
            "fault_type": fault_type.value,
            "severity": severity.value,
            "injected_at": datetime.now().isoformat(),
            "duration_seconds": duration_seconds,
            "status": "injecting",
            "recovery_scheduled": False,
        }

        logger.info(f"开始注入故障: {fault_id}")

        try:
            # 根据层选择注入器
            if layer == ChaosLayer.NETWORK and self.network_layer:
                result = self.network_layer.inject_fault(fault_type, severity, duration_seconds)
            elif layer == ChaosLayer.AGENT and self.agent_layer:
                result = self.agent_layer.inject_fault(fault_type, severity, duration_seconds)
            elif layer == ChaosLayer.TOOL and self.tool_layer:
                result = self.tool_layer.inject_fault(fault_type, severity, duration_seconds)
            elif layer == ChaosLayer.MODEL and self.model_layer:
                result = self.model_layer.inject_fault(fault_type, severity, duration_seconds)
            else:
                result = {
                    "success": False,
                    "error": f"层 {layer.value} 的故障注入器未初始化或不受支持",
                    "simulated": True,
                }

            fault_info.update(result)
            fault_info["status"] = "injected" if result.get("success", False) else "failed"

            if result.get("success", False):
                self.active_faults.append(fault_info)
                logger.info(f"故障注入成功: {fault_id}")

                # 安排自动恢复
                if duration_seconds > 0:
                    self._schedule_recovery(fault_id, duration_seconds)
            else:
                logger.error(f"故障注入失败: {fault_id}, 错误: {result.get('error', '未知错误')}")

        except Exception as e:
            fault_info.update({"success": False, "error": str(e), "simulated": True})
            fault_info["status"] = "failed"
            logger.error(f"故障注入异常: {fault_id}, 异常: {e}")

        return fault_info

    def _schedule_recovery(self, fault_id: str, delay_seconds: int):
        """安排故障自动恢复"""

        def recovery_task():
            time.sleep(delay_seconds)
            self.recover_fault(fault_id)

        thread = threading.Thread(target=recovery_task, daemon=True)
        thread.start()
        self.recovery_threads[fault_id] = thread

        logger.info(f"安排故障 {fault_id} 在 {delay_seconds} 秒后自动恢复")

    def recover_fault(self, fault_id: str) -> dict:
        """
        恢复特定故障

        Args:
            fault_id: 故障ID

        Returns:
            恢复结果
        """
        logger.info(f"开始恢复故障: {fault_id}")

        # 查找故障
        fault_to_recover = None
        for _i, fault in enumerate(self.active_faults):
            if fault["id"] == fault_id:
                fault_to_recover = fault
                break

        if not fault_to_recover:
            return {"success": False, "error": f"未找到故障: {fault_id}", "fault_id": fault_id}

        layer = ChaosLayer(fault_to_recover["layer"])
        fault_type = FaultType(fault_to_recover["fault_type"])

        recovery_result = {
            "fault_id": fault_id,
            "layer": layer.value,
            "fault_type": fault_type.value,
            "recovered_at": datetime.now().isoformat(),
            "status": "recovering",
        }

        try:
            # 根据层选择恢复器
            if layer == ChaosLayer.NETWORK and self.network_layer:
                result = self.network_layer.recover_fault(fault_type)
            elif layer == ChaosLayer.AGENT and self.agent_layer:
                result = self.agent_layer.recover_fault(fault_type)
            elif layer == ChaosLayer.TOOL and self.tool_layer:
                result = self.tool_layer.recover_fault(fault_type)
            elif layer == ChaosLayer.MODEL and self.model_layer:
                result = self.model_layer.recover_fault(fault_type)
            else:
                result = {
                    "success": False,
                    "error": f"层 {layer.value} 的故障恢复器未初始化",
                    "simulated": True,
                }

            recovery_result.update(result)
            recovery_result["status"] = (
                "recovered" if result.get("success", False) else "recovery_failed"
            )

            if result.get("success", False):
                # 从活动故障列表中移除
                if fault_to_recover in self.active_faults:
                    self.active_faults.remove(fault_to_recover)

                # 移除恢复线程
                if fault_id in self.recovery_threads:
                    del self.recovery_threads[fault_id]

                logger.info(f"故障恢复成功: {fault_id}")
            else:
                logger.error(f"故障恢复失败: {fault_id}, 错误: {result.get('error', '未知错误')}")

        except Exception as e:
            recovery_result.update({"success": False, "error": str(e), "simulated": True})
            recovery_result["status"] = "recovery_failed"
            logger.error(f"故障恢复异常: {fault_id}, 异常: {e}")

        return recovery_result

    def recover_all_faults(self) -> list[dict]:
        """恢复所有活动故障"""
        logger.info(f"开始恢复所有活动故障 (共 {len(self.active_faults)} 个)")

        results = []
        faults_to_recover = self.active_faults.copy()

        for fault in faults_to_recover:
            result = self.recover_fault(fault["id"])
            results.append(result)

        logger.info(
            f"所有故障恢复完成 (成功: {sum(1 for r in results if r.get('success', False))}, 失败: {sum(1 for r in results if not r.get('success', True))})"
        )
        return results

    def get_active_faults(self) -> list[dict]:
        """获取所有活动故障"""
        return self.active_faults.copy()

    def get_fault_statistics(self) -> dict:
        """获取故障统计信息"""
        stats = {
            "total_active": len(self.active_faults),
            "by_layer": {},
            "by_severity": {},
            "by_type": {},
        }

        for fault in self.active_faults:
            # 按层统计
            layer = fault["layer"]
            stats["by_layer"][layer] = stats["by_layer"].get(layer, 0) + 1

            # 按严重程度统计
            severity = fault["severity"]
            stats["by_severity"][severity] = stats["by_severity"].get(severity, 0) + 1

            # 按类型统计
            fault_type = fault["fault_type"]
            stats["by_type"][fault_type] = stats["by_type"].get(fault_type, 0) + 1

        return stats

    def run_chaos_scenario(self, scenario_name: str, scenario_config: dict) -> dict:
        """
        运行混沌测试场景

        Args:
            scenario_name: 场景名称
            scenario_config: 场景配置

        Returns:
            场景执行结果
        """
        logger.info(f"开始运行混沌测试场景: {scenario_name}")

        scenario_result = {
            "scenario_name": scenario_name,
            "started_at": datetime.now().isoformat(),
            "faults_injected": [],
            "total_faults": len(scenario_config.get("faults", [])),
            "successful_faults": 0,
            "failed_faults": 0,
        }

        faults = scenario_config.get("faults", [])

        for fault_config in faults:
            try:
                layer = ChaosLayer(fault_config["layer"])
                fault_type = FaultType(fault_config["fault_type"])
                severity = FaultSeverity(fault_config.get("severity", "medium"))
                duration = fault_config.get("duration_seconds", 60)

                fault_result = self.inject_fault(layer, fault_type, severity, duration)

                scenario_result["faults_injected"].append(fault_result)

                if fault_result.get("success", False):
                    scenario_result["successful_faults"] += 1
                else:
                    scenario_result["failed_faults"] += 1

                # 故障之间的间隔
                delay = fault_config.get("delay_before_next", 10)
                if delay > 0:
                    time.sleep(delay)

            except Exception as e:
                logger.error(f"场景 {scenario_name} 中的故障注入失败: {e}")
                scenario_result["failed_faults"] += 1

        scenario_result["completed_at"] = datetime.now().isoformat()
        scenario_result["duration_seconds"] = (
            datetime.fromisoformat(scenario_result["completed_at"])
            - datetime.fromisoformat(scenario_result["started_at"])
        ).total_seconds()

        logger.info(
            f"混沌测试场景完成: {scenario_name}, 成功: {scenario_result['successful_faults']}/{scenario_result['total_faults']}"
        )

        return scenario_result


def main():
    """主函数 - 测试混沌工程引擎"""
    print("🚀 混沌工程引擎测试")
    print("=" * 50)

    engine = ChaosEngineeringEngine(safe_mode=True)

    # 测试故障注入
    print("\n1. 测试网络延迟故障注入...")
    result = engine.inject_fault(
        layer=ChaosLayer.NETWORK,
        fault_type=FaultType.NETWORK_LATENCY,
        severity=FaultSeverity.MEDIUM,
        duration_seconds=30,
    )
    print(f"   结果: {result}")

    print("\n2. 测试Agent内存压力故障注入...")
    result = engine.inject_fault(
        layer=ChaosLayer.AGENT,
        fault_type=FaultType.AGENT_MEMORY_PRESSURE,
        severity=FaultSeverity.LOW,
        duration_seconds=30,
    )
    print(f"   结果: {result}")

    print("\n3. 获取活动故障...")
    active_faults = engine.get_active_faults()
    print(f"   活动故障数: {len(active_faults)}")

    print("\n4. 获取故障统计...")
    stats = engine.get_fault_statistics()
    print(f"   统计: {stats}")

    print("\n5. 恢复所有故障...")
    recovery_results = engine.recover_all_faults()
    print(f"   恢复结果数: {len(recovery_results)}")

    print("\n✅ 混沌工程引擎测试完成")


if __name__ == "__main__":
    main()
