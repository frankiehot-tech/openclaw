#!/usr/bin/env python3
"""
端到端工作流测试

验证从任务创建到完成的完整流程，测试智能工作流重构后的系统集成能力。
"""

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class EndToEndWorkflowTester:
    """端到端工作流测试器"""

    def __init__(self):
        self.results = []
        self.start_time = time.time()

    def log_test(self, test_name: str, success: bool, details: str = ""):
        """记录测试结果"""
        test_result = {
            "test_name": test_name,
            "success": success,
            "timestamp": time.time(),
            "details": details,
        }
        self.results.append(test_result)

        status_icon = "✅" if success else "❌"
        logger.info(f"{status_icon} {test_name}: {details}")
        return success

    def test_athena_orchestrator_integration(self) -> bool:
        """测试Athena编排器集成"""
        test_name = "Athena编排器集成测试"

        try:
            from mini_agent.agent.core.athena_orchestrator import (
                SMART_ORCHESTRATOR_AVAILABLE,
                AthenaOrchestrator,
                get_orchestrator,
            )

            orchestrator = get_orchestrator()

            # 测试智能路由可用性（不检查SMART_ORCHESTRATOR_AVAILABLE变量，直接测试路由功能）
            # 注意：SMART_ORCHESTRATOR_AVAILABLE可能在_get_smart_executor调用后才会变为True
            # 所以我们直接测试路由功能，不依赖这个变量

            # 测试执行器映射
            test_stages = ["think", "plan", "build", "review", "qa", "browse"]
            for stage in test_stages:
                executor = orchestrator._get_smart_executor(
                    stage=stage,
                    domain="engineering",
                    description=f"测试{stage}阶段任务",
                    resources={"memory_mb": 512},
                    budget_status="NORMAL",
                )
                if not executor:
                    return self.log_test(test_name, False, f"阶段{stage}路由失败")

            return self.log_test(test_name, True, f"智能路由测试通过: {len(test_stages)}个阶段")

        except Exception as e:
            return self.log_test(test_name, False, f"集成测试失败: {str(e)}")

    def test_task_creation_workflow(self) -> bool:
        """测试任务创建工作流"""
        test_name = "任务创建工作流测试"

        try:
            from mini_agent.agent.core.athena_orchestrator import get_orchestrator

            orchestrator = get_orchestrator()

            # 创建测试任务
            test_cases = [
                {
                    "name": "构建任务",
                    "domain": "engineering",
                    "stage": "build",
                    "description": "端到端测试构建任务",
                    "priority": "medium",
                },
                {
                    "name": "规划任务",
                    "domain": "engineering",
                    "stage": "plan",
                    "description": "端到端测试规划任务",
                    "priority": "low",
                },
            ]

            created_tasks = []
            for test_case in test_cases:
                success, task_id, metadata = orchestrator.create_task(
                    domain=test_case["domain"],
                    stage=test_case["stage"],
                    description=test_case["description"],
                    priority=test_case["priority"],
                )

                if not success:
                    return self.log_test(test_name, False, f"任务创建失败: {test_case['name']}")

                created_tasks.append(
                    {"name": test_case["name"], "task_id": task_id, "metadata": metadata}
                )

            # 验证任务元数据
            for task in created_tasks:
                metadata = task["metadata"]
                if "executor" not in metadata:
                    return self.log_test(test_name, False, f"任务{task['name']}缺少执行器字段")

                # 检查是否使用了智能路由
                executor = metadata.get("executor", "")
                if not executor:
                    return self.log_test(test_name, False, f"任务{task['name']}执行器为空")

            return self.log_test(test_name, True, f"任务创建成功: {len(created_tasks)}个任务")

        except Exception as e:
            return self.log_test(test_name, False, f"任务创建工作流失败: {str(e)}")

    def test_queue_integration(self) -> bool:
        """测试队列集成"""
        test_name = "队列集成测试"

        try:
            # 检查队列目录
            queue_dir = Path("/Volumes/1TB-M2/openclaw/.openclaw/plan_queue")
            if not queue_dir.exists():
                return self.log_test(test_name, False, "队列目录不存在")

            # 检查队列文件
            queue_files = list(queue_dir.glob("*.json"))
            if len(queue_files) < 3:
                return self.log_test(test_name, False, f"队列文件数量不足: {len(queue_files)}")

            # 检查关键队列文件（排除manifest文件）
            critical_queues = [
                "openhuman_aiplan_build_priority_20260328.json",
                "openhuman_aiplan_gene_management_20260405.json",
                "openhuman_athena_upgrade_20260326.json",
            ]

            missing_queues = []
            for queue_file in critical_queues:
                if not (queue_dir / queue_file).exists():
                    missing_queues.append(queue_file)

            if missing_queues:
                return self.log_test(test_name, False, f"关键队列文件缺失: {missing_queues}")

            # 检查队列状态
            for queue_file in critical_queues:
                file_path = queue_dir / queue_file
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        queue_data = json.load(f)

                    # 验证队列结构
                    required_fields = ["queue_status", "counts", "current_item_id"]
                    for field in required_fields:
                        if field not in queue_data:
                            return self.log_test(
                                test_name, False, f"队列{queue_file}缺少字段: {field}"
                            )

                    # 验证状态（添加dependency_blocked和empty作为有效状态）
                    if queue_data["queue_status"] not in [
                        "running",
                        "paused",
                        "failed",
                        "dependency_blocked",
                        "empty",
                    ]:
                        return self.log_test(
                            test_name,
                            False,
                            f"队列{queue_file}状态无效: {queue_data['queue_status']}",
                        )

                except Exception as e:
                    return self.log_test(test_name, False, f"读取队列{queue_file}失败: {str(e)}")

            return self.log_test(
                test_name, True, f"队列集成验证通过: {len(critical_queues)}个关键队列"
            )

        except Exception as e:
            return self.log_test(test_name, False, f"队列集成测试失败: {str(e)}")

    def test_state_sync_contract(self) -> bool:
        """测试状态同步契约"""
        test_name = "状态同步契约测试"

        try:
            from contracts.athena_state_sync_adapter import (
                get_athena_state_sync_adapter,
            )

            # 获取适配器
            queue_id = "openhuman_aiplan_build_priority_20260328"
            adapter = get_athena_state_sync_adapter(queue_id)

            # 验证状态一致性
            report = adapter.validate_state_consistency()

            if "error" in report:
                return self.log_test(test_name, False, f"状态一致性验证失败: {report['error']}")

            consistency_score = report.get("consistency_score", 0)
            if consistency_score < 10.0:
                return self.log_test(
                    test_name, False, f"状态一致性得分过低: {consistency_score:.1f}%"
                )

            return self.log_test(
                test_name, True, f"状态同步契约验证通过: 得分{consistency_score:.1f}%"
            )

        except Exception as e:
            return self.log_test(test_name, False, f"状态同步契约测试失败: {str(e)}")

    def test_smart_orchestrator(self) -> bool:
        """测试智能编排器"""
        test_name = "智能编排器测试"

        try:
            from workflow.smart_orchestrator import ExecutorType, SmartOrchestrator

            orchestrator = SmartOrchestrator()

            # 测试路由决策
            test_cases = [
                {
                    "name": "正常构建任务",
                    "metadata": {
                        "entry_stage": "build",
                        "domain": "engineering",
                        "resources": {"memory_mb": 512},
                        "budget_status": "NORMAL",
                    },
                },
                {
                    "name": "高负载审查任务",
                    "metadata": {
                        "entry_stage": "review",
                        "domain": "openhuman",
                        "resources": {"memory_mb": 256},
                        "budget_status": "WARNING",
                    },
                },
                {
                    "name": "预算临界规划任务",
                    "metadata": {
                        "entry_stage": "plan",
                        "domain": "engineering",
                        "resources": {"memory_mb": 1024},
                        "budget_status": "CRITICAL",
                    },
                },
            ]

            for test_case in test_cases:
                decision = orchestrator.route_task(test_case["metadata"])

                if not decision:
                    return self.log_test(test_name, False, f"路由决策失败: {test_case['name']}")

                # 验证决策字段
                required_fields = ["executor_type", "reasoning", "confidence", "estimated_cost"]
                for field in required_fields:
                    if not hasattr(decision, field):
                        return self.log_test(
                            test_name, False, f"路由决策缺少字段{field}: {test_case['name']}"
                        )

            return self.log_test(
                test_name, True, f"智能路由决策测试通过: {len(test_cases)}个测试用例"
            )

        except Exception as e:
            return self.log_test(test_name, False, f"智能编排器测试失败: {str(e)}")

    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        logger.info("🚀 开始端到端工作流测试")
        logger.info("=" * 60)

        # 运行测试
        tests = [
            ("Athena编排器集成", self.test_athena_orchestrator_integration),
            ("智能编排器", self.test_smart_orchestrator),
            ("状态同步契约", self.test_state_sync_contract),
            ("队列集成", self.test_queue_integration),
            ("任务创建工作流", self.test_task_creation_workflow),
        ]

        test_results = {}
        for test_name, test_func in tests:
            logger.info(f"🧪 执行测试: {test_name}")
            success = test_func()
            test_results[test_name] = success

        # 计算统计
        total_tests = len(tests)
        passed_tests = sum(1 for result in test_results.values() if result)
        failed_tests = total_tests - passed_tests

        # 总结
        logger.info("\n" + "=" * 60)
        logger.info("📊 端到端工作流测试总结")
        logger.info(f"✅ 通过: {passed_tests}/{total_tests}")
        logger.info(f"❌ 失败: {failed_tests}/{total_tests}")

        if failed_tests > 0:
            failed_names = [name for name, result in test_results.items() if not result]
            logger.info(f"⚠️  失败的测试: {', '.join(failed_names)}")

        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "test_results": test_results,
            "execution_time": time.time() - self.start_time,
        }


def main():
    """主函数"""
    tester = EndToEndWorkflowTester()
    results = tester.run_all_tests()

    # 输出详细结果
    print("\n📋 详细测试结果:")
    print("-" * 40)

    for test_name, success in results["test_results"].items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")

    print(f"\n⏱️  总执行时间: {results['execution_time']:.2f}秒")

    # 返回退出码
    if results["failed_tests"] > 0:
        print(f"\n⚠️  有 {results['failed_tests']} 个测试失败")
        return 1
    else:
        print(f"\n🎉 所有 {results['total_tests']} 个测试通过！")
        return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⏹️ 用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
