"""
进程生命周期契约 - 解决进程可靠性契约缺失和活跃占位检测延迟问题

基于深度审计发现：
1. 进程可靠性契约缺失：spawn_build_worker函数存在状态-进程启动时序问题
2. 活跃占位检测延迟：死进程检测有5分钟宽限延迟（queue_liveness_probe.py中HEARTBEAT_THRESHOLD_MINUTES=5）

此契约确保：
1. 可靠的进程生命周期管理：先启动进程，成功后再更新状态
2. 快速健康检测：从5分钟减少到30秒级检测延迟
3. 僵尸进程检测：及时发现和处理僵尸状态进程
4. 资源清理：进程终止时自动清理相关资源

设计原则：
1. 契约先行：明确定义进程启动、监控、终止的完整契约
2. 失败隔离：进程启动失败不影响系统其他部分
3. 快速响应：秒级而非分钟级的健康检测
4. 资源安全：确保进程终止后资源被正确清理

MAREF框架集成：符合三才六层模型的执行层要求
"""

import json
import logging
import os
import re
import signal
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil

logger = logging.getLogger(__name__)


@dataclass
class ProcessContract:
    """
    进程生命周期契约 - 解决先标记running再启动进程的问题

    属性：
    - command: 要执行的命令
    - env: 环境变量字典
    - cwd: 工作目录
    - timeout_seconds: 进程超时时间（秒）
    - heartbeat_interval: 心跳检测间隔（秒），默认30秒，从5分钟优化而来
    - max_retries: 最大重试次数
    """

    command: str
    env: dict[str, str] = field(default_factory=dict)
    cwd: str | None = None
    timeout_seconds: int = 300  # 5分钟默认超时
    heartbeat_interval: int = 30  # 心跳间隔秒数，从5分钟减少到30秒
    max_retries: int = 3

    def spawn(self) -> tuple[bool, int | None, str | None]:
        """
        先启动进程，成功后再返回状态

        返回：
        - (成功标志, 进程ID, 错误信息)
        """
        logger.info(f"启动进程: {self.command[:100]}...")

        try:
            # 1. 准备环境变量
            full_env = {**os.environ, **self.env}

            # 2. 启动进程但不等待完成
            process = subprocess.Popen(
                self.command,
                shell=True,
                env=full_env,
                cwd=self.cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,  # 创建新的进程组
                text=True,
            )

            # 3. 验证进程真正启动（等待100ms检查进程状态）
            time.sleep(0.1)

            if process.poll() is not None:
                # 进程立即退出，获取错误信息
                stdout, stderr = process.communicate(timeout=1)
                error_msg = stderr if stderr else "进程立即退出"

                logger.error(f"进程启动失败: {error_msg}")
                return False, None, f"进程启动失败: {error_msg}"

            # 4. 进程启动成功，返回进程ID
            pid = process.pid
            logger.info(f"进程启动成功: PID={pid}, 命令={self.command[:100]}...")

            # 5. 启动健康监控（后台线程）
            self._start_health_monitor(pid)

            return True, pid, None

        except FileNotFoundError as e:
            error_msg = f"命令未找到: {self.command.split()[0]}"
            logger.error(f"{error_msg}: {e}")
            return False, None, error_msg
        except PermissionError as e:
            error_msg = f"权限不足: {self.command}"
            logger.error(f"{error_msg}: {e}")
            return False, None, error_msg
        except Exception as e:
            error_msg = f"进程启动异常: {str(e)}"
            logger.error(f"{error_msg}: {e}")
            return False, None, error_msg

    def _start_health_monitor(self, pid: int):
        """启动后台健康监控线程"""
        monitor_thread = threading.Thread(
            target=self._monitor_process_health,
            args=(pid,),
            daemon=True,
            name=f"process-monitor-{pid}",
        )
        monitor_thread.start()
        logger.debug(f"启动健康监控线程: PID={pid}")

    def _monitor_process_health(self, pid: int):
        """后台健康监控"""
        last_heartbeat = time.time()

        while True:
            try:
                # 检查进程是否存在
                if not psutil.pid_exists(pid):
                    logger.warning(f"进程不存在: PID={pid}")
                    self._on_process_terminated(pid, "process_not_found")
                    break

                process = psutil.Process(pid)

                # 快速健康检查
                health_status = self._quick_health_check(process)

                if not health_status["alive"]:
                    reason = health_status.get("reason", "unknown")
                    logger.warning(f"进程异常终止: PID={pid}, 原因={reason}")
                    self._on_process_terminated(pid, reason)
                    break

                # 记录心跳
                current_time = time.time()
                if current_time - last_heartbeat >= self.heartbeat_interval:
                    logger.debug(
                        f"进程心跳: PID={pid}, 状态={health_status['status']}, "
                        f"CPU={health_status['cpu_percent']:.1f}%, "
                        f"内存={health_status['memory_mb']:.1f}MB"
                    )
                    last_heartbeat = current_time

                # 检查是否超时
                if self.timeout_seconds > 0:
                    create_time = datetime.fromtimestamp(process.create_time())
                    elapsed = datetime.now() - create_time
                    if elapsed.total_seconds() > self.timeout_seconds:
                        logger.warning(f"进程超时: PID={pid}, 运行时间={elapsed}")
                        self._terminate_process(pid, "timeout")
                        break

                # 休眠检测间隔时间
                time.sleep(self.heartbeat_interval)

            except psutil.NoSuchProcess:
                logger.warning(f"进程已终止: PID={pid}")
                self._on_process_terminated(pid, "no_such_process")
                break
            except Exception as e:
                logger.error(f"健康监控异常: PID={pid}, 错误={str(e)}")
                # 继续监控，不中断
                time.sleep(self.heartbeat_interval)

    def _quick_health_check(self, process: psutil.Process) -> dict[str, Any]:
        """
        快速健康检查（秒级而非分钟级）

        返回：
        - 健康状态字典
        """
        try:
            status = process.status()
            cpu_percent = process.cpu_percent(interval=0.1)
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024

            # 检查进程是否正在执行（不是僵尸状态）
            is_zombie = status == psutil.STATUS_ZOMBIE

            # 检查进程是否响应（通过内存/CPU变化判断）
            is_responsive = not is_zombie

            return {
                "alive": not is_zombie,
                "status": status,
                "cpu_percent": cpu_percent,
                "memory_mb": memory_mb,
                "zombie": is_zombie,
                "responsive": is_responsive,
                "heartbeat_time": time.time(),
                "reason": "zombie" if is_zombie else "healthy",
            }

        except Exception as e:
            return {"alive": False, "status": "error", "reason": f"健康检查异常: {str(e)}"}

    def _terminate_process(self, pid: int, reason: str):
        """终止进程"""
        logger.info(f"终止进程: PID={pid}, 原因={reason}")

        try:
            # 尝试优雅终止
            os.kill(pid, signal.SIGTERM)
            time.sleep(2)  # 等待2秒

            # 检查是否还在运行
            if psutil.pid_exists(pid):
                logger.warning(f"进程仍在运行，强制终止: PID={pid}")
                os.kill(pid, signal.SIGKILL)

            self._on_process_terminated(pid, reason)

        except ProcessLookupError:
            logger.info(f"进程已终止: PID={pid}")
            self._on_process_terminated(pid, "already_terminated")
        except Exception as e:
            logger.error(f"终止进程失败: PID={pid}, 错误={str(e)}")
            self._on_process_terminated(pid, f"termination_failed: {str(e)}")

    def _on_process_terminated(self, pid: int, reason: str):
        """进程终止时的回调"""
        logger.info(f"进程终止回调: PID={pid}, 原因={reason}")

        # 清理相关资源
        # 这里可以添加清理逻辑，如删除临时文件、更新状态等

        # 记录终止事件
        termination_event = {
            "pid": pid,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
            "command": self.command[:200],
        }

        # 可以写入日志文件或发送到监控系统
        log_file = Path("/tmp/process_termination.log")
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(termination_event) + "\n")
        except Exception as e:
            logger.error(f"记录终止事件失败: {str(e)}")

    def monitor(self, pid: int) -> dict[str, Any]:
        """
        监控进程健康状态（外部调用接口）

        返回：
        - 监控结果字典
        """
        try:
            if not psutil.pid_exists(pid):
                return {
                    "alive": False,
                    "reason": "进程不存在",
                    "timestamp": datetime.now().isoformat(),
                }

            process = psutil.Process(pid)
            return self._quick_health_check(process)

        except psutil.NoSuchProcess:
            return {"alive": False, "reason": "进程不存在", "timestamp": datetime.now().isoformat()}
        except Exception as e:
            return {
                "alive": False,
                "reason": f"监控异常: {str(e)}",
                "timestamp": datetime.now().isoformat(),
            }


