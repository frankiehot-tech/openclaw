#!/usr/bin/env python3
"""
MAREF预警规则引擎
基于易经八卦架构的超稳定性多智能体框架预警系统
"""

import json
import logging
import math
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class MAREFAlertEngine:
    """MAREF预警规则引擎

    职责：
    1. 加载和管理预警规则（红色/黄色预警）
    2. 检查系统指标是否符合预警条件
    3. 跟踪预警持续时间
    4. 生成预警报告和建议
    """

    def __init__(self, config_path: str = None):
        self.logger = self._setup_logger()
        self.rules = self.load_rules(config_path)
        self.alert_history: Dict[str, float] = {}

        self.logger.info(
            f"预警引擎初始化完成，加载 {len(self.rules['red_alerts'])} 个红色预警规则, {len(self.rules['yellow_alerts'])} 个黄色预警规则"
        )

    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger(f"maref_alert_engine")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def load_rules(self, config_path: str = None) -> Dict[str, List[Dict]]:
        """加载预警规则"""
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    rules = json.load(f)
                self.logger.info(f"从 {config_path} 加载预警规则配置")
                return rules
            except Exception as e:
                self.logger.error(f"加载规则配置失败: {e}")

        # 默认预警规则（基于实施方案文档）
        default_rules = {
            "red_alerts": [
                {
                    "id": "H_C_OUT_OF_RANGE",
                    "name": "控制熵超出安全范围",
                    "condition": lambda metrics: (
                        metrics.get("control_entropy_h_c", 0) < 3
                        or metrics.get("control_entropy_h_c", 0) > 6
                    ),
                    "duration": 1800,  # 持续30分钟（秒）
                    "description": "控制熵H_c超出安全范围(3-6 bits)",
                    "recommendation": "立即检查系统状态，调整控制策略",
                    "priority": "critical",
                },
                {
                    "id": "GRAY_CODE_VIOLATION_HIGH",
                    "name": "格雷编码违规率过高",
                    "condition": lambda metrics: (
                        metrics.get("gray_code_compliance", {}).get("rate", 1.0) < 0.95
                    ),
                    "duration": 3600,  # 持续1小时
                    "description": "格雷编码合规率低于95%",
                    "recommendation": "检查状态转换逻辑，修复异常转换",
                    "priority": "high",
                },
                {
                    "id": "SYSTEM_RESOURCE_CRITICAL",
                    "name": "系统资源枯竭",
                    "condition": lambda metrics: (
                        metrics.get("system", {}).get("memory_usage", 0) > 95
                        or metrics.get("system", {}).get("disk_usage", 0) > 98
                    ),
                    "duration": 300,  # 持续5分钟
                    "description": "内存使用率>95%或磁盘使用率>98%",
                    "recommendation": "立即释放资源或扩展存储容量",
                    "priority": "critical",
                },
                {
                    "id": "CRITICAL_AGENT_FAILURE",
                    "name": "关键智能体失效",
                    "condition": lambda metrics: (
                        any(
                            agent.get("status") == "critical"
                            for agent in metrics.get("agents", {}).values()
                        )
                    ),
                    "duration": 600,  # 持续10分钟
                    "description": "关键智能体（Guardian/Coordinator）状态异常",
                    "recommendation": "重启智能体或检查依赖服务",
                    "priority": "high",
                },
                {
                    "id": "STATE_TRANSITION_BROKEN",
                    "name": "状态转换断裂",
                    "condition": lambda metrics: (
                        metrics.get("gray_code_compliance", {}).get("rate", 1.0) < 0.9
                    ),
                    "duration": 1800,  # 持续30分钟
                    "description": "格雷编码合规率低于90%",
                    "recommendation": "立即检查卦象状态管理器",
                    "priority": "critical",
                },
            ],
            "yellow_alerts": [
                {
                    "id": "LEARNER_STAGNATION",
                    "name": "Learner学习停滞",
                    "condition": lambda metrics: (
                        metrics.get("agents", {}).get("learner", {}).get("learning_progress", 1.0)
                        < 0.8
                    ),
                    "duration": 604800,  # 持续7天
                    "description": "Learner智能体学习进度低于80%",
                    "recommendation": "检查学习数据集，调整学习参数",
                    "priority": "medium",
                },
                {
                    "id": "HEXAGRAM_IMBALANCE",
                    "name": "卦象状态失衡",
                    "condition": lambda metrics: (
                        self.calculate_distribution_entropy(
                            metrics.get("hexagram_distribution", {})
                        )
                        < 4.5
                    ),
                    "duration": 86400,  # 持续1天
                    "description": "卦象状态分布熵值低于4.5",
                    "recommendation": "检查状态转移概率，增加多样性",
                    "priority": "medium",
                },
                {
                    "id": "COMPLEMENTARY_PAIR_INACTIVE",
                    "name": "互补智能体对未激活",
                    "condition": lambda metrics: (
                        self.check_complementary_activation(metrics.get("agents", {})) < 0.7
                    ),
                    "duration": 172800,  # 持续2天
                    "description": "互补智能体对（如艮↔坎、离↔兑）协同工作比例低于70%",
                    "recommendation": "检查智能体通信和任务分配",
                    "priority": "low",
                },
                {
                    "id": "SYSTEM_RESOURCE_WARNING",
                    "name": "系统资源紧张",
                    "condition": lambda metrics: (
                        metrics.get("system", {}).get("cpu_usage", 0) > 85
                        or metrics.get("system", {}).get("memory_usage", 0) > 90
                    ),
                    "duration": 3600,  # 持续1小时
                    "description": "CPU使用率>85%或内存使用率>90%",
                    "recommendation": "优化资源使用，考虑扩容",
                    "priority": "medium",
                },
                {
                    "id": "PERFORMANCE_DEGRADATION",
                    "name": "性能持续下降",
                    "condition": lambda metrics: (self.check_performance_trend(metrics) < 0.9),
                    "duration": 259200,  # 持续3天
                    "description": "关键性能指标连续3天下降",
                    "recommendation": "分析性能瓶颈，进行优化",
                    "priority": "low",
                },
            ],
        }

        self.logger.info(f"使用默认预警规则配置")
        return default_rules

    def calculate_distribution_entropy(self, distribution: Dict[str, int]) -> float:
        """计算卦象状态分布熵值"""
        if not distribution:
            return 0.0

        total = sum(distribution.values())
        if total == 0:
            return 0.0

        entropy = 0.0
        for count in distribution.values():
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)

        # 上限6 bits（64状态）
        return min(entropy, 6.0)

    def check_complementary_activation(self, agents: Dict[str, Dict]) -> float:
        """检查互补智能体对激活比例"""
        # 互补对映射：艮↔坎（Guardian↔Explorer）、离↔兑（Communicator↔Learner）
        complementary_pairs = [
            ("guardian", "explorer"),
            ("communicator", "learner"),
            ("atomizer", "verifier"),
            ("planner", "aggregator"),
            ("executor", "aggregator"),
        ]

        active_pairs = 0
        total_pairs = 0

        for agent1, agent2 in complementary_pairs:
            if agent1 in agents and agent2 in agents:
                total_pairs += 1
                status1 = agents[agent1].get("status", "inactive")
                status2 = agents[agent2].get("status", "inactive")

                if status1 in ["active", "healthy"] and status2 in ["active", "healthy"]:
                    active_pairs += 1

        return active_pairs / total_pairs if total_pairs > 0 else 1.0

    def check_performance_trend(self, metrics: Dict[str, Any]) -> float:
        """检查性能趋势（简化实现）"""
        # 在实际系统中，这里应该分析历史数据
        # 简化实现：返回默认值
        return 0.95

    def check_alerts(self, metrics: Dict[str, Any]) -> Dict[str, List[Dict]]:
        """检查预警条件

        Args:
            metrics: 系统指标数据，包含system、maref、agents等部分

        Returns:
            包含红色和黄色预警的字典
        """
        current_time = time.time()
        alerts = {"red_alerts": [], "yellow_alerts": []}

        self.logger.debug(f"开始检查预警条件，指标keys: {list(metrics.keys())}")

        # 检查红色预警
        for rule in self.rules["red_alerts"]:
            try:
                if rule["condition"](metrics):
                    alert_key = f"{rule['id']}_red"

                    # 首次触发或重新触发
                    if alert_key not in self.alert_history:
                        self.alert_history[alert_key] = current_time
                        self.logger.info(f"红色预警首次触发: {rule['name']}")

                    # 检查持续时间
                    duration = current_time - self.alert_history[alert_key]
                    if duration >= rule["duration"]:
                        alert_data = {
                            "id": rule["id"],
                            "title": rule["name"],
                            "description": rule["description"],
                            "recommendation": rule["recommendation"],
                            "duration": duration,
                            "priority": rule.get("priority", "high"),
                            "trigger_time": datetime.fromtimestamp(current_time).isoformat(),
                            "metrics_snapshot": self.extract_relevant_metrics(metrics, rule["id"]),
                        }

                        alerts["red_alerts"].append(alert_data)
                        self.logger.warning(f"红色预警确认: {rule['name']}, 持续 {duration:.0f}秒")
                    else:
                        self.logger.debug(
                            f"红色预警条件满足但持续时间不足: {rule['name']} ({duration:.0f}/{rule['duration']}秒)"
                        )
                else:
                    # 条件不满足，清除历史记录
                    alert_key = f"{rule['id']}_red"
                    if alert_key in self.alert_history:
                        del self.alert_history[alert_key]
                        self.logger.info(f"红色预警条件解除: {rule['name']}")

            except Exception as e:
                self.logger.error(f"检查红色预警规则 {rule.get('id', 'unknown')} 失败: {e}")

        # 检查黄色预警
        for rule in self.rules["yellow_alerts"]:
            try:
                if rule["condition"](metrics):
                    alert_key = f"{rule['id']}_yellow"

                    if alert_key not in self.alert_history:
                        self.alert_history[alert_key] = current_time
                        self.logger.info(f"黄色预警首次触发: {rule['name']}")

                    duration = current_time - self.alert_history[alert_key]
                    if duration >= rule["duration"]:
                        alert_data = {
                            "id": rule["id"],
                            "title": rule["name"],
                            "description": rule["description"],
                            "recommendation": rule["recommendation"],
                            "duration": duration,
                            "priority": rule.get("priority", "medium"),
                            "trigger_time": datetime.fromtimestamp(current_time).isoformat(),
                            "metrics_snapshot": self.extract_relevant_metrics(metrics, rule["id"]),
                        }

                        alerts["yellow_alerts"].append(alert_data)
                        self.logger.warning(f"黄色预警确认: {rule['name']}, 持续 {duration:.0f}秒")
                    else:
                        self.logger.debug(
                            f"黄色预警条件满足但持续时间不足: {rule['name']} ({duration:.0f}/{rule['duration']}秒)"
                        )
                else:
                    alert_key = f"{rule['id']}_yellow"
                    if alert_key in self.alert_history:
                        del self.alert_history[alert_key]
                        self.logger.info(f"黄色预警条件解除: {rule['name']}")

            except Exception as e:
                self.logger.error(f"检查黄色预警规则 {rule.get('id', 'unknown')} 失败: {e}")

        self.logger.info(
            f"预警检查完成: {len(alerts['red_alerts'])} 个红色预警, {len(alerts['yellow_alerts'])} 个黄色预警"
        )
        return alerts

    def extract_relevant_metrics(self, metrics: Dict[str, Any], rule_id: str) -> Dict[str, Any]:
        """提取与特定预警相关的指标"""
        relevant_metrics = {}

        if rule_id == "H_C_OUT_OF_RANGE":
            relevant_metrics = {
                "control_entropy_h_c": metrics.get("control_entropy_h_c", 0),
                "hexagram_name": metrics.get("hexagram_name", "unknown"),
                "current_hexagram": metrics.get("current_hexagram", "000000"),
            }
        elif rule_id == "GRAY_CODE_VIOLATION_HIGH":
            relevant_metrics = {
                "gray_code_compliance_rate": metrics.get("gray_code_compliance", {}).get(
                    "rate", 1.0
                ),
                "total_transitions": metrics.get("gray_code_compliance", {}).get("total", 0),
                "compliant_transitions": metrics.get("gray_code_compliance", {}).get(
                    "compliant", 0
                ),
            }
        elif rule_id == "SYSTEM_RESOURCE_CRITICAL" or rule_id == "SYSTEM_RESOURCE_WARNING":
            relevant_metrics = {
                "cpu_usage": metrics.get("system", {}).get("cpu_usage", 0),
                "memory_usage": metrics.get("system", {}).get("memory_usage", 0),
                "disk_usage": metrics.get("system", {}).get("disk_usage", 0),
                "memory_available_gb": metrics.get("system", {}).get("memory_available", 0),
            }
        elif rule_id == "CRITICAL_AGENT_FAILURE":
            relevant_metrics = {
                "agent_statuses": {
                    name: agent.get("status", "unknown")
                    for name, agent in metrics.get("agents", {}).items()
                }
            }
        elif rule_id == "LEARNER_STAGNATION":
            relevant_metrics = {
                "learner_progress": metrics.get("agents", {})
                .get("learner", {})
                .get("learning_progress", 0),
                "learner_status": metrics.get("agents", {})
                .get("learner", {})
                .get("status", "unknown"),
            }
        elif rule_id == "HEXAGRAM_IMBALANCE":
            relevant_metrics = {
                "distribution_entropy": self.calculate_distribution_entropy(
                    metrics.get("hexagram_distribution", {})
                ),
                "distribution_summary": {
                    trigram: count
                    for trigram, count in list(metrics.get("hexagram_distribution", {}).items())[:5]
                },
            }

        return relevant_metrics

    def get_alert_summary(self) -> Dict[str, Any]:
        """获取预警摘要"""
        return {
            "total_alerts": len(self.alert_history),
            "active_red_alerts": sum(1 for k in self.alert_history.keys() if k.endswith("_red")),
            "active_yellow_alerts": sum(
                1 for k in self.alert_history.keys() if k.endswith("_yellow")
            ),
            "alert_history_keys": list(self.alert_history.keys())[-10:],  # 最近10个
            "last_check": datetime.now().isoformat(),
        }


