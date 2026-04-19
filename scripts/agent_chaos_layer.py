#!/usr/bin/env python3
"""
Agent层故障注入器
基于《多Agent系统24小时压力测试问题修复实施方案》第二阶段设计
实现Agent进程故障注入、内存压力测试、CPU饱和测试等
"""

import logging
import os
import random
import signal
import subprocess
import sys
import threading
import time
from typing import Any, Dict, List, Optional

import psutil
from chaos_engineering_engine import FaultSeverity, FaultType

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class AgentChaosLayer:
    """Agent层故障注入器"""

    def __init__(self, safe_mode: bool = True):
        """
        初始化Agent层故障注入器

        Args:
            safe_mode: 安全模式，为True时模拟故障而不实际终止进程
        """
        self.safe_mode = safe_mode
        self.active_faults: Dict[str, Dict] = {}
        self.killed_processes: List[Dict] = []
        self.stress_threads: Dict[str, threading.Thread] = {}

        # 检测当前运行的Agent进程
        self.agent_processes = self._detect_agent_processes()

        logger.info(f"Agent层故障注入器初始化完成 (安全模式: {'启用' if safe_mode else '禁用'})")
        logger.info(f"检测到的Agent进程: {len(self.agent_processes)} 个")

    def _detect_agent_processes(self) -> List[Dict]:
        """检测当前运行的Agent相关进程"""
        agent_processes = []

        try:
            # 查找包含"athena"、"agent"、"runner"等关键字的进程
            keywords = ["athena", "agent", "runner", "plan", "queue"]

            for proc in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
                try:
                    process_info = proc.info

                    # 检查进程命令行是否包含关键字
                    cmdline = " ".join(process_info.get("cmdline", []) or [])

                    for keyword in keywords:
                        if keyword.lower() in cmdline.lower():
                            # 排除本进程自身
                            if process_info["pid"] != os.getpid():
                                agent_processes.append(
                                    {
                                        "pid": process_info["pid"],
                                        "name": process_info.get("name", "unknown"),
                                        "cmdline": cmdline[:100],  # 截取前100字符
                                        "create_time": process_info.get("create_time", 0),
                                    }
                                )
                            break

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        except Exception as e:
            logger.warning(f"检测Agent进程失败: {e}")

            # 安全模式下返回模拟进程
            if self.safe_mode:
                agent_processes = [
                    {
                        "pid": 1001,
                        "name": "athena_ai_plan_runner",
                        "cmdline": "python3 athena_ai_plan_runner.py",
                        "create_time": time.time() - 3600,
                    },
                    {
                        "pid": 1002,
                        "name": "agent_dispatcher",
                        "cmdline": "python3 agent_dispatcher.py",
                        "create_time": time.time() - 1800,
                    },
                    {
                        "pid": 1003,
                        "name": "task_processor",
                        "cmdline": "python3 task_processor.py",
                        "create_time": time.time() - 900,
                    },
                ]

        return agent_processes

    def _get_agent_by_pid(self, pid: int) -> Optional[Dict]:
        """根据PID获取Agent信息"""
        for agent in self.agent_processes:
            if agent["pid"] == pid:
                return agent
        return None

    def inject_fault(
        self, fault_type: FaultType, severity: FaultSeverity, duration_seconds: int = 60
    ) -> Dict:
        """
        注入Agent故障

        Args:
            fault_type: 故障类型
            severity: 故障严重程度
            duration_seconds: 故障持续时间（秒）

        Returns:
            故障注入结果
        """
        logger.info(
            f"注入Agent故障: 类型={fault_type.value}, 严重程度={severity.value}, 持续时间={duration_seconds}秒"
        )

        # 构造故障ID
        fault_id = f"agent_{fault_type.value}_{severity.value}_{int(time.time())}"

        result = {
            "fault_id": fault_id,
            "layer": "agent",
            "fault_type": fault_type.value,
            "severity": severity.value,
            "injected_at": time.time(),
            "duration_seconds": duration_seconds,
            "simulated": self.safe_mode,
        }

        try:
            if fault_type == FaultType.AGENT_CRASH:
                fault_result = self._inject_agent_crash(severity)
            elif fault_type == FaultType.AGENT_MEMORY_PRESSURE:
                fault_result = self._inject_memory_pressure(severity, duration_seconds)
            elif fault_type == FaultType.AGENT_CPU_PRESSURE:
                fault_result = self._inject_cpu_pressure(severity, duration_seconds)
            else:
                fault_result = {"success": False, "error": f"不支持的故障类型: {fault_type.value}"}

            result.update(fault_result)

            if fault_result.get("success", False):
                self.active_faults[fault_id] = result
                logger.info(f"Agent故障注入成功: {fault_id}")
            else:
                logger.error(
                    f"Agent故障注入失败: {fault_id}, 错误: {fault_result.get('error', '未知错误')}"
                )

        except Exception as e:
            result.update({"success": False, "error": str(e)})
            logger.error(f"Agent故障注入异常: {fault_id}, 异常: {e}")

        return result

    def _inject_agent_crash(self, severity: FaultSeverity) -> Dict:
        """注入Agent崩溃故障"""
        if not self.agent_processes:
            return {"success": False, "error": "未找到可终止的Agent进程"}

        # 根据严重程度选择要终止的进程数量
        if severity == FaultSeverity.LOW:
            num_to_kill = 1
        elif severity == FaultSeverity.MEDIUM:
            num_to_kill = min(2, len(self.agent_processes))
        elif severity == FaultSeverity.HIGH:
            num_to_kill = min(3, len(self.agent_processes))
        else:
            num_to_kill = 1

        # 随机选择进程
        selected_agents = random.sample(
            self.agent_processes, min(num_to_kill, len(self.agent_processes))
        )

        killed_results = []

        for agent in selected_agents:
            pid = agent["pid"]
            agent_name = agent["name"]

            kill_result = self._kill_agent_process(pid, agent_name)
            killed_results.append(kill_result)

            if kill_result.get("success", False):
                # 记录被杀死的进程
                self.killed_processes.append(
                    {"pid": pid, "name": agent_name, "killed_at": time.time(), "agent_info": agent}
                )

        success_count = sum(1 for r in killed_results if r.get("success", False))

        return {
            "success": success_count > 0,
            "agents_selected": len(selected_agents),
            "agents_killed": success_count,
            "kill_results": killed_results,
            "severity": severity.value,
        }

    def _kill_agent_process(self, pid: int, agent_name: str) -> Dict:
        """杀死Agent进程"""
        if self.safe_mode:
            logger.info(f"[模拟] 终止Agent进程: PID={pid}, 名称={agent_name}")
            return {
                "success": True,
                "pid": pid,
                "name": agent_name,
                "method": "simulated_kill",
                "simulated": True,
            }

        try:
            # 尝试优雅终止
            os.kill(pid, signal.SIGTERM)
            time.sleep(1)  # 等待进程终止

            # 检查进程是否还存在
            try:
                psutil.Process(pid)
                # 进程还存在，强制终止
                os.kill(pid, signal.SIGKILL)
                kill_method = "sigkill"
            except psutil.NoSuchProcess:
                kill_method = "sigterm"

            logger.info(f"成功终止Agent进程: PID={pid}, 名称={agent_name}, 方法={kill_method}")

            return {
                "success": True,
                "pid": pid,
                "name": agent_name,
                "method": kill_method,
                "simulated": False,
            }

        except ProcessLookupError:
            logger.warning(f"进程不存在: PID={pid}")
            return {
                "success": False,
                "pid": pid,
                "name": agent_name,
                "error": "进程不存在",
                "simulated": False,
            }
        except PermissionError:
            logger.error(f"权限不足，无法终止进程: PID={pid}")
            return {
                "success": False,
                "pid": pid,
                "name": agent_name,
                "error": "权限不足",
                "simulated": False,
            }
        except Exception as e:
            logger.error(f"终止进程失败: PID={pid}, 错误: {e}")
            return {
                "success": False,
                "pid": pid,
                "name": agent_name,
                "error": str(e),
                "simulated": False,
            }

    def _inject_memory_pressure(self, severity: FaultSeverity, duration_seconds: int) -> Dict:
        """注入内存压力故障"""
        # 根据严重程度确定内存使用量
        if severity == FaultSeverity.LOW:
            memory_mb = 100  # 100MB
            num_threads = 1
        elif severity == FaultSeverity.MEDIUM:
            memory_mb = 500  # 500MB
            num_threads = 2
        elif severity == FaultSeverity.HIGH:
            memory_mb = 2000  # 2GB
            num_threads = 3
        else:
            memory_mb = 100
            num_threads = 1

        # 创建内存压力线程
        thread_id = f"memory_pressure_{int(time.time())}"

        def memory_pressure_task():
            """内存压力任务：分配内存并保持"""
            try:
                # 分配内存
                memory_block = []
                chunk_size = 10 * 1024 * 1024  # 10MB
                chunks_needed = memory_mb // 10

                logger.info(f"开始内存压力测试: 目标={memory_mb}MB, 块数={chunks_needed}")

                for i in range(chunks_needed):
                    # 分配10MB内存块
                    block = bytearray(chunk_size)
                    memory_block.append(block)

                    # 每分配10块后暂停一下
                    if i % 10 == 9:
                        time.sleep(0.1)

                # 保持内存压力指定时间
                logger.info(
                    f"内存压力测试进行中: 已分配{memory_mb}MB, 持续时间={duration_seconds}秒"
                )
                time.sleep(duration_seconds)

                # 释放内存
                memory_block.clear()
                logger.info(f"内存压力测试完成: 释放{memory_mb}MB内存")

            except Exception as e:
                logger.error(f"内存压力测试异常: {e}")

        if self.safe_mode:
            logger.info(f"[模拟] 内存压力测试: {memory_mb}MB, 持续时间={duration_seconds}秒")
            return {
                "success": True,
                "memory_mb": memory_mb,
                "duration_seconds": duration_seconds,
                "threads": num_threads,
                "simulated": True,
            }

        # 启动内存压力线程
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(
                target=memory_pressure_task, name=f"memory_pressure_{i}", daemon=True
            )
            thread.start()
            threads.append(thread)

        # 记录线程
        self.stress_threads[thread_id] = threads[0] if threads else None

        return {
            "success": True,
            "memory_mb": memory_mb,
            "duration_seconds": duration_seconds,
            "threads": num_threads,
            "thread_id": thread_id,
            "simulated": False,
        }

    def _inject_cpu_pressure(self, severity: FaultSeverity, duration_seconds: int) -> Dict:
        """注入CPU压力故障"""
        # 根据严重程度确定CPU使用率
        if severity == FaultSeverity.LOW:
            cpu_percent = 50  # 50% CPU使用率
            num_threads = 2
        elif severity == FaultSeverity.MEDIUM:
            cpu_percent = 80  # 80% CPU使用率
            num_threads = 4
        elif severity == FaultSeverity.HIGH:
            cpu_percent = 95  # 95% CPU使用率
            num_threads = 8
        else:
            cpu_percent = 50
            num_threads = 2

        # 创建CPU压力线程
        thread_id = f"cpu_pressure_{int(time.time())}"

        def cpu_pressure_task():
            """CPU压力任务：进行高强度计算"""
            try:
                end_time = time.time() + duration_seconds

                logger.info(
                    f"开始CPU压力测试: 目标使用率={cpu_percent}%, 持续时间={duration_seconds}秒"
                )

                while time.time() < end_time:
                    # 进行一些计算密集型操作
                    for _ in range(1000000):
                        _ = 3.14159 * 2.71828

                    # 控制CPU使用率
                    if cpu_percent < 100:
                        sleep_time = (1 - cpu_percent / 100) * 0.1
                        if sleep_time > 0:
                            time.sleep(sleep_time)

                logger.info(f"CPU压力测试完成: 持续时间={duration_seconds}秒")

            except Exception as e:
                logger.error(f"CPU压力测试异常: {e}")

        if self.safe_mode:
            logger.info(f"[模拟] CPU压力测试: {cpu_percent}%使用率, 持续时间={duration_seconds}秒")
            return {
                "success": True,
                "cpu_percent": cpu_percent,
                "duration_seconds": duration_seconds,
                "threads": num_threads,
                "simulated": True,
            }

        # 启动CPU压力线程
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(
                target=cpu_pressure_task, name=f"cpu_pressure_{i}", daemon=True
            )
            thread.start()
            threads.append(thread)

        # 记录线程
        self.stress_threads[thread_id] = threads[0] if threads else None

        return {
            "success": True,
            "cpu_percent": cpu_percent,
            "duration_seconds": duration_seconds,
            "threads": num_threads,
            "thread_id": thread_id,
            "simulated": False,
        }

    def recover_fault(self, fault_type: FaultType) -> Dict:
        """
        恢复Agent故障

        Args:
            fault_type: 故障类型

        Returns:
            恢复结果
        """
        logger.info(f"恢复Agent故障: 类型={fault_type.value}")

        try:
            if fault_type == FaultType.AGENT_CRASH:
                # 对于Agent崩溃，我们可以尝试重启进程
                # 这里我们只是清除记录
                recovered_count = len(self.killed_processes)
                self.killed_processes.clear()

                recovery_result = {
                    "success": True,
                    "fault_type": fault_type.value,
                    "agents_recovered": recovered_count,
                    "recovery_action": "clear_killed_records",
                }

            elif fault_type in [FaultType.AGENT_MEMORY_PRESSURE, FaultType.AGENT_CPU_PRESSURE]:
                # 对于压力测试，停止压力线程
                # 注意：实际的压力线程会在完成后自动结束
                threads_stopped = 0
                for thread_id, thread in list(self.stress_threads.items()):
                    if thread and thread.is_alive():
                        # 我们无法直接停止线程，但可以记录
                        threads_stopped += 1

                # 清除线程记录
                self.stress_threads.clear()

                recovery_result = {
                    "success": True,
                    "fault_type": fault_type.value,
                    "threads_stopped": threads_stopped,
                    "recovery_action": "clear_stress_threads",
                }

            else:
                recovery_result = {
                    "success": False,
                    "error": f"不支持的故障类型: {fault_type.value}",
                }

            # 从活动故障列表中移除相关故障
            faults_to_remove = []
            for fault_id, fault in self.active_faults.items():
                if fault["fault_type"] == fault_type.value:
                    faults_to_remove.append(fault_id)

            for fault_id in faults_to_remove:
                del self.active_faults[fault_id]

            recovery_result["recovered_faults"] = len(faults_to_remove)

            return recovery_result

        except Exception as e:
            return {"success": False, "error": str(e), "fault_type": fault_type.value}

    def restart_killed_agents(self) -> List[Dict]:
        """
        重启被杀死的Agent进程（模拟）
        在实际环境中，这可能需要调用系统的进程管理工具

        Returns:
            重启结果列表
        """
        logger.info(f"尝试重启 {len(self.killed_processes)} 个被杀死的Agent进程")

        restart_results = []

        for killed_agent in self.killed_processes:
            agent_info = killed_agent.get("agent_info", {})
            cmdline = agent_info.get("cmdline", "")

            if self.safe_mode or not cmdline:
                # 模拟重启
                result = {
                    "pid": killed_agent["pid"],
                    "name": killed_agent["name"],
                    "success": True,
                    "simulated": True,
                    "restart_command": f"[模拟] {cmdline}",
                }
            else:
                # 实际重启（需要根据具体环境实现）
                try:
                    # 解析命令行
                    parts = cmdline.split()
                    if parts and parts[0].endswith(".py"):
                        # Python脚本
                        command = ["python3"] + parts
                    else:
                        command = parts

                    # 启动进程
                    process = subprocess.Popen(
                        command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        start_new_session=True,
                    )

                    result = {
                        "pid": process.pid,
                        "name": killed_agent["name"],
                        "success": True,
                        "simulated": False,
                        "restart_command": " ".join(command),
                        "new_pid": process.pid,
                    }

                except Exception as e:
                    result = {
                        "pid": killed_agent["pid"],
                        "name": killed_agent["name"],
                        "success": False,
                        "error": str(e),
                        "simulated": False,
                    }

            restart_results.append(result)

        # 清空被杀死的进程记录
        self.killed_processes.clear()

        return restart_results