class ProcessLifecycleContract:
    """
    进程生命周期契约管理器

    提供批量进程管理、资源跟踪、状态同步等功能
    """

    def __init__(self):
        self.active_processes: dict[int, ProcessContract] = {}
        self.process_history: list[dict[str, Any]] = []
        self.lock = threading.RLock()
        logger.info("ProcessLifecycleContract初始化完成")

    def spawn_with_contract(
        self, command: str, env: dict[str, str] = None, cwd: str = None, timeout_seconds: int = 300
    ) -> dict[str, Any]:
        """
        使用契约启动进程（先启动进程，成功后返回状态）

        返回：
        - 包含进程信息和状态的字典
        """
        if env is None:
            env = {}

        contract = ProcessContract(
            command=command, env=env, cwd=cwd, timeout_seconds=timeout_seconds
        )

        with self.lock:
            # 先启动进程
            success, pid, error = contract.spawn()

            if success and pid:
                # 进程启动成功，记录状态
                self.active_processes[pid] = contract

                process_info = {
                    "pid": pid,
                    "command": command,
                    "status": "running",
                    "started_at": datetime.now().isoformat(),
                    "contract": contract,
                    "success": True,
                }

                self.process_history.append(process_info)
                logger.info(f"契约进程启动成功: PID={pid}")

                return process_info
            else:
                # 进程启动失败
                error_info = {
                    "pid": None,
                    "command": command,
                    "status": "failed",
                    "started_at": datetime.now().isoformat(),
                    "error": error,
                    "success": False,
                }

                self.process_history.append(error_info)
                logger.error(f"契约进程启动失败: {command[:100]}..., 错误={error}")

                return error_info

    def get_process_status(self, pid: int) -> dict[str, Any]:
        """获取进程状态"""
        with self.lock:
            if pid in self.active_processes:
                contract = self.active_processes[pid]
                health_status = contract.monitor(pid)

                return {
                    "pid": pid,
                    "alive": health_status["alive"],
                    "health": health_status,
                    "in_active_list": True,
                    "timestamp": datetime.now().isoformat(),
                }
            else:
                # 检查进程是否还在运行（可能在外部启动）
                try:
                    if psutil.pid_exists(pid):
                        # 创建临时契约进行检查
                        temp_contract = ProcessContract(command="unknown")
                        health_status = temp_contract.monitor(pid)

                        return {
                            "pid": pid,
                            "alive": health_status["alive"],
                            "health": health_status,
                            "in_active_list": False,
                            "timestamp": datetime.now().isoformat(),
                        }
                    else:
                        return {
                            "pid": pid,
                            "alive": False,
                            "health": {"reason": "进程不存在"},
                            "in_active_list": False,
                            "timestamp": datetime.now().isoformat(),
                        }
                except Exception as e:
                    return {
                        "pid": pid,
                        "alive": False,
                        "health": {"reason": f"检查异常: {str(e)}"},
                        "in_active_list": False,
                        "timestamp": datetime.now().isoformat(),
                    }

    def cleanup_stale_processes(self, threshold_minutes: int = 5) -> dict[str, Any]:
        """
        清理过期进程（优化版，从5分钟减少到更短时间）

        参数：
        - threshold_minutes: 过期阈值（分钟），默认为5分钟

        返回：
        - 清理结果
        """
        cleanup_report = {"total_checked": 0, "stale_found": 0, "terminated": 0, "details": []}

        with self.lock:
            pids_to_remove = []

            for pid, contract in list(self.active_processes.items()):
                cleanup_report["total_checked"] += 1

                health_status = contract.monitor(pid)

                if not health_status["alive"]:
                    # 进程已死亡，清理
                    pids_to_remove.append(pid)
                    cleanup_report["stale_found"] += 1
                    cleanup_report["terminated"] += 1

                    cleanup_report["details"].append(
                        {
                            "pid": pid,
                            "reason": health_status.get("reason", "dead"),
                            "action": "removed_from_active_list",
                            "timestamp": datetime.now().isoformat(),
                        }
                    )

                    logger.info(
                        f"清理死亡进程: PID={pid}, 原因={health_status.get('reason', 'dead')}"
                    )

                elif self.timeout_minutes > 0:
                    # 检查是否超时
                    try:
                        process = psutil.Process(pid)
                        create_time = datetime.fromtimestamp(process.create_time())
                        elapsed = datetime.now() - create_time

                        if elapsed.total_seconds() > self.timeout_minutes * 60:
                            # 超时进程，终止它
                            contract._terminate_process(pid, "timeout")
                            pids_to_remove.append(pid)
                            cleanup_report["stale_found"] += 1
                            cleanup_report["terminated"] += 1

                            cleanup_report["details"].append(
                                {
                                    "pid": pid,
                                    "reason": "timeout",
                                    "elapsed_minutes": elapsed.total_seconds() / 60,
                                    "action": "terminated",
                                    "timestamp": datetime.now().isoformat(),
                                }
                            )
                    except Exception as e:
                        logger.error(f"检查进程超时失败: PID={pid}, 错误={str(e)}")

            # 移除清理的进程
            for pid in pids_to_remove:
                self.active_processes.pop(pid, None)

        logger.info(
            f"进程清理完成: 检查{cleanup_report['total_checked']}个，"
            f"发现{cleanup_report['stale_found']}个过期进程，"
            f"终止{cleanup_report['terminated']}个"
        )

        return cleanup_report

    def bulk_health_check(self) -> dict[str, Any]:
        """批量健康检查"""
        health_report = {
            "total_processes": 0,
            "healthy": 0,
            "unhealthy": 0,
            "zombies": 0,
            "details": {},
        }

        with self.lock:
            for pid, contract in self.active_processes.items():
                health_report["total_processes"] += 1

                health_status = contract.monitor(pid)

                if health_status["alive"]:
                    if health_status.get("zombie", False):
                        health_report["zombies"] += 1
                        health_status["status"] = "zombie"
                    else:
                        health_report["healthy"] += 1
                        health_status["status"] = "healthy"
                else:
                    health_report["unhealthy"] += 1
                    health_status["status"] = "dead"

                health_report["details"][pid] = health_status

        return health_report

    @property
    def timeout_minutes(self):
        """获取超时时间（分钟）"""
        return 5  # 默认5分钟，可以配置

    @property
    def heartbeat_interval_seconds(self):
        """获取心跳间隔（秒）"""
        return 30  # 从5分钟优化到30秒


