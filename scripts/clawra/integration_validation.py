#!/usr/bin/env python3
"""
MAREF生产系统集成验证脚本
执行生产集成检查清单中的所有验证点
"""

import json
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

print("=== MAREF生产系统集成验证 ===")
print("开始时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
print()

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))


class IntegrationValidator:
    """集成验证器"""

    def __init__(self):
        self.results = []
        self.start_time = time.time()
        self.memory_db_path = "/Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db"

    def add_result(self, test_name, status, message, details=None):
        """添加测试结果"""
        result = {
            "test_name": test_name,
            "status": status,  # "pass", "fail", "warning"
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "details": details or {},
        }
        self.results.append(result)

        # 输出结果
        status_icon = "✅" if status == "pass" else "⚠️ " if status == "warning" else "❌"
        print(f"{status_icon} {test_name}: {message}")
        if details:
            for key, value in details.items():
                print(f"    {key}: {value}")
        print()

        return result

    def validate_database_connection(self):
        """验证数据库连接"""
        test_name = "数据库连接验证"
        try:
            if not os.path.exists(self.memory_db_path):
                return self.add_result(
                    test_name, "fail", f"内存数据库不存在: {self.memory_db_path}"
                )

            conn = sqlite3.connect(self.memory_db_path)
            cursor = conn.cursor()

            # 检查表结构
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            table_names = [t[0] for t in tables]

            # 检查关键表是否存在（基于实际架构）
            required_tables = ["memory_entries"]  # 必需的核心表
            missing_tables = [t for t in required_tables if t not in table_names]

            if missing_tables:
                conn.close()
                return self.add_result(
                    test_name,
                    "fail",
                    f"缺少核心表: {missing_tables}",
                    {"existing_tables": table_names},
                )

            # 检查关键条目类型是否存在
            cursor.execute("""
                SELECT entry_type, COUNT(*) as count, MAX(timestamp) as latest
                FROM memory_entries
                GROUP BY entry_type
                ORDER BY count DESC
            """)
            entry_stats = cursor.fetchall()

            # 检查是否有状态转换和智能体相关的条目
            entry_types = [stat[0] for stat in entry_stats]
            has_state_transitions = "state_transition" in entry_types
            has_agent_data = any(
                t in entry_types for t in ["agent_action", "agent_decision", "agent_metric"]
            )

            # 检查状态转换条目详情
            state_transition_count = 0
            latest_state_transition = None
            if has_state_transitions:
                cursor.execute("""
                    SELECT COUNT(*) as count, MAX(timestamp) as latest
                    FROM memory_entries
                    WHERE entry_type = 'state_transition'
                """)
                count_result = cursor.fetchone()
                state_transition_count = count_result[0] if count_result else 0
                latest_state_transition = count_result[1] if count_result else None

            conn.close()

            # 评估数据库状态
            if not has_state_transitions:
                return self.add_result(
                    test_name,
                    "warning",
                    "数据库连接成功，但缺少状态转换数据",
                    {
                        "tables": table_names,
                        "entry_types": entry_types,
                        "state_transition_count": state_transition_count,
                        "has_agent_data": has_agent_data,
                    },
                )
            else:
                return self.add_result(
                    test_name,
                    "pass",
                    f"数据库连接成功，包含 {state_transition_count} 条状态转换记录",
                    {
                        "tables": table_names,
                        "entry_types": entry_types,
                        "state_transition_count": state_transition_count,
                        "latest_state_transition": latest_state_transition,
                        "has_agent_data": has_agent_data,
                        "total_entry_types": len(entry_types),
                    },
                )

        except Exception as e:
            return self.add_result(test_name, "fail", f"数据库连接失败: {e}")

    def validate_maref_components(self):
        """验证MAREF组件导入和实例化"""
        test_name = "MAREF组件验证"
        try:
            # 1. 导入MAREF内存管理器
            from maref_memory_manager import MAREFMemoryManager

            memory_manager = MAREFMemoryManager()

            # 2. 导入状态管理器
            from external.ROMA.hexagram_state_manager import HexagramStateManager

            # 从数据库获取当前状态
            current_state = self._get_current_state_from_db()
            if not current_state:
                current_state = "000000"

            state_manager = HexagramStateManager(current_state)

            # 3. 导入智能体
            from external.ROMA.communicator_agent import CommunicatorAgent
            from external.ROMA.explorer_agent import ExplorerAgent
            from external.ROMA.guardian_agent import GuardianAgent, SecurityLevel
            from external.ROMA.learner_agent import LearnerAgent

            # 4. 实例化智能体
            agents = {
                "guardian": GuardianAgent(
                    agent_id="guardian_test", security_level=SecurityLevel.MEDIUM
                ),
                "communicator": CommunicatorAgent(agent_id="communicator_test"),
                "learner": LearnerAgent(agent_id="learner_test"),
                "explorer": ExplorerAgent(agent_id="explorer_test"),
            }

            # 5. 验证智能体属性
            agent_info = {}
            for name, agent in agents.items():
                agent_info[name] = {
                    "agent_id": agent.agent_id,
                    "agent_type": getattr(agent, "agent_type", "unknown"),
                    "has_decision_method": (
                        hasattr(agent, "assess_communication_impact")
                        if name == "communicator"
                        else (
                            hasattr(agent, "validate_state_transition_safety")
                            if name == "guardian"
                            else (
                                hasattr(agent, "recommend_state_transition")
                                if name == "learner"
                                else (
                                    hasattr(agent, "evaluate_exploration_value")
                                    if name == "explorer"
                                    else False
                                )
                            )
                        )
                    ),
                }

            return self.add_result(
                test_name,
                "pass",
                "MAREF组件导入和实例化成功",
                {
                    "current_state": current_state,
                    "hexagram_name": state_manager.get_hexagram_name(),
                    "agents_count": len(agents),
                    "agent_details": agent_info,
                },
            )

        except Exception as e:
            import traceback

            return self.add_result(
                test_name, "fail", f"MAREF组件验证失败: {e}", {"traceback": traceback.format_exc()}
            )

    def validate_monitor_system(self):
        """验证监控系统数据采集"""
        test_name = "监控系统验证"
        try:
            # 创建集成环境
            from run_maref_daily_report import create_integration_environment

            state_manager, agents = create_integration_environment()

            # 初始化监控器
            from maref_monitor import MAREFMonitor

            monitor = MAREFMonitor(state_manager, agents)

            # 收集数据
            logger.info("收集监控数据...")
            metrics = monitor.collect_all_metrics()

            # 验证数据内容
            if not metrics:
                return self.add_result(test_name, "warning", "监控器收集到空数据")

            # 检查关键指标（基于实际监控器输出格式）
            # 实际字段: timestamp, system, maref, agents
            required_keys = ["timestamp", "system", "maref", "agents"]
            missing_keys = [k for k in required_keys if k not in metrics]

            if missing_keys:
                return self.add_result(
                    test_name,
                    "warning",
                    f"监控数据缺少关键字段: {missing_keys}",
                    {"available_keys": list(metrics.keys())},
                )

            # 检查智能体数据
            agents_data = metrics.get("agents", {})
            if not agents_data:
                return self.add_result(test_name, "warning", "监控数据缺少智能体信息")

            agent_count = len(agents_data)

            # 检查MAREF数据（包含卦象状态）
            maref_data = metrics.get("maref", {})
            has_hexagram_info = "hexagram_state" in maref_data or "control_entropy" in maref_data

            # 检查系统数据
            system_data = metrics.get("system", {})
            has_system_metrics = "cpu_usage" in system_data or "memory_usage" in system_data

            return self.add_result(
                test_name,
                "pass",
                f"监控系统数据采集成功，收集到 {agent_count} 个智能体数据",
                {
                    "agent_count": agent_count,
                    "has_hexagram_info": has_hexagram_info,
                    "has_system_metrics": has_system_metrics,
                    "metrics_keys": list(metrics.keys()),
                    "sample_agent": list(agents_data.keys())[0] if agents_data else None,
                    "maref_keys": list(maref_data.keys()) if maref_data else [],
                    "system_keys": list(system_data.keys()) if system_data else [],
                },
            )

        except Exception as e:
            import traceback

            return self.add_result(
                test_name, "fail", f"监控系统验证失败: {e}", {"traceback": traceback.format_exc()}
            )

    def validate_daily_report_system(self):
        """验证日报系统"""
        test_name = "日报系统验证"
        try:
            # 运行日报生成
            from run_maref_daily_report import run_daily_report

            report_path = run_daily_report(mode="integration")

            if not report_path:
                return self.add_result(test_name, "fail", "日报生成失败，返回路径为空")

            # 检查报告文件
            if not os.path.exists(report_path):
                return self.add_result(test_name, "fail", f"日报文件不存在: {report_path}")

            # 读取报告内容
            with open(report_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 检查关键内容
            required_sections = ["核心稳定性状态", "智能体健康度报告", "系统性能指标"]
            missing_sections = [s for s in required_sections if s not in content]

            if missing_sections:
                return self.add_result(
                    test_name,
                    "warning",
                    f"日报缺少部分章节: {missing_sections}",
                    {"report_path": report_path, "content_length": len(content)},
                )

            # 检查是否包含实际数据标记
            has_actual_data = False
            actual_data_indicators = ["䷗", "000001", "地雷复", "控制熵"]
            for indicator in actual_data_indicators:
                if indicator in content:
                    has_actual_data = True
                    break

            return self.add_result(
                test_name,
                "pass" if has_actual_data else "warning",
                f"日报生成成功: {report_path}",
                {
                    "report_path": report_path,
                    "content_length": len(content),
                    "has_actual_data": has_actual_data,
                    "file_size_kb": os.path.getsize(report_path) / 1024,
                },
            )

        except Exception as e:
            import traceback

            return self.add_result(
                test_name, "fail", f"日报系统验证失败: {e}", {"traceback": traceback.format_exc()}
            )

    def validate_agent_collaboration(self):
        """验证智能体协同"""
        test_name = "智能体协同验证"
        try:
            # 创建智能体
            from external.ROMA.communicator_agent import CommunicatorAgent
            from external.ROMA.explorer_agent import ExplorerAgent
            from external.ROMA.guardian_agent import GuardianAgent, SecurityLevel
            from external.ROMA.learner_agent import LearnerAgent

            agents = {
                "guardian": GuardianAgent(
                    agent_id="guardian_collab", security_level=SecurityLevel.MEDIUM
                ),
                "communicator": CommunicatorAgent(agent_id="communicator_collab"),
                "learner": LearnerAgent(agent_id="learner_collab"),
                "explorer": ExplorerAgent(agent_id="explorer_collab"),
            }

            # 测试协同决策
            test_state_from = "000001"
            test_state_to = "000011"

            collaboration_results = {}

            for name, agent in agents.items():
                try:
                    if name == "guardian" and hasattr(agent, "validate_state_transition_safety"):
                        result = agent.validate_state_transition_safety(
                            test_state_from, test_state_to
                        )
                        collaboration_results[name] = {
                            "decision": result.get("decision", "unknown"),
                            "confidence": result.get("confidence", 0),
                            "has_method": True,
                        }
                    elif name == "communicator" and hasattr(agent, "assess_communication_impact"):
                        result = agent.assess_communication_impact(test_state_from, test_state_to)
                        collaboration_results[name] = {
                            "decision": result.get("decision", "unknown"),
                            "confidence": result.get("confidence", 0),
                            "has_method": True,
                        }
                    elif name == "learner" and hasattr(agent, "recommend_state_transition"):
                        result = agent.recommend_state_transition(test_state_from, test_state_to)
                        collaboration_results[name] = {
                            "recommendation": result.get("recommendation", "unknown"),
                            "confidence": result.get("confidence", 0),
                            "has_method": True,
                        }
                    elif name == "explorer" and hasattr(agent, "evaluate_exploration_value"):
                        result = agent.evaluate_exploration_value(test_state_from, test_state_to)
                        collaboration_results[name] = {
                            "value": result.get("exploration_value", 0),
                            "confidence": result.get("confidence", 0),
                            "has_method": True,
                        }
                    else:
                        collaboration_results[name] = {"has_method": False}

                except Exception as e:
                    collaboration_results[name] = {"error": str(e), "has_method": False}

            # 评估协同能力
            agents_with_methods = sum(
                1 for r in collaboration_results.values() if r.get("has_method")
            )
            total_agents = len(agents)

            method_coverage = agents_with_methods / total_agents

            return self.add_result(
                test_name,
                "pass" if method_coverage >= 0.75 else "warning",
                f"智能体协同验证完成，方法覆盖率: {method_coverage:.1%}",
                {
                    "total_agents": total_agents,
                    "agents_with_methods": agents_with_methods,
                    "method_coverage": method_coverage,
                    "collaboration_results": collaboration_results,
                },
            )

        except Exception as e:
            import traceback

            return self.add_result(
                test_name, "fail", f"智能体协同验证失败: {e}", {"traceback": traceback.format_exc()}
            )

    def validate_performance_metrics(self):
        """验证性能指标"""
        test_name = "性能指标验证"
        try:
            performance_data = []

            # 1. 状态转换响应时间测试
            logger.info("测试状态转换响应时间...")

            # 使用集成环境获取包装后的状态管理器
            import maref_memory_integration
            from external.ROMA.hexagram_state_manager import HexagramStateManager
            from run_maref_daily_report import create_integration_environment

            # 测试两种模式：性能模式和正常模式
            test_modes = [(True, "性能模式"), (False, "正常模式")]

            for performance_mode, mode_name in test_modes:
                logger.info(f"测试{mode_name}...")

                # 重新初始化内存管理器以启用性能模式
                # 首先关闭现有内存管理器（如果存在）
                try:
                    memory_manager = maref_memory_integration.get_memory_manager()
                    if hasattr(memory_manager, "close"):
                        memory_manager.close()
                except:
                    pass

                # 清除单例实例
                import sys

                if "maref_memory_integration" in sys.modules:
                    import importlib

                    importlib.reload(maref_memory_integration)

                # 重新初始化内存管理器
                from maref_memory_integration import get_memory_manager

                global _memory_manager_instance
                _memory_manager_instance = None
                memory_manager = get_memory_manager(performance_mode=performance_mode)

                # 通过集成环境获取包装后的状态管理器
                wrapped_state_manager, _ = create_integration_environment()

                # 验证包装后的状态管理器有正确的参数签名
                import inspect

                sig = inspect.signature(wrapped_state_manager.transition)
                param_names = list(sig.parameters.keys())

                logger.info(f"{mode_name}状态管理器transition方法参数: {param_names}")

                # 测试转换
                test_transitions = [
                    ("000001", "单步转换"),
                    ("000011", "两步转换"),
                    ("000111", "三步转换"),
                ]

                for state, description in test_transitions:
                    start_time = time.time()

                    # 根据参数签名决定调用方式
                    if "trigger_agent" in param_names:
                        # 包装后的版本
                        success = wrapped_state_manager.transition(
                            new_state=state, trigger_agent="validator", reason="性能测试"
                        )
                    else:
                        # 原始版本
                        success = wrapped_state_manager.transition(new_state=state)

                    elapsed = time.time() - start_time

                    performance_data.append(
                        {
                            "test": f"state_transition_{mode_name}_{description}",
                            "elapsed_ms": elapsed * 1000,
                            "success": success,
                            "wrapped": "trigger_agent" in param_names,
                            "performance_mode": performance_mode,
                            "mode": mode_name,
                        }
                    )

            # 2. 智能体决策时间测试
            logger.info("测试智能体决策时间...")
            from external.ROMA.guardian_agent import GuardianAgent, SecurityLevel

            guardian = GuardianAgent(agent_id="guardian_perf", security_level=SecurityLevel.MEDIUM)

            if hasattr(guardian, "validate_state_transition_safety"):
                start_time = time.time()
                result = guardian.validate_state_transition_safety("000000", "000001")
                elapsed = time.time() - start_time

                performance_data.append(
                    {
                        "test": "guardian_decision",
                        "elapsed_ms": elapsed * 1000,
                        "confidence": result.get("confidence", 0),
                    }
                )

            # 分析性能数据
            state_transition_times = [
                d["elapsed_ms"]
                for d in performance_data
                if d["test"].startswith("state_transition")
            ]
            avg_transition_time = (
                sum(state_transition_times) / len(state_transition_times)
                if state_transition_times
                else 0
            )

            # 分别计算性能模式和正常模式的平均时间
            perf_mode_times = [
                d["elapsed_ms"]
                for d in performance_data
                if d["test"].startswith("state_transition") and d.get("performance_mode") == True
            ]
            normal_mode_times = [
                d["elapsed_ms"]
                for d in performance_data
                if d["test"].startswith("state_transition") and d.get("performance_mode") == False
            ]

            avg_perf_mode_time = (
                sum(perf_mode_times) / len(perf_mode_times) if perf_mode_times else 0
            )
            avg_normal_mode_time = (
                sum(normal_mode_times) / len(normal_mode_times) if normal_mode_times else 0
            )

            # 性能标准
            transition_threshold = 0.5  # 0.5ms

            # 检查性能模式是否达标
            meets_performance = (
                avg_perf_mode_time <= transition_threshold if perf_mode_times else False
            )
            normal_mode_meets = (
                avg_normal_mode_time <= transition_threshold if normal_mode_times else False
            )

            # 生成详细报告
            if perf_mode_times and normal_mode_times:
                message = f"性能测试完成:\n"
                message += f"  性能模式平均时间: {avg_perf_mode_time:.3f}ms ({'达标' if meets_performance else '未达标'})\n"
                message += f"  正常模式平均时间: {avg_normal_mode_time:.3f}ms ({'达标' if normal_mode_meets else '未达标'})\n"
                message += f"  性能阈值: {transition_threshold}ms"
            else:
                message = f"性能测试完成，平均状态转换时间: {avg_transition_time:.3f}ms"

            # 确定测试结果状态
            # 主要看性能模式是否达标
            status = "pass" if meets_performance else "warning"

            return self.add_result(
                test_name,
                status,
                message,
                {
                    "avg_transition_time_ms": avg_transition_time,
                    "avg_performance_mode_time_ms": avg_perf_mode_time,
                    "avg_normal_mode_time_ms": avg_normal_mode_time,
                    "performance_threshold_ms": transition_threshold,
                    "performance_mode_meets": meets_performance,
                    "normal_mode_meets": normal_mode_meets,
                    "performance_data": performance_data,
                },
            )

        except Exception as e:
            import traceback

            return self.add_result(
                test_name, "fail", f"性能指标验证失败: {e}", {"traceback": traceback.format_exc()}
            )

    def _get_current_state_from_db(self):
        """从数据库获取当前状态"""
        if not os.path.exists(self.memory_db_path):
            return None

        try:
            conn = sqlite3.connect(self.memory_db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT content_json, timestamp, source_agent
                FROM memory_entries
                WHERE entry_type = 'state_transition'
                ORDER BY timestamp DESC
                LIMIT 1
            """)

            result = cursor.fetchone()
            conn.close()

            if result:
                content_json, timestamp, source_agent = result
                try:
                    content = json.loads(content_json)
                    to_state = content.get("to_state")
                    if to_state and len(to_state) == 6:
                        return to_state
                except json.JSONDecodeError:
                    pass

        except Exception:
            pass

        return None

    def run_all_tests(self):
        """运行所有测试"""
        print("开始执行集成验证测试...")
        print()

        # 执行测试
        tests = [
            ("数据库连接验证", self.validate_database_connection),
            ("MAREF组件验证", self.validate_maref_components),
            ("监控系统验证", self.validate_monitor_system),
            ("日报系统验证", self.validate_daily_report_system),
            ("智能体协同验证", self.validate_agent_collaboration),
            ("性能指标验证", self.validate_performance_metrics),
        ]

        for test_name, test_func in tests:
            print(f"执行测试: {test_name}")
            print("-" * 40)
            test_func()

        # 生成总结报告
        self.generate_summary_report()

    def generate_summary_report(self):
        """生成总结报告"""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r["status"] == "pass")
        warning_tests = sum(1 for r in self.results if r["status"] == "warning")
        failed_tests = sum(1 for r in self.results if r["status"] == "fail")

        success_rate = passed_tests / total_tests if total_tests > 0 else 0

        elapsed_time = time.time() - self.start_time

        print()
        print("=" * 60)
        print("集成验证总结报告")
        print("=" * 60)
        print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"总耗时: {elapsed_time:.2f}秒")
        print(f"测试总数: {total_tests}")
        print(f"✅ 通过: {passed_tests}")
        print(f"⚠️  警告: {warning_tests}")
        print(f"❌ 失败: {failed_tests}")
        print(f"成功率: {success_rate:.1%}")
        print()

        # 详细结果
        print("详细结果:")
        for result in self.results:
            status_icon = (
                "✅"
                if result["status"] == "pass"
                else "⚠️ " if result["status"] == "warning" else "❌"
            )
            print(f"  {status_icon} {result['test_name']}: {result['message']}")

        print()
        print("建议:")

        if failed_tests > 0:
            print("❌ 存在失败的测试，需要优先修复")
            for result in self.results:
                if result["status"] == "fail":
                    print(f"  - 修复: {result['test_name']} - {result['message']}")

        if warning_tests > 0:
            print("⚠️  存在警告的测试，建议优化")
            for result in self.results:
                if result["status"] == "warning":
                    print(f"  - 优化: {result['test_name']} - {result['message']}")

        if success_rate >= 0.8:
            print("✅ 集成验证基本成功，可以推进生产部署")
        elif success_rate >= 0.6:
            print("⚠️  集成验证部分成功，需要解决关键问题后再部署")
        else:
            print("❌ 集成验证失败，需要全面修复问题")

        # 保存结果到文件
        self.save_results_to_file()

    def save_results_to_file(self):
        """保存结果到文件"""
        output_file = Path(__file__).parent / "integration_validation_results.json"

        report_data = {
            "validation_date": datetime.now().isoformat(),
            "total_tests": len(self.results),
            "passed_tests": sum(1 for r in self.results if r["status"] == "pass"),
            "warning_tests": sum(1 for r in self.results if r["status"] == "warning"),
            "failed_tests": sum(1 for r in self.results if r["status"] == "fail"),
            "results": self.results,
            "summary": self._generate_summary_text(),
        }

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            logger.info(f"验证结果已保存到: {output_file}")
        except Exception as e:
            logger.error(f"保存验证结果失败: {e}")

    def _generate_summary_text(self):
        """生成总结文本"""
        passed = sum(1 for r in self.results if r["status"] == "pass")
        total = len(self.results)
        success_rate = passed / total if total > 0 else 0

        if success_rate >= 0.8:
            return "✅ 集成验证成功 - 可以推进生产部署"
        elif success_rate >= 0.6:
            return "⚠️  集成验证部分成功 - 需要解决关键问题"
        else:
            return "❌ 集成验证失败 - 需要全面修复"


def main():
    """主函数"""
    validator = IntegrationValidator()

    try:
        validator.run_all_tests()
        return 0
    except KeyboardInterrupt:
        print("\n验证被用户中断")
        return 1
    except Exception as e:
        print(f"验证过程发生异常: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
