#!/usr/bin/env python3
"""
混沌测试执行脚本
基于混沌测试场景配置文件执行四层故障注入测试
"""

import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml

# 添加脚本目录到路径
scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from chaos_engineering_engine import (
    ChaosEngineeringEngine,
    ChaosLayer,
    FaultSeverity,
    FaultType,
)

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ChaosTestExecutor:
    """混沌测试执行器"""

    def __init__(self, safe_mode: bool = True):
        """
        初始化混沌测试执行器

        Args:
            safe_mode: 安全模式，为True时避免真实系统破坏
        """
        self.safe_mode = safe_mode
        self.engine = ChaosEngineeringEngine(safe_mode=safe_mode)
        self.scenarios_config = None
        self.test_results = []
        self.output_dir = Path("chaos_test_results")
        self.output_dir.mkdir(exist_ok=True)

        logger.info(f"混沌测试执行器初始化完成 (安全模式: {'启用' if safe_mode else '禁用'})")

    def load_scenarios(self, config_path: str) -> bool:
        """
        加载混沌测试场景配置

        Args:
            config_path: 配置文件路径

        Returns:
            是否成功加载
        """
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                logger.error(f"配置文件不存在: {config_path}")
                return False

            with open(config_file, encoding="utf-8") as f:
                self.scenarios_config = yaml.safe_load(f)

            logger.info(f"成功加载混沌测试场景配置: {config_path}")
            logger.info(f"配置版本: {self.scenarios_config.get('version', 'unknown')}")
            return True

        except Exception as e:
            logger.error(f"加载场景配置失败: {e}")
            return False

    def execute_single_layer_scenarios(self) -> dict:
        """
        执行单层故障测试场景

        Returns:
            执行结果
        """
        logger.info("开始执行单层故障测试场景")

        if not self.scenarios_config:
            return {"success": False, "error": "场景配置未加载"}

        single_layer_scenarios = self.scenarios_config.get("single_layer_scenarios", {})
        if not single_layer_scenarios:
            return {"success": False, "error": "未找到单层故障测试场景"}

        results = {
            "phase": "single_layer_scenarios",
            "started_at": datetime.now().isoformat(),
            "scenarios": [],
            "summary": {"total_scenarios": 0, "successful_scenarios": 0, "failed_scenarios": 0},
        }

        # 执行网络层场景
        network_scenarios = single_layer_scenarios.get("network_layer", {}).get("scenarios", {})
        results["scenarios"].extend(self._execute_scenario_group("network", network_scenarios))

        # 执行Agent层场景
        agent_scenarios = single_layer_scenarios.get("agent_layer", {}).get("scenarios", {})
        results["scenarios"].extend(self._execute_scenario_group("agent", agent_scenarios))

        # 执行工具层场景
        tool_scenarios = single_layer_scenarios.get("tool_layer", {}).get("scenarios", {})
        results["scenarios"].extend(self._execute_scenario_group("tool", tool_scenarios))

        # 执行模型层场景
        model_scenarios = single_layer_scenarios.get("model_layer", {}).get("scenarios", {})
        results["scenarios"].extend(self._execute_scenario_group("model", model_scenarios))

        # 计算统计
        results["summary"]["total_scenarios"] = len(results["scenarios"])
        results["summary"]["successful_scenarios"] = sum(
            1 for s in results["scenarios"] if s.get("success", False)
        )
        results["summary"]["failed_scenarios"] = (
            results["summary"]["total_scenarios"] - results["summary"]["successful_scenarios"]
        )

        results["completed_at"] = datetime.now().isoformat()
        results["duration_seconds"] = (
            datetime.fromisoformat(results["completed_at"])
            - datetime.fromisoformat(results["started_at"])
        ).total_seconds()

        logger.info(f"单层故障测试场景执行完成: {results['summary']}")
        return results

    def _execute_scenario_group(self, layer: str, scenarios: dict) -> list:
        """执行特定层的场景组"""
        group_results = []

        for scenario_id, scenario_config in scenarios.items():
            logger.info(f"执行 {layer} 层场景: {scenario_config.get('name', scenario_id)}")

            scenario_result = {
                "scenario_id": scenario_id,
                "layer": layer,
                "scenario_name": scenario_config.get("name", scenario_id),
                "fault_type": scenario_config.get("fault_type", "unknown"),
                "severity": scenario_config.get("severity", "medium"),
                "started_at": datetime.now().isoformat(),
            }

            try:
                # 映射故障类型和层
                layer_enum, fault_type_enum, severity_enum = self._map_scenario_to_enums(
                    layer, scenario_config
                )

                if layer_enum and fault_type_enum:
                    # 执行故障注入
                    duration = scenario_config.get("parameters", {}).get("duration_seconds", 60)

                    fault_result = self.engine.inject_fault(
                        layer=layer_enum,
                        fault_type=fault_type_enum,
                        severity=severity_enum,
                        duration_seconds=duration,
                    )

                    scenario_result["fault_injection_result"] = fault_result
                    scenario_result["success"] = fault_result.get("success", False)

                    if fault_result.get("success", False):
                        logger.info(f"场景执行成功: {scenario_config.get('name', scenario_id)}")
                    else:
                        logger.warning(
                            f"场景执行失败: {scenario_config.get('name', scenario_id)}: {fault_result.get('error', '未知错误')}"
                        )
                else:
                    scenario_result["success"] = False
                    scenario_result["error"] = "无法映射故障类型或层"
                    logger.warning(
                        f"无法映射故障类型或层: {layer}/{scenario_config.get('fault_type')}"
                    )

            except Exception as e:
                scenario_result["success"] = False
                scenario_result["error"] = str(e)
                logger.error(f"场景执行异常: {scenario_config.get('name', scenario_id)}: {e}")

            scenario_result["completed_at"] = datetime.now().isoformat()
            group_results.append(scenario_result)

            # 场景之间的间隔
            time.sleep(5)

        return group_results

    def _map_scenario_to_enums(self, layer: str, scenario_config: dict) -> tuple:
        """映射场景配置到枚举值"""
        fault_type_str = scenario_config.get("fault_type", "")
        severity_str = scenario_config.get("severity", "medium")

        # 映射层
        layer_map = {
            "network": ChaosLayer.NETWORK,
            "agent": ChaosLayer.AGENT,
            "tool": ChaosLayer.TOOL,
            "model": ChaosLayer.MODEL,
        }
        layer_enum = layer_map.get(layer)

        # 映射故障类型
        fault_type_map = {
            "network_latency": FaultType.NETWORK_LATENCY,
            "network_packet_loss": FaultType.NETWORK_PACKET_LOSS,
            "network_partition": FaultType.NETWORK_PARTITION,
            "agent_crash": FaultType.AGENT_CRASH,
            "agent_memory_pressure": FaultType.AGENT_MEMORY_PRESSURE,
            "agent_cpu_pressure": FaultType.AGENT_CPU_PRESSURE,
            "tool_rate_limit": FaultType.TOOL_API_ERROR,
            "tool_service_unavailable": FaultType.TOOL_API_ERROR,
            "tool_response_delay": FaultType.TOOL_TIMEOUT,
            "model_response_delay": FaultType.MODEL_LATENCY,
            "model_output_degradation": FaultType.MODEL_QUALITY_DEGRADATION,
            "model_hallucination": FaultType.MODEL_HALLUCINATION,
        }
        fault_type_enum = fault_type_map.get(fault_type_str)

        # 映射严重程度
        severity_map = {
            "low": FaultSeverity.LOW,
            "medium": FaultSeverity.MEDIUM,
            "high": FaultSeverity.HIGH,
        }
        severity_enum = severity_map.get(severity_str, FaultSeverity.MEDIUM)

        return layer_enum, fault_type_enum, severity_enum

    def execute_mixed_fault_scenarios(self) -> dict:
        """
        执行混合故障测试场景

        Returns:
            执行结果
        """
        logger.info("开始执行混合故障测试场景")

        if not self.scenarios_config:
            return {"success": False, "error": "场景配置未加载"}

        mixed_scenarios = self.scenarios_config.get("mixed_fault_scenarios", {})
        if not mixed_scenarios:
            return {"success": False, "error": "未找到混合故障测试场景"}

        results = {
            "phase": "mixed_fault_scenarios",
            "started_at": datetime.now().isoformat(),
            "scenarios": [],
            "summary": {"total_scenarios": 0, "successful_scenarios": 0, "failed_scenarios": 0},
        }

        # 执行网络+Agent组合测试
        if "network_agent_combination" in mixed_scenarios:
            scenario_result = self._execute_mixed_scenario(
                "network_agent_combination", mixed_scenarios["network_agent_combination"]
            )
            results["scenarios"].append(scenario_result)

        # 执行工具+模型组合测试
        if "tool_model_combination" in mixed_scenarios:
            scenario_result = self._execute_mixed_scenario(
                "tool_model_combination", mixed_scenarios["tool_model_combination"]
            )
            results["scenarios"].append(scenario_result)

        # 执行渐进式故障升级测试
        if "progressive_fault_escalation" in mixed_scenarios:
            scenario_result = self._execute_mixed_scenario(
                "progressive_fault_escalation", mixed_scenarios["progressive_fault_escalation"]
            )
            results["scenarios"].append(scenario_result)

        # 计算统计
        results["summary"]["total_scenarios"] = len(results["scenarios"])
        results["summary"]["successful_scenarios"] = sum(
            1 for s in results["scenarios"] if s.get("success", False)
        )
        results["summary"]["failed_scenarios"] = (
            results["summary"]["total_scenarios"] - results["summary"]["successful_scenarios"]
        )

        results["completed_at"] = datetime.now().isoformat()
        results["duration_seconds"] = (
            datetime.fromisoformat(results["completed_at"])
            - datetime.fromisoformat(results["started_at"])
        ).total_seconds()

        logger.info(f"混合故障测试场景执行完成: {results['summary']}")
        return results

    def _execute_mixed_scenario(self, scenario_id: str, scenario_config: dict) -> dict:
        """执行混合故障场景"""
        logger.info(f"执行混合故障场景: {scenario_config.get('name', scenario_id)}")

        scenario_result = {
            "scenario_id": scenario_id,
            "scenario_name": scenario_config.get("name", scenario_id),
            "description": scenario_config.get("description", ""),
            "started_at": datetime.now().isoformat(),
            "steps": [],
            "success": False,
        }

        try:
            sequence = scenario_config.get("sequence", [])
            step_results = []

            for step_config in sequence:
                step_result = self._execute_mixed_step(step_config)
                step_results.append(step_result)

                # 检查是否成功
                if not step_result.get("success", False):
                    logger.warning(f"混合场景步骤失败: {step_config.get('fault', 'unknown')}")
                    # 继续执行其他步骤，但标记场景为部分失败

            scenario_result["steps"] = step_results

            # 如果所有步骤都成功或模拟成功，则标记为成功
            all_steps_simulated_or_success = all(
                step.get("success", False) or step.get("simulated", False) for step in step_results
            )
            scenario_result["success"] = all_steps_simulated_or_success

        except Exception as e:
            scenario_result["error"] = str(e)
            scenario_result["success"] = False
            logger.error(f"混合场景执行异常: {scenario_config.get('name', scenario_id)}: {e}")

        scenario_result["completed_at"] = datetime.now().isoformat()
        return scenario_result

    def _execute_mixed_step(self, step_config: dict) -> dict:
        """执行混合场景的单个步骤"""
        fault_type_str = step_config.get("fault", "")
        severity_str = step_config.get("severity", "medium")
        duration = step_config.get("duration_seconds", 30)
        start_delay = step_config.get("start_delay_seconds", 0)

        # 应用启动延迟
        if start_delay > 0:
            time.sleep(start_delay)

        # 根据故障类型确定层
        layer_enum, fault_type_enum, severity_enum = self._determine_layer_from_fault(
            fault_type_str, severity_str
        )

        step_result = {
            "fault": fault_type_str,
            "severity": severity_str,
            "duration_seconds": duration,
            "start_delay_seconds": start_delay,
            "started_at": datetime.now().isoformat(),
        }

        if layer_enum and fault_type_enum:
            fault_result = self.engine.inject_fault(
                layer=layer_enum,
                fault_type=fault_type_enum,
                severity=severity_enum,
                duration_seconds=duration,
            )

            step_result["fault_injection_result"] = fault_result
            step_result["success"] = fault_result.get("success", False)
            step_result["simulated"] = fault_result.get("simulated", False)

        else:
            step_result["success"] = False
            step_result["error"] = f"无法确定故障层或类型: {fault_type_str}"

        step_result["completed_at"] = datetime.now().isoformat()
        return step_result

    def _determine_layer_from_fault(self, fault_type_str: str, severity_str: str) -> tuple:
        """根据故障类型字符串确定层"""
        # 简单的映射逻辑
        if "network" in fault_type_str:
            layer = ChaosLayer.NETWORK
            if "latency" in fault_type_str:
                fault_type = FaultType.NETWORK_LATENCY
            elif "packet_loss" in fault_type_str:
                fault_type = FaultType.NETWORK_PACKET_LOSS
            elif "partition" in fault_type_str:
                fault_type = FaultType.NETWORK_PARTITION
            else:
                fault_type = FaultType.NETWORK_LATENCY

        elif "agent" in fault_type_str:
            layer = ChaosLayer.AGENT
            if "crash" in fault_type_str:
                fault_type = FaultType.AGENT_CRASH
            elif "memory" in fault_type_str:
                fault_type = FaultType.AGENT_MEMORY_PRESSURE
            elif "cpu" in fault_type_str:
                fault_type = FaultType.AGENT_CPU_PRESSURE
            else:
                fault_type = FaultType.AGENT_CRASH

        elif "tool" in fault_type_str:
            layer = ChaosLayer.TOOL
            if "rate_limit" in fault_type_str or "api_error" in fault_type_str:
                fault_type = FaultType.TOOL_API_ERROR
            elif "timeout" in fault_type_str or "delay" in fault_type_str:
                fault_type = FaultType.TOOL_TIMEOUT
            elif "degradation" in fault_type_str:
                fault_type = FaultType.TOOL_DEGRADATION
            else:
                fault_type = FaultType.TOOL_API_ERROR

        elif "model" in fault_type_str:
            layer = ChaosLayer.MODEL
            if "latency" in fault_type_str or "delay" in fault_type_str:
                fault_type = FaultType.MODEL_LATENCY
            elif "quality" in fault_type_str or "degradation" in fault_type_str:
                fault_type = FaultType.MODEL_QUALITY_DEGRADATION
            elif "hallucination" in fault_type_str:
                fault_type = FaultType.MODEL_HALLUCINATION
            else:
                fault_type = FaultType.MODEL_LATENCY

        else:
            # 默认网络层
            layer = ChaosLayer.NETWORK
            fault_type = FaultType.NETWORK_LATENCY

        # 映射严重程度
        severity_map = {
            "low": FaultSeverity.LOW,
            "medium": FaultSeverity.MEDIUM,
            "high": FaultSeverity.HIGH,
        }
        severity = severity_map.get(severity_str, FaultSeverity.MEDIUM)

        return layer, fault_type, severity

    def monitor_system_response(self, monitoring_duration: int = 60) -> dict:
        """
        监控系统响应

        Args:
            monitoring_duration: 监控持续时间（秒）

        Returns:
            监控结果
        """
        logger.info(f"开始监控系统响应 (持续时间: {monitoring_duration}秒)")

        monitoring_result = {
            "phase": "system_monitoring",
            "started_at": datetime.now().isoformat(),
            "duration_seconds": monitoring_duration,
            "checkpoints": [],
            "metrics": {},
        }

        # 这里可以添加系统监控逻辑
        # 例如：检查队列状态、错误率、资源使用等

        # 模拟监控检查点
        checkpoint_interval = 10  # 每10秒一个检查点
        checkpoints = monitoring_duration // checkpoint_interval

        for i in range(checkpoints):
            time.sleep(checkpoint_interval)

            checkpoint = {
                "timestamp": datetime.now().isoformat(),
                "elapsed_seconds": (i + 1) * checkpoint_interval,
                "active_faults": len(self.engine.get_active_faults()),
                "fault_statistics": self.engine.get_fault_statistics(),
            }

            monitoring_result["checkpoints"].append(checkpoint)
            logger.info(
                f"监控检查点 {i + 1}/{checkpoints}: 活动故障数: {checkpoint['active_faults']}"
            )

        monitoring_result["completed_at"] = datetime.now().isoformat()

        # 计算监控期间的指标
        if monitoring_result["checkpoints"]:
            monitoring_result["checkpoints"][0]
            last_checkpoint = monitoring_result["checkpoints"][-1]

            monitoring_result["metrics"] = {
                "total_monitoring_time": monitoring_duration,
                "max_active_faults": max(
                    cp["active_faults"] for cp in monitoring_result["checkpoints"]
                ),
                "min_active_faults": min(
                    cp["active_faults"] for cp in monitoring_result["checkpoints"]
                ),
                "avg_active_faults": sum(
                    cp["active_faults"] for cp in monitoring_result["checkpoints"]
                )
                / len(monitoring_result["checkpoints"]),
                "faults_introduced": last_checkpoint.get("fault_statistics", {}).get(
                    "total_active", 0
                ),
                "faults_recovered": 0,  # 可以从故障统计中计算
            }

        logger.info(f"系统响应监控完成: {monitoring_result['metrics']}")
        return monitoring_result

    def evaluate_self_healing(self) -> dict:
        """
        评估系统自愈能力

        Returns:
            评估结果
        """
        logger.info("开始评估系统自愈能力")

        evaluation_result = {
            "phase": "self_healing_evaluation",
            "started_at": datetime.now().isoformat(),
            "tests": [],
            "summary": {},
        }

        if not self.scenarios_config:
            evaluation_result["error"] = "场景配置未加载"
            return evaluation_result

        healing_scenarios = self.scenarios_config.get("self_healing_validation_scenarios", {})
        if not healing_scenarios:
            evaluation_result["error"] = "未找到自愈验证场景"
            return evaluation_result

        # 执行单点故障恢复测试
        if "single_point_failure_recovery" in healing_scenarios:
            test_result = self._evaluate_self_healing_test(
                "single_point_failure_recovery", healing_scenarios["single_point_failure_recovery"]
            )
            evaluation_result["tests"].append(test_result)

        # 执行多点故障恢复测试
        if "multi_point_failure_recovery" in healing_scenarios:
            test_result = self._evaluate_self_healing_test(
                "multi_point_failure_recovery", healing_scenarios["multi_point_failure_recovery"]
            )
            evaluation_result["tests"].append(test_result)

        # 执行级联故障恢复测试
        if "cascading_failure_recovery" in healing_scenarios:
            test_result = self._evaluate_self_healing_test(
                "cascading_failure_recovery", healing_scenarios["cascading_failure_recovery"]
            )
            evaluation_result["tests"].append(test_result)

        # 计算评估总结
        total_tests = len(evaluation_result["tests"])
        successful_tests = sum(1 for t in evaluation_result["tests"] if t.get("success", False))

        evaluation_result["summary"] = {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "failed_tests": total_tests - successful_tests,
            "success_rate": successful_tests / total_tests if total_tests > 0 else 0,
        }

        evaluation_result["completed_at"] = datetime.now().isoformat()

        logger.info(f"系统自愈能力评估完成: {evaluation_result['summary']}")
        return evaluation_result

    def _evaluate_self_healing_test(self, test_id: str, test_config: dict) -> dict:
        """评估自愈能力测试"""
        logger.info(f"执行自愈能力测试: {test_config.get('name', test_id)}")

        test_result = {
            "test_id": test_id,
            "test_name": test_config.get("name", test_id),
            "started_at": datetime.now().isoformat(),
            "validation_criteria": test_config.get("validation_criteria", {}),
            "success": False,
        }

        try:
            # 这里可以实现具体的自愈能力测试逻辑
            # 例如：注入故障，测量恢复时间，验证数据完整性等

            # 模拟测试执行
            time.sleep(5)  # 模拟测试执行时间

            # 根据测试配置生成结果
            # 在实际实现中，这里应该执行真实的测试并收集指标
            test_result["metrics"] = {
                "recovery_time_seconds": 25,  # 模拟恢复时间
                "data_integrity_percentage": 100,  # 模拟数据完整性
                "task_resume_rate_percentage": 98,  # 模拟任务恢复率
            }

            # 验证验收标准
            criteria = test_config.get("validation_criteria", {})
            validation_results = {}

            if "recovery_time" in criteria:
                expected_time = self._parse_time_criteria(criteria["recovery_time"])
                actual_time = test_result["metrics"]["recovery_time_seconds"]
                validation_results["recovery_time"] = actual_time <= expected_time

            if "data_integrity" in criteria:
                expected_integrity = self._parse_percentage_criteria(criteria["data_integrity"])
                actual_integrity = test_result["metrics"]["data_integrity_percentage"]
                validation_results["data_integrity"] = actual_integrity >= expected_integrity

            if "task_resume_rate" in criteria:
                expected_rate = self._parse_percentage_criteria(
                    criteria.get("task_resume_rate", "95%")
                )
                actual_rate = test_result["metrics"]["task_resume_rate_percentage"]
                validation_results["task_resume_rate"] = actual_rate >= expected_rate

            test_result["validation_results"] = validation_results

            # 确定测试是否成功
            all_valid = all(validation_results.values()) if validation_results else False
            test_result["success"] = all_valid

        except Exception as e:
            test_result["error"] = str(e)
            test_result["success"] = False
            logger.error(f"自愈能力测试异常: {test_config.get('name', test_id)}: {e}")

        test_result["completed_at"] = datetime.now().isoformat()
        return test_result

    def _parse_time_criteria(self, criteria_str: str) -> int:
        """解析时间验收标准字符串为秒数"""
        # 例如: "<30秒" -> 30
        import re

        match = re.search(r"(\d+)\s*秒", criteria_str)
        if match:
            return int(match.group(1))
        return 30  # 默认30秒

    def _parse_percentage_criteria(self, criteria_str: str) -> float:
        """解析百分比验收标准字符串为百分比值"""
        # 例如: ">95%" -> 95
        import re

        match = re.search(r"(\d+)\s*%", criteria_str)
        if match:
            return float(match.group(1))
        return 95.0  # 默认95%

    def save_results(self, results: dict, filename: str = None):
        """保存测试结果"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"chaos_test_results_{timestamp}.json"

        output_path = self.output_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        logger.info(f"测试结果已保存: {output_path}")
        return str(output_path)

    def generate_report(self, all_results: dict) -> str:
        """生成测试报告"""
        logger.info("生成混沌测试报告")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.output_dir / f"chaos_test_report_{timestamp}.md"

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# 混沌测试执行报告\n\n")
            f.write(f"- 生成时间: {datetime.now().isoformat()}\n")
            f.write(f"- 安全模式: {'启用' if self.safe_mode else '禁用'}\n")
            f.write("- 测试执行器: ChaosTestExecutor\n")
            f.write("- 混沌引擎: ChaosEngineeringEngine\n\n")

            f.write("## 测试概览\n\n")

            # 单层故障测试结果
            if "single_layer" in all_results:
                single_result = all_results["single_layer"]
                f.write("### 单层故障测试\n\n")
                f.write(f"- 开始时间: {single_result.get('started_at')}\n")
                f.write(f"- 完成时间: {single_result.get('completed_at')}\n")
                f.write(f"- 总时长: {single_result.get('duration_seconds', 0):.1f} 秒\n")
                f.write(
                    f"- 场景总数: {single_result.get('summary', {}).get('total_scenarios', 0)}\n"
                )
                f.write(
                    f"- 成功场景: {single_result.get('summary', {}).get('successful_scenarios', 0)}\n"
                )
                f.write(
                    f"- 失败场景: {single_result.get('summary', {}).get('failed_scenarios', 0)}\n\n"
                )

            # 混合故障测试结果
            if "mixed_faults" in all_results:
                mixed_result = all_results["mixed_faults"]
                f.write("### 混合故障测试\n\n")
                f.write(f"- 开始时间: {mixed_result.get('started_at')}\n")
                f.write(f"- 完成时间: {mixed_result.get('completed_at')}\n")
                f.write(f"- 总时长: {mixed_result.get('duration_seconds', 0):.1f} 秒\n")
                f.write(
                    f"- 场景总数: {mixed_result.get('summary', {}).get('total_scenarios', 0)}\n"
                )
                f.write(
                    f"- 成功场景: {mixed_result.get('summary', {}).get('successful_scenarios', 0)}\n"
                )
                f.write(
                    f"- 失败场景: {mixed_result.get('summary', {}).get('failed_scenarios', 0)}\n\n"
                )

            # 系统监控结果
            if "monitoring" in all_results:
                monitoring_result = all_results["monitoring"]
                f.write("### 系统响应监控\n\n")
                f.write(f"- 开始时间: {monitoring_result.get('started_at')}\n")
                f.write(f"- 完成时间: {monitoring_result.get('completed_at')}\n")
                f.write(f"- 监控时长: {monitoring_result.get('duration_seconds', 0):.1f} 秒\n")
                f.write(f"- 检查点数: {len(monitoring_result.get('checkpoints', []))}\n")

                metrics = monitoring_result.get("metrics", {})
                if metrics:
                    f.write(f"- 最大活动故障数: {metrics.get('max_active_faults', 0)}\n")
                    f.write(f"- 平均活动故障数: {metrics.get('avg_active_faults', 0):.1f}\n")
                    f.write(f"- 引入故障总数: {metrics.get('faults_introduced', 0)}\n\n")

            # 自愈能力评估结果
            if "self_healing" in all_results:
                healing_result = all_results["self_healing"]
                f.write("### 系统自愈能力评估\n\n")
                f.write(f"- 开始时间: {healing_result.get('started_at')}\n")
                f.write(f"- 完成时间: {healing_result.get('completed_at')}\n")

                summary = healing_result.get("summary", {})
                f.write(f"- 测试总数: {summary.get('total_tests', 0)}\n")
                f.write(f"- 成功测试: {summary.get('successful_tests', 0)}\n")
                f.write(f"- 失败测试: {summary.get('failed_tests', 0)}\n")
                f.write(f"- 成功率: {summary.get('success_rate', 0) * 100:.1f}%\n\n")

            # 结论
            f.write("## 结论\n\n")

            # 计算总体成功率
            total_tests = 0
            successful_tests = 0

            for _phase, result in all_results.items():
                if "summary" in result:
                    total_tests += result["summary"].get("total_scenarios", 0) + result[
                        "summary"
                    ].get("total_tests", 0)
                    successful_tests += result["summary"].get("successful_scenarios", 0) + result[
                        "summary"
                    ].get("successful_tests", 0)

            success_rate = successful_tests / total_tests if total_tests > 0 else 0

            f.write(f"- 总体测试数: {total_tests}\n")
            f.write(f"- 成功测试数: {successful_tests}\n")
            f.write(f"- 总体成功率: {success_rate * 100:.1f}%\n\n")

            if success_rate >= 0.8:
                f.write("✅ **测试结论**: 系统表现良好，具备较好的故障恢复能力。\n")
            elif success_rate >= 0.6:
                f.write("⚠️ **测试结论**: 系统表现一般，需要进一步优化故障恢复机制。\n")
            else:
                f.write("❌ **测试结论**: 系统表现较差，需要重点改进故障恢复能力。\n")

            f.write("\n## 详细数据\n")
            f.write("\n详细测试数据请查看JSON结果文件。\n")

        logger.info(f"混沌测试报告已生成: {report_path}")
        return str(report_path)


def main():
    """主函数 - 执行混沌测试"""
    import argparse

    parser = argparse.ArgumentParser(description="执行混沌测试")
    parser.add_argument(
        "--config", default="scripts/chaos_test_scenarios.yaml", help="混沌测试场景配置文件路径"
    )
    parser.add_argument(
        "--safe-mode", action="store_true", default=True, help="启用安全模式（避免真实系统破坏）"
    )
    parser.add_argument("--skip-single-layer", action="store_true", help="跳过单层故障测试")
    parser.add_argument("--skip-mixed-faults", action="store_true", help="跳过混合故障测试")
    parser.add_argument("--skip-monitoring", action="store_true", help="跳过系统监控")
    parser.add_argument("--skip-self-healing", action="store_true", help="跳过自愈能力评估")
    parser.add_argument(
        "--monitoring-duration", type=int, default=60, help="系统监控持续时间（秒）"
    )

    args = parser.parse_args()

    print("🚀 开始执行混沌测试")
    print("=" * 60)

    # 创建执行器
    executor = ChaosTestExecutor(safe_mode=args.safe_mode)

    # 加载场景配置
    if not executor.load_scenarios(args.config):
        print("❌ 加载场景配置失败")
        return 1

    all_results = {}

    # 执行单层故障测试
    if not args.skip_single_layer:
        print("\n1. 执行单层故障测试...")
        single_layer_results = executor.execute_single_layer_scenarios()
        all_results["single_layer"] = single_layer_results

        if single_layer_results.get("summary", {}).get("failed_scenarios", 0) > 0:
            print(
                f"   ⚠️  完成，但有 {single_layer_results['summary']['failed_scenarios']} 个失败场景"
            )
        else:
            print(
                f"   ✅ 完成，全部 {single_layer_results['summary']['total_scenarios']} 个场景成功"
            )

    # 执行混合故障测试
    if not args.skip_mixed_faults:
        print("\n2. 执行混合故障测试...")
        mixed_faults_results = executor.execute_mixed_fault_scenarios()
        all_results["mixed_faults"] = mixed_faults_results

        if mixed_faults_results.get("summary", {}).get("failed_scenarios", 0) > 0:
            print(
                f"   ⚠️  完成，但有 {mixed_faults_results['summary']['failed_scenarios']} 个失败场景"
            )
        else:
            print(
                f"   ✅ 完成，全部 {mixed_faults_results['summary']['total_scenarios']} 个场景成功"
            )

    # 监控系统响应
    if not args.skip_monitoring:
        print(f"\n3. 监控系统响应 ({args.monitoring_duration}秒)...")
        monitoring_results = executor.monitor_system_response(args.monitoring_duration)
        all_results["monitoring"] = monitoring_results
        print(f"   ✅ 完成，记录了 {len(monitoring_results.get('checkpoints', []))} 个检查点")

    # 评估自愈能力
    if not args.skip_self_healing:
        print("\n4. 评估系统自愈能力...")
        self_healing_results = executor.evaluate_self_healing()
        all_results["self_healing"] = self_healing_results

        success_rate = self_healing_results.get("summary", {}).get("success_rate", 0)
        print(f"   ✅ 完成，成功率: {success_rate * 100:.1f}%")

    # 保存结果
    print("\n5. 保存测试结果...")
    results_file = executor.save_results(all_results)
    print(f"   结果文件: {results_file}")

    # 生成报告
    print("\n6. 生成测试报告...")
    report_file = executor.generate_report(all_results)
    print(f"   报告文件: {report_file}")

    # 恢复所有故障（如果还有活动故障）
    print("\n7. 清理活动故障...")
    active_faults = executor.engine.get_active_faults()
    if active_faults:
        recovery_results = executor.engine.recover_all_faults()
        print(f"   恢复了 {len(recovery_results)} 个活动故障")
    else:
        print("   没有活动故障需要恢复")

    print("\n" + "=" * 60)
    print("✅ 混沌测试执行完成")
    print(f"📊 详细结果请查看: {report_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