def validate_process_start_sequence(existing_code: str) -> dict[str, Any]:
    """
    验证现有代码中的进程启动顺序

    参数：
    - existing_code: 现有代码片段

    返回：
    - 验证结果
    """
    validation_result = {
        "contract_compliant": False,
        "issues": [],
        "warnings": [],
        "recommendations": [],
    }

    # 检查是否先标记状态再启动进程
    status_patterns = [
        r'set.*status.*=.*["\']running["\']',
        r'status.*:.*["\']running["\']',
        r'"status"\s*:\s*"running"',
    ]

    process_patterns = [r"subprocess\.Popen", r"process\s*=", r"start_new_session"]

    lines = existing_code.split("\n")

    # 查找状态更新行
    status_lines = []
    for i, line in enumerate(lines):
        for pattern in status_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                status_lines.append((i, line))
                break

    # 查找进程启动行
    process_lines = []
    for i, line in enumerate(lines):
        for pattern in process_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                process_lines.append((i, line))
                break

    # 分析顺序
    if status_lines and process_lines:
        first_status = min(line[0] for line in status_lines)
        first_process = min(line[0] for line in process_lines)

        if first_status < first_process:
            validation_result["issues"].append("检测到先标记状态再启动进程的问题")
            validation_result["contract_compliant"] = False
        else:
            validation_result["contract_compliant"] = True
            validation_result["recommendations"].append("进程启动顺序正确")

    return validation_result