def test_agent_chaos_layer():
    """测试Agent层故障注入器"""
    print("🧪 测试Agent层故障注入器")
    print("=" * 50)

    # 安全模式测试
    layer = AgentChaosLayer(safe_mode=True)

    print(f"\n1. 检测到的Agent进程: {len(layer.agent_processes)} 个")
    for i, agent in enumerate(layer.agent_processes[:3]):  # 只显示前3个
        print(f"   {i+1}. PID={agent['pid']}, 名称={agent['name']}")

    print("\n2. 测试Agent崩溃注入...")
    result = layer.inject_fault(
        fault_type=FaultType.AGENT_CRASH, severity=FaultSeverity.MEDIUM, duration_seconds=10
    )
    print(
        f"   结果: 成功={result.get('success', False)}, 终止进程数={result.get('agents_killed', 0)}"
    )

    print("\n3. 测试内存压力注入...")
    result = layer.inject_fault(
        fault_type=FaultType.AGENT_MEMORY_PRESSURE, severity=FaultSeverity.LOW, duration_seconds=5
    )
    print(f"   结果: 成功={result.get('success', False)}, 内存={result.get('memory_mb', 0)}MB")

    print("\n4. 测试CPU压力注入...")
    result = layer.inject_fault(
        fault_type=FaultType.AGENT_CPU_PRESSURE, severity=FaultSeverity.HIGH, duration_seconds=5
    )
    print(
        f"   结果: 成功={result.get('success', False)}, CPU使用率={result.get('cpu_percent', 0)}%"
    )

    print("\n5. 测试故障恢复...")
    result = layer.recover_fault(FaultType.AGENT_CRASH)
    print(
        f"   结果: 成功={result.get('success', False)}, 恢复故障数={result.get('recovered_faults', 0)}"
    )

    print("\n6. 测试重启被杀死的Agent...")
    restart_results = layer.restart_killed_agents()
    print(f"   结果: 重启了 {len(restart_results)} 个Agent")

    print("\n✅ Agent层故障注入器测试完成")


if __name__ == "__main__":
    test_agent_chaos_layer()
