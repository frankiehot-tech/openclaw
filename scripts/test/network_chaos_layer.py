#!/usr/bin/env python3
"""
网络层故障注入器
基于《多Agent系统24小时压力测试问题修复实施方案》第二阶段设计
使用tc netem注入网络故障
"""

import logging
import subprocess
import time

from chaos_engineering_engine import FaultSeverity, FaultType

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class NetworkChaosLayer:
    """网络层故障注入器"""

    def __init__(self, safe_mode: bool = True):
        """
        初始化网络层故障注入器

        Args:
            safe_mode: 安全模式，为True时模拟故障而不实际修改系统
        """
        self.safe_mode = safe_mode
        self.active_faults: dict[str, dict] = {}
        self.network_interfaces = self._detect_network_interfaces()

        logger.info(f"网络层故障注入器初始化完成 (安全模式: {'启用' if safe_mode else '禁用'})")
        logger.info(f"检测到的网络接口: {self.network_interfaces}")

    def _detect_network_interfaces(self) -> list[str]:
        """检测可用的网络接口"""
        interfaces = []

        try:
            # 尝试使用ifconfig或ip命令获取网络接口
            if self.safe_mode:
                # 安全模式下返回模拟接口
                return ["eth0", "wlan0", "lo"]

            # 尝试使用ip命令
            result = subprocess.run(
                ["ip", "-o", "link", "show"], capture_output=True, text=True, timeout=5
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                for line in lines:
                    parts = line.split(":")
                    if len(parts) >= 2:
                        interface = parts[1].strip()
                        if interface and interface != "lo":
                            interfaces.append(interface)

            # 如果ip命令失败，尝试ifconfig
            if not interfaces:
                result = subprocess.run(
                    ["ifconfig", "-a"], capture_output=True, text=True, timeout=5
                )

                if result.returncode == 0:
                    lines = result.stdout.strip().split("\n")
                    for line in lines:
                        if line and not line.startswith(" ") and not line.startswith("\t"):
                            interface = line.split(":")[0]
                            if interface and interface != "lo":
                                interfaces.append(interface)

            # 如果都失败，返回默认接口
            if not interfaces:
                interfaces = ["eth0"]

        except Exception as e:
            logger.warning(f"检测网络接口失败: {e}")
            interfaces = ["eth0"]

        return interfaces

    def _run_tc_command(self, command: list[str], simulate: bool = False) -> dict:
        """
        运行tc命令

        Args:
            command: tc命令参数列表
            simulate: 是否模拟运行

        Returns:
            命令执行结果
        """
        if simulate or self.safe_mode:
            logger.info(f"[模拟] tc命令: {' '.join(command)}")
            return {"success": True, "simulated": True, "command": " ".join(command)}

        try:
            result = subprocess.run(["sudo"] + command, capture_output=True, text=True, timeout=10)

            success = result.returncode == 0

            return {
                "success": success,
                "simulated": False,
                "command": " ".join(command),
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }

        except subprocess.TimeoutExpired:
            logger.error(f"tc命令超时: {' '.join(command)}")
            return {
                "success": False,
                "simulated": False,
                "command": " ".join(command),
                "error": "命令执行超时",
            }
        except Exception as e:
            logger.error(f"tc命令执行失败: {e}")
            return {
                "success": False,
                "simulated": False,
                "command": " ".join(command),
                "error": str(e),
            }

    def inject_fault(
        self, fault_type: FaultType, severity: FaultSeverity, duration_seconds: int = 60
    ) -> dict:
        """
        注入网络故障

        Args:
            fault_type: 故障类型
            severity: 故障严重程度
            duration_seconds: 故障持续时间（秒）

        Returns:
            故障注入结果
        """
        logger.info(
            f"注入网络故障: 类型={fault_type.value}, 严重程度={severity.value}, 持续时间={duration_seconds}秒"
        )

        # 选择目标网络接口
        target_interface = self.network_interfaces[0] if self.network_interfaces else "eth0"

        # 根据故障类型和严重程度确定参数
        params = self._get_fault_params(fault_type, severity)

        # 构造故障ID
        fault_id = f"net_{fault_type.value}_{severity.value}_{int(time.time())}"

        result = {
            "fault_id": fault_id,
            "layer": "network",
            "fault_type": fault_type.value,
            "severity": severity.value,
            "target_interface": target_interface,
            "params": params,
            "injected_at": time.time(),
            "duration_seconds": duration_seconds,
            "simulated": self.safe_mode,
        }

        try:
            if fault_type == FaultType.NETWORK_LATENCY:
                fault_result = self._inject_latency(target_interface, params)
            elif fault_type == FaultType.NETWORK_PACKET_LOSS:
                fault_result = self._inject_packet_loss(target_interface, params)
            elif fault_type == FaultType.NETWORK_PARTITION:
                fault_result = self._inject_network_partition(target_interface, params)
            else:
                fault_result = {"success": False, "error": f"不支持的故障类型: {fault_type.value}"}

            result.update(fault_result)

            if fault_result.get("success", False):
                self.active_faults[fault_id] = result
                logger.info(f"网络故障注入成功: {fault_id}")
            else:
                logger.error(
                    f"网络故障注入失败: {fault_id}, 错误: {fault_result.get('error', '未知错误')}"
                )

        except Exception as e:
            result.update({"success": False, "error": str(e)})
            logger.error(f"网络故障注入异常: {fault_id}, 异常: {e}")

        return result

    def _get_fault_params(self, fault_type: FaultType, severity: FaultSeverity) -> dict:
        """根据故障类型和严重程度获取参数"""
        params = {}

        if fault_type == FaultType.NETWORK_LATENCY:
            # 延迟参数（毫秒）
            if severity == FaultSeverity.LOW:
                params = {"latency_ms": 50, "jitter_ms": 10}
            elif severity == FaultSeverity.MEDIUM:
                params = {"latency_ms": 200, "jitter_ms": 50}
            elif severity == FaultSeverity.HIGH:
                params = {"latency_ms": 1000, "jitter_ms": 200}

        elif fault_type == FaultType.NETWORK_PACKET_LOSS:
            # 丢包率参数（百分比）
            if severity == FaultSeverity.LOW:
                params = {"loss_percent": 1, "correlation_percent": 25}
            elif severity == FaultSeverity.MEDIUM:
                params = {"loss_percent": 5, "correlation_percent": 50}
            elif severity == FaultSeverity.HIGH:
                params = {"loss_percent": 20, "correlation_percent": 75}

        elif fault_type == FaultType.NETWORK_PARTITION:
            # 网络分区参数
            params = {"partition_type": "bidirectional", "severity": severity.value}

        return params

    def _inject_latency(self, interface: str, params: dict) -> dict:
        """注入网络延迟"""
        latency_ms = params.get("latency_ms", 100)
        jitter_ms = params.get("jitter_ms", 20)

        # 添加延迟规则
        commands = [
            # 清除现有规则
            ["tc", "qdisc", "del", "dev", interface, "root"],
            # 添加netem延迟规则
            [
                "tc",
                "qdisc",
                "add",
                "dev",
                interface,
                "root",
                "netem",
                "delay",
                f"{latency_ms}ms",
                f"{jitter_ms}ms",
                "distribution",
                "normal",
            ],
        ]

        results = []
        for cmd in commands:
            result = self._run_tc_command(cmd)
            results.append(result)
            if not result.get("success", False):
                return {"success": False, "error": f"命令失败: {cmd}", "details": results}

        return {
            "success": True,
            "latency_ms": latency_ms,
            "jitter_ms": jitter_ms,
            "details": results,
        }

    def _inject_packet_loss(self, interface: str, params: dict) -> dict:
        """注入网络丢包"""
        loss_percent = params.get("loss_percent", 5)
        correlation_percent = params.get("correlation_percent", 25)

        # 添加丢包规则
        commands = [
            # 清除现有规则
            ["tc", "qdisc", "del", "dev", interface, "root"],
            # 添加netem丢包规则
            [
                "tc",
                "qdisc",
                "add",
                "dev",
                interface,
                "root",
                "netem",
                "loss",
                f"{loss_percent}%",
                f"{correlation_percent}%",
            ],
        ]

        results = []
        for cmd in commands:
            result = self._run_tc_command(cmd)
            results.append(result)
            if not result.get("success", False):
                return {"success": False, "error": f"命令失败: {cmd}", "details": results}

        return {
            "success": True,
            "loss_percent": loss_percent,
            "correlation_percent": correlation_percent,
            "details": results,
        }

    def _inject_network_partition(self, interface: str, params: dict) -> dict:
        """注入网络分区"""
        # 网络分区实际上是通过防火墙规则实现的
        # 这里我们模拟或实际添加防火墙规则

        if self.safe_mode:
            logger.info(f"[模拟] 注入网络分区到接口 {interface}")
            return {
                "success": True,
                "partition_type": params.get("partition_type", "bidirectional"),
                "simulated": True,
            }

        try:
            # 使用iptables添加DROP规则（需要sudo权限）
            severity = params.get("severity", "medium")

            if severity == "low":
                # 低严重程度：只DROP部分端口
                ports = ["80", "443", "8080"]
                results = []
                for port in ports:
                    cmd = [
                        "iptables",
                        "-A",
                        "OUTPUT",
                        "-o",
                        interface,
                        "-p",
                        "tcp",
                        "--dport",
                        port,
                        "-j",
                        "DROP",
                    ]
                    result = self._run_tc_command(cmd, simulate=False)
                    results.append(result)

                success = all(r.get("success", False) for r in results)

                return {
                    "success": success,
                    "partition_type": "partial",
                    "blocked_ports": ports,
                    "details": results,
                }

            else:
                # 中等或高严重程度：DROP所有流量
                cmd = ["iptables", "-A", "OUTPUT", "-o", interface, "-j", "DROP"]
                result = self._run_tc_command(cmd, simulate=False)

                return {
                    "success": result.get("success", False),
                    "partition_type": "complete",
                    "details": [result],
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def recover_fault(self, fault_type: FaultType) -> dict:
        """
        恢复网络故障

        Args:
            fault_type: 故障类型

        Returns:
            恢复结果
        """
        logger.info(f"恢复网络故障: 类型={fault_type.value}")

        # 选择目标网络接口
        target_interface = self.network_interfaces[0] if self.network_interfaces else "eth0"

        try:
            if fault_type == FaultType.NETWORK_PARTITION and not self.safe_mode:
                # 恢复网络分区：清除iptables规则
                cmd = ["iptables", "-D", "OUTPUT", "-o", target_interface, "-j", "DROP"]
                result = self._run_tc_command(cmd, simulate=False)

                if not result.get("success", False):
                    # 尝试另一种方式
                    cmd = ["iptables", "-F"]
                    result = self._run_tc_command(cmd, simulate=False)
            else:
                # 恢复其他故障：清除tc规则
                cmd = ["tc", "qdisc", "del", "dev", target_interface, "root"]
                result = self._run_tc_command(cmd)

            # 从活动故障列表中移除相关故障
            faults_to_remove = []
            for fault_id, fault in self.active_faults.items():
                if fault["fault_type"] == fault_type.value:
                    faults_to_remove.append(fault_id)

            for fault_id in faults_to_remove:
                del self.active_faults[fault_id]

            return {
                "success": result.get("success", False),
                "fault_type": fault_type.value,
                "recovered_faults": len(faults_to_remove),
                "details": result,
            }

        except Exception as e:
            return {"success": False, "error": str(e), "fault_type": fault_type.value}


def test_network_chaos_layer():
    """测试网络层故障注入器"""
    print("🧪 测试网络层故障注入器")
    print("=" * 50)

    # 安全模式测试
    layer = NetworkChaosLayer(safe_mode=True)

    print("\n1. 测试网络延迟注入...")
    result = layer.inject_fault(
        fault_type=FaultType.NETWORK_LATENCY, severity=FaultSeverity.MEDIUM, duration_seconds=10
    )
    print(f"   结果: {result.get('success', False)}")

    print("\n2. 测试网络丢包注入...")
    result = layer.inject_fault(
        fault_type=FaultType.NETWORK_PACKET_LOSS, severity=FaultSeverity.LOW, duration_seconds=10
    )
    print(f"   结果: {result.get('success', False)}")

    print("\n3. 测试网络分区注入...")
    result = layer.inject_fault(
        fault_type=FaultType.NETWORK_PARTITION, severity=FaultSeverity.HIGH, duration_seconds=10
    )
    print(f"   结果: {result.get('success', False)}")

    print("\n4. 测试故障恢复...")
    result = layer.recover_fault(FaultType.NETWORK_LATENCY)
    print(f"   结果: {result.get('success', False)}")

    print("\n✅ 网络层故障注入器测试完成")


if __name__ == "__main__":
    test_network_chaos_layer()