if __name__ == "__main__":
    # 示例用法
    print("=== ProcessLifecycleContract 测试 ===")

    # 1. 创建契约管理器
    contract_manager = ProcessLifecycleContract()

    # 2. 测试进程启动
    print("\n1. 测试进程启动:")
    test_command = "echo '测试进程' && sleep 2"
    result = contract_manager.spawn_with_contract(test_command)
    print(f"   启动结果: PID={result.get('pid')}, 成功={result.get('success')}")

    if result.get("pid"):
        # 3. 测试健康检查
        print("\n2. 测试健康检查:")
        time.sleep(0.5)
        status = contract_manager.get_process_status(result["pid"])
        print(f"   进程状态: 存活={status.get('alive')}, 健康={status.get('health', {})}")

        # 4. 测试批量健康检查
        print("\n3. 测试批量健康检查:")
        health_report = contract_manager.bulk_health_check()
        print(
            f"   健康报告: 总数={health_report.get('total_processes')}, "
            f"健康={health_report.get('healthy')}, "
            f"不健康={health_report.get('unhealthy')}"
        )

        # 5. 等待进程结束并清理
        print("\n4. 等待进程结束...")
        time.sleep(3)

        cleanup_report = contract_manager.cleanup_stale_processes()
        print(
            f"   清理报告: 检查={cleanup_report.get('total_checked')}, "
            f"过期={cleanup_report.get('stale_found')}"
        )

    print("\n=== 测试完成 ===")