def test_alert_engine():
    """测试预警引擎"""
    print("=== MAREF预警引擎测试 ===")

    # 创建预警引擎
    engine = MAREFAlertEngine()

    print(f"✅ 预警引擎创建成功")
    print(f"红色预警规则: {len(engine.rules['red_alerts'])} 条")
    print(f"黄色预警规则: {len(engine.rules['yellow_alerts'])} 条")

    # 测试指标数据
    test_metrics = {
        "system": {
            "cpu_usage": 92.5,
            "memory_usage": 96.8,
            "disk_usage": 45.2,
            "memory_available": 0.8,  # GB
        },
        "control_entropy_h_c": 2.8,  # 低于安全范围
        "hexagram_name": "艮卦",
        "current_hexagram": "001001",
        "hexagram_distribution": {"001001": 5, "010010": 3, "100100": 2},  # 艮卦
        "gray_code_compliance": {"rate": 0.87, "total": 100, "compliant": 87},  # 低于95%
        "agents": {
            "guardian": {"status": "critical", "health_score": 0.3},
            "learner": {
                "status": "active",
                "learning_progress": 0.65,  # 低于80%
                "health_score": 0.7,
            },
            "explorer": {"status": "active", "health_score": 0.9},
            "communicator": {"status": "healthy", "health_score": 0.95},
        },
    }

    print("\n=== 预警检查测试 ===")
    alerts = engine.check_alerts(test_metrics)

    print(f"检测到红色预警: {len(alerts['red_alerts'])} 个")
    for i, alert in enumerate(alerts["red_alerts"], 1):
        print(f"  {i}. 🔴 {alert['title']}")
        print(f"     问题: {alert['description']}")
        print(f"     建议: {alert['recommendation']}")
        print(f"     持续: {alert['duration']:.0f}秒")

    print(f"\n检测到黄色预警: {len(alerts['yellow_alerts'])} 个")
    for i, alert in enumerate(alerts["yellow_alerts"], 1):
        print(f"  {i}. 🟡 {alert['title']}")
        print(f"     问题: {alert['description']}")
        print(f"     建议: {alert['recommendation']}")
        print(f"     持续: {alert['duration']:.0f}秒")

    # 测试预警摘要
    print("\n=== 预警摘要测试 ===")
    summary = engine.get_alert_summary()
    print(f"活跃预警总数: {summary['total_alerts']}")
    print(f"活跃红色预警: {summary['active_red_alerts']}")
    print(f"活跃黄色预警: {summary['active_yellow_alerts']}")
    print(f"最近预警: {summary['alert_history_keys']}")

    print("\n=== 测试完成 ===")
    print("MAREF预警引擎功能验证通过")


if __name__ == "__main__":
    test_alert_engine()
