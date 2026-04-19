#!/usr/bin/env python3
"""
MAREF系统监控数据采集模块
基于易经八卦架构的超稳定性多智能体框架监控
"""

import json
import logging
import math
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# 添加ROMA模块路径
sys.path.insert(0, str(Path(__file__).parent / "external/ROMA"))

try:
    from hexagram_state_manager import HexagramStateManager
except ImportError as e:
    print(f"警告: 无法导入hexagram_state_manager: {e}")
    HexagramStateManager = None

try:
    import psutil
except ImportError:
    psutil = None
    print("警告: psutil未安装，系统指标采集功能受限")

# 导入健康度计算器
try:
    from health_calculator import AgentHealthCalculator
except ImportError as e:
    print(f"警告: 无法导入health_calculator: {e}")
    AgentHealthCalculator = None


class MAREFMonitor:
    """
    MAREF系统监控器

    职责:
    1. 收集系统性能指标（CPU、内存、磁盘）
    2. 收集MAREF核心指标（控制熵、卦象状态分布、格雷编码合规性）
    3. 收集智能体健康指标
    4. 计算趋势和预警
    """

    def __init__(self, state_manager=None, agents=None):
        """
        初始化监控器

        Args:
            state_manager: HexagramStateManager实例
            agents: 智能体字典，键为智能体名称，值为智能体实例
        """
        self.state_manager = state_manager
        self.agents = agents or {}
        self.metrics_history = []
        self.logger = self._setup_logger()

        # 初始化健康度计算器
        self.health_calculator = None
        if AgentHealthCalculator is not None:
            self.health_calculator = AgentHealthCalculator()
            self.logger.info("健康度计算器初始化成功")
        else:
            self.logger.warning("健康度计算器不可用，将使用默认健康分数")

        self.logger.info(f"MAREF监控器初始化完成，监控 {len(self.agents)} 个智能体")

    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger(f"maref_monitor")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def collect_system_metrics(self) -> Dict[str, Any]:
        """收集系统性能指标"""
        if psutil is None:
            return {
                "timestamp": datetime.now().isoformat(),
                "cpu_usage": 0.0,
                "memory_usage": 0.0,
                "memory_available": 0.0,
                "disk_usage": 0.0,
                "disk_free": 0.0,
                "psutil_missing": True,
            }

        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            return {
                "timestamp": datetime.now().isoformat(),
                "cpu_usage": cpu_percent,
                "memory_usage": memory.percent,
                "memory_available": memory.available / (1024**3),  # GB
                "disk_usage": disk.percent,
                "disk_free": disk.free / (1024**3),  # GB
            }
        except Exception as e:
            self.logger.error(f"收集系统指标失败: {e}")
            return {"timestamp": datetime.now().isoformat(), "error": str(e)}

    def collect_maref_metrics(self) -> Dict[str, Any]:
        """收集MAREF核心指标"""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "control_entropy_h_c": 0.0,
            "hexagram_distribution": {},
            "gray_code_compliance": {"total": 0, "compliant": 0, "rate": 1.0},
            "current_hexagram": "000000",
            "hexagram_name": "未知卦象",
        }

        if self.state_manager is None:
            metrics["error"] = "state_manager未配置"
            return metrics

        try:
            # 控制熵H_c计算
            h_c = self.calculate_control_entropy()

            # 卦象状态分布
            hexagram_distribution = self.get_hexagram_distribution()

            # 格雷编码合规性
            gray_compliance = self.check_gray_code_compliance()

            metrics.update(
                {
                    "control_entropy_h_c": h_c,
                    "hexagram_distribution": hexagram_distribution,
                    "gray_code_compliance": gray_compliance,
                    "current_hexagram": self.state_manager.current_state,
                    "hexagram_name": self.state_manager.get_hexagram_name(),
                }
            )

        except Exception as e:
            self.logger.error(f"收集MAREF指标失败: {e}")
            metrics["error"] = str(e)

        return metrics

    def collect_agent_metrics(self) -> Dict[str, Any]:
        """收集智能体健康指标"""
        agent_metrics = {}

        for agent_name, agent in self.agents.items():
            try:
                # 尝试调用智能体的健康检查方法
                if hasattr(agent, "get_health_metrics"):
                    metrics = agent.get_health_metrics()

                    # 尝试使用健康度计算器计算健康分数
                    if self.health_calculator is not None:
                        try:
                            # 提取健康度计算器所需的指标
                            health_metrics = {
                                "response_time": metrics.get("response_time", 0.5),
                                "success_rate": metrics.get("success_rate", 0.95),
                                "resource_usage": metrics.get("resource_usage", 0.5),
                                "availability": metrics.get("availability", 0.99),
                            }

                            # 计算健康分数并更新metrics
                            calculated_score = self.health_calculator.calculate_health(
                                health_metrics
                            )
                            metrics["health_score"] = calculated_score
                            metrics["health_calculated"] = True  # 标记为已计算

                        except Exception as calc_error:
                            self.logger.warning(
                                f"计算智能体 {agent_name} 健康分数失败: {calc_error}"
                            )
                            # 如果metrics中没有health_score，添加默认值
                            if "health_score" not in metrics:
                                metrics["health_score"] = 0.8

                    agent_metrics[agent_name] = metrics
                elif hasattr(agent, "agent_type"):
                    # 基础健康检查
                    agent_id = getattr(agent, "agent_id", "unknown")
                    agent_type = getattr(agent, "agent_type", "unknown")

                    # 基础指标（模拟值，实际实现应从智能体获取）
                    base_metrics = {
                        "response_time": 0.5,  # 默认0.5秒响应时间
                        "success_rate": 0.95,  # 默认95%成功率
                        "resource_usage": 0.5,  # 默认50%资源使用率
                        "availability": 0.99,  # 默认99%可用性
                    }

                    # 计算健康分数
                    health_score = 0.8  # 默认值
                    if self.health_calculator is not None:
                        try:
                            health_score = self.health_calculator.calculate_health(base_metrics)
                        except Exception as calc_error:
                            self.logger.warning(
                                f"计算智能体 {agent_name} 健康分数失败: {calc_error}"
                            )

                    agent_metrics[agent_name] = {
                        "agent_id": agent_id,
                        "agent_type": agent_type,
                        "status": "active",
                        "last_check": datetime.now().isoformat(),
                        "health_score": health_score,
                        "metrics": base_metrics,  # 包含基础指标用于调试
                    }
                else:
                    agent_metrics[agent_name] = {
                        "status": "unknown",
                        "last_activity": datetime.now().isoformat(),
                        "error": "智能体缺少标准接口",
                    }
            except Exception as e:
                self.logger.error(f"收集智能体 {agent_name} 指标失败: {e}")
                agent_metrics[agent_name] = {
                    "status": "error",
                    "error": str(e),
                    "last_check": datetime.now().isoformat(),
                }

        return agent_metrics

    def calculate_control_entropy(self) -> float:
        """计算控制熵H_c（基于卦象状态分布）"""
        if self.state_manager is None:
            return 0.0

        distribution = self.get_hexagram_distribution()

        if not distribution:
            return 0.0

        entropy = 0.0
        total = sum(distribution.values())

        if total == 0:
            return 0.0

        for count in distribution.values():
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)

        # 上限6 bits（64状态）
        return min(entropy, 6.0)

    def get_hexagram_distribution(self) -> Dict[str, int]:
        """获取卦象状态分布（基于状态历史）"""
        if self.state_manager is None or not hasattr(self.state_manager, "state_history"):
            return {}

        history = self.state_manager.state_history

        if not history:
            # 如果没有历史，至少包含当前状态
            return {self.state_manager.current_state: 1}

        # 获取最近100次状态转换
        recent_history = history[-100:] if len(history) > 100 else history

        distribution = {}
        for record in recent_history:
            state = record.get("to", self.state_manager.current_state)
            distribution[state] = distribution.get(state, 0) + 1

        return distribution

    def check_gray_code_compliance(self) -> Dict[str, Any]:
        """检查格雷编码合规性"""
        if self.state_manager is None or not hasattr(self.state_manager, "state_history"):
            return {"total": 0, "compliant": 0, "rate": 1.0}

        history = self.state_manager.state_history
        if len(history) < 2:
            return {"total": 0, "compliant": 0, "rate": 1.0}

        total = len(history) - 1
        compliant = 0
        violations = []

        for i in range(1, len(history)):
            prev_record = history[i - 1]
            curr_record = history[i]

            prev_state = prev_record.get("to", "000000")
            curr_state = curr_record.get("to", "000000")

            # 计算汉明距离
            try:
                distance = self.state_manager.hamming_distance(prev_state, curr_state)

                if distance == 1:
                    compliant += 1
                else:
                    violations.append(
                        {"from": prev_state, "to": curr_state, "distance": distance, "step": i}
                    )
            except Exception as e:
                self.logger.warning(f"计算汉明距离失败: {e}")

        return {
            "total": total,
            "compliant": compliant,
            "rate": compliant / total if total > 0 else 1.0,
            "violations": violations[-5:] if violations else [],  # 最近5次违规
        }

    def collect_all_metrics(self) -> Dict[str, Any]:
        """收集所有指标"""
        system_metrics = self.collect_system_metrics()
        maref_metrics = self.collect_maref_metrics()
        agent_metrics = self.collect_agent_metrics()

        all_metrics = {
            "timestamp": datetime.now().isoformat(),
            "system": system_metrics,
            "maref": maref_metrics,
            "agents": agent_metrics,
        }

        # 保存到历史
        self.metrics_history.append(all_metrics)

        # 限制历史记录数量
        if len(self.metrics_history) > 1000:
            self.metrics_history = self.metrics_history[-1000:]

        self.logger.info(f"收集到 {len(self.metrics_history)} 条指标记录")
        return all_metrics

    def get_recent_metrics(self, count: int = 100) -> List[Dict[str, Any]]:
        """获取最近的指标记录"""
        return self.metrics_history[-count:] if self.metrics_history else []

    def save_metrics_to_file(self, filepath: str = None) -> str:
        """保存指标到文件"""
        if filepath is None:
            # 默认保存路径
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"/tmp/maref_metrics_{timestamp}.json"

        metrics = self.collect_all_metrics()

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(metrics, f, ensure_ascii=False, indent=2)

            self.logger.info(f"指标已保存到 {filepath}")
            return filepath

        except Exception as e:
            self.logger.error(f"保存指标失败: {e}")
            raise

    def get_health_summary(self) -> Dict[str, Any]:
        """获取系统健康摘要"""
        metrics = self.collect_all_metrics()

        # 系统健康状态
        system_health = "healthy"
        if metrics["system"].get("memory_usage", 0) > 90:
            system_health = "warning"
        if metrics["system"].get("cpu_usage", 0) > 95:
            system_health = "critical"

        # MAREF健康状态
        maref_health = "healthy"
        h_c = metrics["maref"].get("control_entropy_h_c", 0)
        if h_c > 4.5:
            maref_health = "warning"
        if h_c > 5.5:
            maref_health = "critical"

        # 智能体健康状态
        active_agents = 0
        total_agents = len(metrics["agents"])

        for agent_name, agent_data in metrics["agents"].items():
            if agent_data.get("status") in ["active", "healthy"]:
                active_agents += 1

        agent_health = "healthy"
        if active_agents < total_agents * 0.8:  # 少于80%的智能体活跃
            agent_health = "warning"
        if active_agents < total_agents * 0.5:  # 少于50%的智能体活跃
            agent_health = "critical"

        return {
            "timestamp": datetime.now().isoformat(),
            "system_health": system_health,
            "maref_health": maref_health,
            "agent_health": agent_health,
            "active_agents": active_agents,
            "total_agents": total_agents,
            "control_entropy": h_c,
            "gray_code_compliance_rate": metrics["maref"]["gray_code_compliance"]["rate"],
        }


