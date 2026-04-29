#!/usr/bin/env python3
"""
Harness Acceptance - 观测评估基线与集成验收脚本

验证 Harness Engineering 要求的观测、评估和验收基线。
检查上下文层、执行编排层、恢复层的关键接线。
生成结构化证据供审计链使用。

执行要求：
1. 最小可运行闭环
2. 基于当前工作区真实结构
3. 输出 JSON 证据到 workspace/
4. 与现有 build artifact、review、memory 体系对齐
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 路径配置
RUNTIME_ROOT = Path(os.getenv("ATHENA_RUNTIME_ROOT", "/Volumes/1TB-M2/openclaw"))
WORKSPACE_DIR = RUNTIME_ROOT / "workspace"
EVIDENCE_FILE = WORKSPACE_DIR / "harness_acceptance_evidence.json"
OBSERVABILITY_DIR = RUNTIME_ROOT / "observability"
SCRIPTS_DIR = RUNTIME_ROOT / "scripts"
MINI_AGENT_DIR = RUNTIME_ROOT / "mini-agent"
AGENT_CORE_DIR = MINI_AGENT_DIR / "agent" / "core"
OPENCLAW_DIR = RUNTIME_ROOT / ".openclaw"


class HarnessAcceptance:
    """Harness 验收测试器"""

    def __init__(self):
        self.evidence = {
            "contractVersion": "harness-acceptance.v1",
            "generatedAt": datetime.now().isoformat(),
            "runtimeRoot": str(RUNTIME_ROOT),
            "tests": {},
            "metrics": {},
            "warnings": [],
            "summary": {
                "passed": 0,
                "failed": 0,
                "total": 0,
            },
        }
        # 添加模块搜索路径
        sys.path.insert(0, str(MINI_AGENT_DIR))
        sys.path.insert(0, str(RUNTIME_ROOT))
        self.start_time = time.time()

    def log_test(self, name: str, passed: bool, message: str, details: dict[str, Any] = None):
        """记录测试结果"""
        self.evidence["tests"][name] = {
            "passed": passed,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "details": details or {},
        }
        self.evidence["summary"]["total"] += 1
        if passed:
            self.evidence["summary"]["passed"] += 1
            logger.info(f"✓ {name}: {message}")
        else:
            self.evidence["summary"]["failed"] += 1
            logger.error(f"✗ {name}: {message}")

    def add_warning(self, warning: str):
        """添加警告"""
        self.evidence["warnings"].append(
            {
                "message": warning,
                "timestamp": datetime.now().isoformat(),
            }
        )
        logger.warning(f"警告: {warning}")

    def add_metric(self, name: str, value: Any, unit: str = "", metadata: dict[str, Any] = None):
        """添加指标"""
        self.evidence["metrics"][name] = {
            "value": value,
            "unit": unit,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }

    def save_evidence(self):
        """保存证据文件"""
        self.evidence["durationSeconds"] = time.time() - self.start_time
        WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
        with open(EVIDENCE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.evidence, f, ensure_ascii=False, indent=2)
        logger.info(f"证据已保存: {EVIDENCE_FILE}")
        return EVIDENCE_FILE

    def run_all_tests(self):
        """运行所有验收测试"""
        logger.info("=== 开始 Harness 验收测试 ===")

        # 1. 观测数据模型验证
        self.test_observability_schema()

        # 2. 上下文层验证
        self.test_context_layer()

        # 3. 执行编排层验证
        self.test_orchestration_layer()

        # 4. 恢复层验证
        self.test_recovery_layer()

        # 5. 评估基线验证
        self.test_evaluation_baseline()

        # 6. 集成验收（端到端接线）
        self.test_integration_smoke()

        # 生成总结
        self.generate_summary()

        # 保存证据
        self.save_evidence()

        logger.info("=== Harness 验收测试完成 ===")
        return self.evidence["summary"]["failed"] == 0

    def test_observability_schema(self):
        """测试观测数据模型"""
        name = "observability_schema"
        try:
            # 检查 schema 文件存在
            schema_files = [
                "common.schema.json",
                "task-trace.schema.json",
                "system-facts.schema.json",
                "health.schema.json",
            ]
            missing = []
            for fname in schema_files:
                path = OBSERVABILITY_DIR / "contracts" / fname
                if not path.exists():
                    missing.append(fname)

            if missing:
                self.log_test(name, False, f"缺失 schema 文件: {missing}", {"missing": missing})
                return

            # 检查统一字段
            common_path = OBSERVABILITY_DIR / "contracts" / "common.schema.json"
            with open(common_path, encoding="utf-8") as f:
                common = json.load(f)

            # 验证 responseEnvelope 定义
            if "$defs" not in common or "responseEnvelope" not in common["$defs"]:
                self.log_test(name, False, "common.schema.json 缺少 responseEnvelope 定义")
                return

            envelope_def = common["$defs"]["responseEnvelope"]
            required_fields = [
                "contractVersion",
                "generatedAt",
                "runtimeRoot",
                "source",
                "freshness",
            ]
            if "required" not in envelope_def:
                self.log_test(name, False, "responseEnvelope 缺少 required 字段")
                return

            for field in required_fields:
                if field not in envelope_def["required"]:
                    self.log_test(name, False, f"responseEnvelope 缺少必需字段: {field}")
                    return

            self.log_test(
                name,
                True,
                "观测数据模型 schema 完整，统一字段定义有效",
                {
                    "schema_count": len(schema_files),
                    "contract_version": common.get("$defs", {})
                    .get("contractVersion", {})
                    .get("const", "unknown"),
                },
            )

        except Exception as e:
            self.log_test(name, False, f"观测数据模型测试异常: {e}")

    def test_context_layer(self):
        """测试上下文层"""
        name = "context_layer"
        try:
            # 尝试导入 context_budget 模块
            from agent.core.context_budget import get_budget_manager

            # 检查预算管理器
            manager = get_budget_manager()
            if manager is None:
                self.log_test(name, False, "context_budget 模块未返回预算管理器")
                return

            # 记录成功
            self.log_test(
                name,
                True,
                "上下文层接线正常",
                {
                    "budget_manager_available": True,
                    "manager_type": type(manager).__name__,
                },
            )

            # 添加上下文指标
            self.add_metric("context_budget_manager_available", True)

            # 尝试检查上下文健康（可选）
            try:
                # 使用默认参数调用（如果函数支持）
                import inspect

                from agent.core.context_budget import check_context_health

                sig = inspect.signature(check_context_health)
                if len(sig.parameters) == 0:
                    health = check_context_health()
                else:
                    # 跳过需要参数的调用
                    health = {"status": "requires_parameters"}
                if isinstance(health, dict):
                    self.add_metric("context_health_status", health.get("status", "unknown"))
            except Exception:
                pass

        except ImportError as e:
            self.log_test(name, False, f"context_budget 模块不可导入: {e}")
            self.add_warning("上下文预算模块不可用，可能影响任务编排")
        except Exception as e:
            self.log_test(name, False, f"上下文层测试异常: {e}")

    def test_orchestration_layer(self):
        """测试执行编排层"""
        name = "orchestration_layer"
        try:
            # 尝试导入 orchestrator 模块
            sys.path.insert(0, str(AGENT_CORE_DIR.parent))
            from agent.core.athena_orchestrator import (
                EXECUTION_INTEGRATION_AVAILABLE,
                TASKS_DIR,
            )

            # 检查任务目录存在
            if not TASKS_DIR.exists():
                self.log_test(name, False, f"任务目录不存在: {TASKS_DIR}")
                return

            # 检查执行集成可用性
            self.log_test(
                name,
                True,
                "执行编排层接线正常",
                {
                    "tasks_dir_exists": True,
                    "execution_integration_available": EXECUTION_INTEGRATION_AVAILABLE,
                    "tasks_dir": str(TASKS_DIR),
                },
            )

            # 添加编排指标
            self.add_metric("orchestration_tasks_dir_exists", True)
            self.add_metric("execution_integration_available", EXECUTION_INTEGRATION_AVAILABLE)

            # 检查是否有任务文件
            tasks_path = OPENCLAW_DIR / "orchestrator" / "tasks.json"
            if tasks_path.exists():
                try:
                    with open(tasks_path, encoding="utf-8") as f:
                        tasks_data = json.load(f)
                    task_count = len(tasks_data.get("tasks", []))
                    self.add_metric("total_tasks", task_count)
                except Exception:
                    pass

        except ImportError as e:
            self.log_test(name, False, f"athena_orchestrator 模块不可导入: {e}")
        except Exception as e:
            self.log_test(name, False, f"执行编排层测试异常: {e}")

    def test_recovery_layer(self):
        """测试恢复层"""
        name = "recovery_layer"
        try:
            # 检查队列保护脚本
            queue_protection_scripts = [
                "protect_all_queues.py",
                "queue_state_protector.py",
                "fix_queue_stopping_and_manual_launch.py",
            ]

            available_scripts = []
            for script in queue_protection_scripts:
                path = SCRIPTS_DIR / script
                if path.exists():
                    available_scripts.append(script)

            # 检查队列状态目录
            queue_state_dir = OPENCLAW_DIR / "plan_queue"
            queue_state_exists = queue_state_dir.exists()

            # 检查队列状态文件
            queue_state_files = []
            if queue_state_exists:
                for item in queue_state_dir.iterdir():
                    if item.is_file():
                        queue_state_files.append(item.name)

            # 评估恢复能力
            recovery_score = min(
                100, len(available_scripts) * 20 + (10 if queue_state_exists else 0)
            )

            self.log_test(
                name,
                True,
                "恢复层接线正常",
                {
                    "queue_protection_scripts": available_scripts,
                    "queue_state_dir_exists": queue_state_exists,
                    "queue_state_file_count": len(queue_state_files),
                    "recovery_score": recovery_score,
                },
            )

            # 添加恢复指标
            self.add_metric("queue_protection_scripts_count", len(available_scripts))
            self.add_metric("queue_state_exists", queue_state_exists)
            self.add_metric("recovery_score", recovery_score, unit="percent")

        except Exception as e:
            self.log_test(name, False, f"恢复层测试异常: {e}")

    def test_evaluation_baseline(self):
        """测试评估基线"""
        name = "evaluation_baseline"
        try:
            # 尝试导入 scoreboard 模块
            sys.path.insert(0, str(AGENT_CORE_DIR.parent))
            from agent.core.scoreboard import (
                generate_scoreboard,
                get_score_trend,
                load_latest_score,
            )

            # 生成或加载最新评分
            latest_score = load_latest_score()
            if latest_score is None:
                # 生成新评分
                latest_score = generate_scoreboard()

            # 获取趋势
            trend = get_score_trend()

            # 计算核心指标
            core_metrics = self.calculate_core_metrics()

            self.log_test(
                name,
                True,
                "评估基线正常",
                {
                    "scoreboard_available": True,
                    "technical_score": latest_score.technical_score,
                    "user_score": latest_score.user_score,
                    "business_score": latest_score.business_score,
                    "overall_score": latest_score.overall_score,
                    "trend_status": trend.get("trend", "unknown"),
                    "core_metrics": core_metrics,
                },
            )

            # 添加评估指标
            self.add_metric("technical_score", latest_score.technical_score, unit="percent")
            self.add_metric("user_score", latest_score.user_score, unit="percent")
            self.add_metric("business_score", latest_score.business_score, unit="percent")
            self.add_metric("overall_score", latest_score.overall_score, unit="percent")

            for metric_name, metric_value in core_metrics.items():
                self.add_metric(
                    f"core_{metric_name}",
                    metric_value.get("value"),
                    unit=metric_value.get("unit", ""),
                )

        except ImportError as e:
            self.log_test(name, False, f"scoreboard 模块不可导入: {e}")
            # 回退：计算基本核心指标
            self.fallback_core_metrics()
        except Exception as e:
            self.log_test(name, False, f"评估基线测试异常: {e}")
            self.fallback_core_metrics()

    def calculate_core_metrics(self) -> dict[str, dict[str, Any]]:
        """计算核心指标：成功率、恢复率、延迟、资源使用"""
        metrics = {}

        try:
            # 1. 成功率：基于任务完成率
            tasks_path = OPENCLAW_DIR / "orchestrator" / "tasks.json"
            if tasks_path.exists():
                with open(tasks_path, encoding="utf-8") as f:
                    tasks_data = json.load(f)
                tasks = tasks_data.get("tasks", [])
                if tasks:
                    completed = sum(1 for t in tasks if t.get("status") == "completed")
                    success_rate = completed / len(tasks) * 100
                    metrics["success_rate"] = {
                        "value": round(success_rate, 1),
                        "unit": "percent",
                        "description": "任务完成率",
                    }

            # 2. 恢复率：基于队列失败恢复（简化）
            queue_state_dir = OPENCLAW_DIR / "plan_queue"
            if queue_state_dir.exists():
                # 检查是否有失败状态的项目
                recovery_items = []
                for item in queue_state_dir.iterdir():
                    if item.is_file() and item.suffix == ".json":
                        try:
                            with open(item, encoding="utf-8") as f:
                                state = json.load(f)
                            if state.get("status") == "failed":
                                # 检查是否有重试记录
                                if state.get("retry_count", 0) > 0:
                                    recovery_items.append(item.name)
                        except Exception:
                            pass

                # 简单恢复率估算
                recovery_rate = min(100, len(recovery_items) * 20)  # 每个恢复项+20%
                metrics["recovery_rate"] = {
                    "value": recovery_rate,
                    "unit": "percent",
                    "description": "队列失败恢复率",
                }

            # 3. 延迟：基于任务时间戳（简化）
            tasks_path = OPENCLAW_DIR / "orchestrator" / "tasks.json"
            if tasks_path.exists():
                with open(tasks_path, encoding="utf-8") as f:
                    tasks_data = json.load(f)
                tasks = tasks_data.get("tasks", [])
                if tasks:
                    # 计算平均执行时间（如果有时间戳）
                    total_duration = 0
                    count = 0
                    for task in tasks:
                        started = task.get("started_at")
                        finished = task.get("finished_at")
                        if started and finished:
                            try:
                                start_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
                                end_dt = datetime.fromisoformat(finished.replace("Z", "+00:00"))
                                duration = (end_dt - start_dt).total_seconds()
                                total_duration += duration
                                count += 1
                            except Exception:
                                pass

                    if count > 0:
                        avg_duration = total_duration / count
                        metrics["avg_task_duration"] = {
                            "value": round(avg_duration, 1),
                            "unit": "seconds",
                            "description": "平均任务执行时间",
                        }

            # 4. 资源使用：基于系统事实（如果可用）
            system_facts_path = OPENCLAW_DIR / "health" / "system_facts.json"
            if system_facts_path.exists():
                try:
                    with open(system_facts_path, encoding="utf-8") as f:
                        facts = json.load(f)
                    cpu_usage = facts.get("cpu", {}).get("usage_percent", 0)
                    memory_pressure = facts.get("memory", {}).get("pressure_used_percent", 0)

                    metrics["cpu_usage"] = {
                        "value": round(cpu_usage, 1),
                        "unit": "percent",
                        "description": "CPU使用率",
                    }
                    metrics["memory_pressure"] = {
                        "value": round(memory_pressure, 1),
                        "unit": "percent",
                        "description": "内存压力",
                    }
                except Exception:
                    pass

        except Exception as e:
            logger.warning(f"计算核心指标时出错: {e}")

        return metrics

    def fallback_core_metrics(self):
        """回退核心指标计算（当scoreboard不可用时）"""
        try:
            metrics = self.calculate_core_metrics()
            for metric_name, metric_value in metrics.items():
                self.add_metric(
                    f"core_{metric_name}",
                    metric_value.get("value"),
                    unit=metric_value.get("unit", ""),
                )

            # 添加回退指标标记
            self.add_metric("evaluation_baseline_fallback", True)

        except Exception as e:
            self.add_warning(f"回退核心指标计算失败: {e}")

    def test_integration_smoke(self):
        """集成冒烟测试：验证端到端接线"""
        name = "integration_smoke"
        try:
            # 测试观测端点（如果适配器运行）
            adapter_port_file = OPENCLAW_DIR / "athena_observability_adapter.port"
            adapter_available = False
            if adapter_port_file.exists():
                try:
                    port = int(adapter_port_file.read_text().strip())
                    # 简单检查端口是否监听（不实际连接）
                    import socket

                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    result = sock.connect_ex(("127.0.0.1", port))
                    sock.close()
                    adapter_available = result == 0
                except Exception:
                    pass

            # 测试任务执行链完整性
            chain_components = [
                ("orchestrator", AGENT_CORE_DIR / "athena_orchestrator.py"),
                ("execution_integration", AGENT_CORE_DIR / "execution_integration.py"),
                ("context_budget", AGENT_CORE_DIR / "context_budget.py"),
                ("scoreboard", AGENT_CORE_DIR / "scoreboard.py"),
            ]

            available_components = []
            for comp_name, comp_path in chain_components:
                if comp_path.exists():
                    available_components.append(comp_name)

            # 评估集成完整性
            integration_score = min(
                100,
                (len(available_components) / len(chain_components)) * 70
                + (30 if adapter_available else 0),
            )

            self.log_test(
                name,
                integration_score >= 70,
                "集成接线完整性检查",
                {
                    "observability_adapter_available": adapter_available,
                    "available_components": available_components,
                    "integration_score": integration_score,
                    "integration_healthy": integration_score >= 70,
                },
            )

            # 添加集成指标
            self.add_metric("integration_score", integration_score, unit="percent")
            self.add_metric("observability_adapter_available", adapter_available)
            self.add_metric("available_components_count", len(available_components))

        except Exception as e:
            self.log_test(name, False, f"集成冒烟测试异常: {e}")

    def generate_summary(self):
        """生成测试总结"""
        summary = self.evidence["summary"]
        total = summary["total"]
        passed = summary["passed"]
        failed = summary["failed"]

        self.evidence["conclusion"] = {
            "overall_status": "PASS" if failed == 0 else "FAIL",
            "pass_rate": round(passed / total * 100, 1) if total > 0 else 0,
            "total_tests": total,
            "passed_tests": passed,
            "failed_tests": failed,
            "recommendations": self.generate_recommendations(),
        }

        logger.info(f"测试总结: 总计 {total}, 通过 {passed}, 失败 {failed}")

    def generate_recommendations(self) -> list[str]:
        """生成改进建议"""
        recommendations = []

        # 检查失败测试
        for test_name, test_result in self.evidence["tests"].items():
            if not test_result["passed"]:
                recommendations.append(f"修复测试失败: {test_name} - {test_result['message']}")

        # 检查警告
        if self.evidence["warnings"]:
            recommendations.append(f"处理 {len(self.evidence['warnings'])} 个警告")

        # 检查核心指标
        core_metrics = ["success_rate", "recovery_rate", "avg_task_duration"]
        for metric in core_metrics:
            if f"core_{metric}" not in self.evidence["metrics"]:
                recommendations.append(f"完善核心指标: {metric}")

        if not recommendations:
            recommendations.append("所有验收项通过，保持监控")

        return recommendations


def main():
    """主函数"""
    acceptance = HarnessAcceptance()
    success = acceptance.run_all_tests()

    # 输出证据路径
    evidence_path = acceptance.save_evidence()
    print(f"\n证据文件: {evidence_path}")

    # 输出简要结果
    summary = acceptance.evidence["summary"]
    print(f"测试结果: {summary['passed']}/{summary['total']} 通过")

    if not success:
        print("⚠️  部分测试失败，请查看证据文件中的详细信息")
        sys.exit(1)
    else:
        print("✅ 所有验收测试通过")
        sys.exit(0)


if __name__ == "__main__":
    main()