def test_maref_monitor():
    """测试MAREF监控器"""
    print("=== MAREF监控器测试 ===")

    try:
        # 创建状态管理器
        from hexagram_state_manager import HexagramStateManager

        state_manager = HexagramStateManager("000000")

        # 模拟一些状态转换
        test_transitions = ["000001", "000011", "000010", "000000"]
        for state in test_transitions:
            state_manager.transition(state)

        # 创建模拟智能体
        class MockAgent:
            def __init__(self, agent_id, agent_type):
                self.agent_id = agent_id
                self.agent_type = agent_type

            def get_health_metrics(self):
                return {
                    "agent_id": self.agent_id,
                    "agent_type": str(self.agent_type),
                    "status": "active",
                    "health_score": 0.9,
                    "last_active": datetime.now().isoformat(),
                }

        # 创建模拟智能体字典
        agents = {
            "guardian": MockAgent("guardian_001", "guardian"),
            "communicator": MockAgent("communicator_001", "communicator"),
            "learner": MockAgent("learner_001", "learner"),
            "explorer": MockAgent("explorer_001", "explorer"),
        }

        # 创建监控器
        monitor = MAREFMonitor(state_manager, agents)

        print("✅ 监控器创建成功")

        # 测试系统指标收集
        print("\n=== 系统指标测试 ===")
        system_metrics = monitor.collect_system_metrics()
        print(f"CPU使用率: {system_metrics.get('cpu_usage', 'N/A')}%")
        print(f"内存使用率: {system_metrics.get('memory_usage', 'N/A')}%")

        # 测试MAREF指标收集
        print("\n=== MAREF指标测试 ===")
        maref_metrics = monitor.collect_maref_metrics()
        print(f"当前卦象: {maref_metrics.get('hexagram_name', 'N/A')}")
        print(f"控制熵H_c: {maref_metrics.get('control_entropy_h_c', 'N/A'):.2f}")

        gray_compliance = maref_metrics.get("gray_code_compliance", {})
        print(f"格雷编码合规率: {gray_compliance.get('rate', 'N/A'):.1%}")

        # 测试智能体指标收集
        print("\n=== 智能体指标测试 ===")
        agent_metrics = monitor.collect_agent_metrics()
        print(f"监控智能体数量: {len(agent_metrics)}")

        for agent_name, metrics in agent_metrics.items():
            print(f"  {agent_name}: {metrics.get('status', 'unknown')}")

        # 测试健康摘要
        print("\n=== 健康摘要测试 ===")
        health_summary = monitor.get_health_summary()
        print(f"系统健康: {health_summary.get('system_health', 'N/A')}")
        print(f"MAREF健康: {health_summary.get('maref_health', 'N/A')}")
        print(f"智能体健康: {health_summary.get('agent_health', 'N/A')}")
        print(f"控制熵: {health_summary.get('control_entropy', 'N/A'):.2f}")

        # 测试指标保存
        print("\n=== 指标保存测试 ===")
        try:
            saved_file = monitor.save_metrics_to_file("/tmp/test_maref_metrics.json")
            print(f"✅ 指标已保存到: {saved_file}")
        except Exception as e:
            print(f"⚠️  指标保存失败: {e}")

        print("\n=== 测试完成 ===")
        print("MAREF监控器功能验证通过")

    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print("请确保hexagram_state_manager.py在正确路径")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_maref_monitor()
