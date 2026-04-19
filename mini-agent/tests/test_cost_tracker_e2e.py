#!/usr/bin/env python3
"""
成本跟踪系统端到端测试

测试完整的成本跟踪流程：
1. 模拟OpenCode包装器调用环境
2. 通过成本跟踪集成记录成本
3. 验证数据存储和检索
4. 运行分析引擎处理
5. 生成可视化报告

设计为集成测试，覆盖全链条数据完整性。
"""

import json
import os
import shutil
import sys
import tempfile
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, Mock, patch

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 添加 mini-agent 目录到路径
mini_agent_dir = project_root / "mini-agent"
if str(mini_agent_dir) not in sys.path:
    sys.path.insert(0, str(mini_agent_dir))

from mini_agent.agent.core.cost_estimation_strategy import CostEstimationStrategy
from mini_agent.agent.core.cost_tracker import (
    CostRecord,
    CostSummary,
    CostTracker,
    MemoryStorageBackend,
    SQLiteStorageBackend,
    StorageBackend,
)
from mini_agent.agent.core.cost_tracker_analytics import CostAnalyticsEngine
from mini_agent.agent.core.cost_tracker_integration import (
    CostTrackingIntegration,
    TokenEstimator,
)
from mini_agent.agent.core.cost_tracker_json_storage import JSONStorageBackend
from mini_agent.agent.core.cost_tracker_reports import CostReportGenerator
from mini_agent.agent.core.provider_registry import get_provider_cost_config


class TestCostTrackerE2E:
    """端到端成本跟踪测试"""

    def setup_method(self):
        """每个测试方法前执行"""
        # 创建临时目录用于测试
        self.temp_dir = tempfile.mkdtemp(prefix="cost_e2e_test_")
        self.db_path = Path(self.temp_dir) / "e2e_test.db"
        self.json_path = Path(self.temp_dir) / "e2e_test.json"

        # 初始化成本跟踪器
        self.cost_tracker = CostTracker(
            storage_backend="sqlite", config={"db_path": str(self.db_path)}
        )

        # 初始化成本跟踪集成
        self.integration = CostTrackingIntegration(cost_tracker=self.cost_tracker)

        # 初始化分析引擎
        self.analytics_engine = CostAnalyticsEngine(cost_tracker=self.cost_tracker)

        # 初始化报告生成器
        self.report_generator = CostReportGenerator(cost_tracker=self.cost_tracker)

        # 模拟provider配置
        self.provider_config = {
            "deepseek": {
                "name": "DeepSeek",
                "models": {
                    "deepseek-chat": {
                        "input_cost_per_million": 0.27,  # 美元/百万tokens
                        "output_cost_per_million": 0.54,
                    }
                },
            },
            "dashscope": {
                "name": "DashScope",
                "models": {
                    "qwen3.5-plus": {
                        "input_cost_per_million": 0.40,
                        "output_cost_per_million": 0.80,
                    }
                },
            },
        }

        # 模拟API响应数据
        self.mock_api_response = {
            "usage": {"prompt_tokens": 150, "completion_tokens": 75, "total_tokens": 225},
            "model": "deepseek-chat",
        }

        # 模拟provider替代脚本输出
        self.mock_script_output = json.dumps(
            {"usage": {"prompt_tokens": 120, "completion_tokens": 60}, "model": "qwen3.5-plus"}
        )

        print(f"测试环境初始化完成，临时目录: {self.temp_dir}")

    def teardown_method(self):
        """每个测试方法后执行"""
        # 清理临时目录
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        print(f"清理临时目录: {self.temp_dir}")

    def test_full_integration_workflow(self):
        """测试完整集成工作流"""
        print("\n=== 测试完整集成工作流 ===")

        # 步骤1: 模拟provider请求
        print("1. 模拟provider请求...")
        request_id = "req_e2e_001"
        provider_id = "deepseek"
        model_id = "deepseek-chat"
        task_kind = "code_review"
        input_text = "请审查以下代码：def hello(): return 'world'"

        # 步骤2: 通过集成记录成本
        print("2. 通过集成记录成本...")
        record_id = self.integration.record_provider_request(
            request_id=request_id,
            provider_id=provider_id,
            model_id=model_id,
            task_kind=task_kind,
            input_text=input_text,
            api_response=self.mock_api_response,
            estimated_tokens=False,
        )

        assert record_id is not None
        print(f"   成本记录ID: {record_id}")

        # 步骤3: 验证记录已保存
        print("3. 验证记录已保存...")
        records = self.cost_tracker.get_records()
        assert len(records) == 1

        record = records[0]
        assert record.request_id == request_id
        assert record.provider_id == provider_id
        assert record.model_id == model_id
        assert record.task_kind == task_kind
        assert record.input_tokens == 150  # 来自mock_api_response
        assert record.output_tokens == 75  # 来自mock_api_response
        assert record.estimated_cost > 0
        print(f"   记录验证成功: {record.id}")

        # 步骤4: 运行分析引擎
        print("4. 运行分析引擎...")

        # 趋势分析
        trend_analysis = self.analytics_engine.get_trend_analysis(granularity="daily")
        assert trend_analysis["success"] == True
        print(
            f"   趋势分析完成: {trend_analysis['period']['start']} 到 {trend_analysis['period']['end']}"
        )

        # provider对比分析
        provider_comparison = self.analytics_engine.get_provider_comparison()
        assert provider_comparison["success"] == True
        print(f"   provider对比分析完成: {len(provider_comparison['providers'])} 个provider")

        # 任务类型分析
        task_kind_analysis = self.analytics_engine.get_task_kind_analysis()
        assert task_kind_analysis["success"] == True
        print(f"   任务类型分析完成: {len(task_kind_analysis['task_kind_analysis'])} 种任务类型")

        # 步骤5: 生成报告
        print("5. 生成报告...")

        # 文本报告
        text_report = self.report_generator.generate_text_report(
            period="today", output_format="summary"
        )
        assert text_report["success"] == True
        print(f"   文本报告生成成功: {text_report['report_type']}")

        # 可视化报告（如果可用）
        try:
            rich_report = self.report_generator.generate_rich_report(period="today")
            if rich_report["success"]:
                print(f"   可视化报告生成成功: {rich_report['report_type']}")
        except Exception as e:
            print(f"   可视化报告跳过（可能缺少rich库）: {e}")

        # 步骤6: 验证成本摘要
        print("6. 验证成本摘要...")
        summary = self.cost_tracker.get_summary()
        assert summary.total_requests == 1
        assert summary.total_cost > 0
        assert summary.total_input_tokens == 150
        assert summary.total_output_tokens == 75
        assert provider_id in summary.by_provider
        assert model_id in summary.by_model
        assert task_kind in summary.by_task_kind

        print(f"   成本摘要验证成功:")
        print(f"     - 总请求数: {summary.total_requests}")
        print(f"     - 总成本: ${summary.total_cost:.6f}")
        print(f"     - 总输入tokens: {summary.total_input_tokens}")
        print(f"     - 总输出tokens: {summary.total_output_tokens}")

        print("=== 完整集成工作流测试通过 ===")

    def test_multiple_providers_and_models(self):
        """测试多provider和多模型场景"""
        print("\n=== 测试多provider和多模型场景 ===")

        # 模拟不同provider和模型的请求
        test_cases = [
            {
                "provider": "deepseek",
                "model": "deepseek-chat",
                "task": "code_review",
                "input_tokens": 200,
                "output_tokens": 100,
            },
            {
                "provider": "deepseek",
                "model": "deepseek-coder",
                "task": "code_generation",
                "input_tokens": 150,
                "output_tokens": 300,
            },
            {
                "provider": "dashscope",
                "model": "qwen3.5-plus",
                "task": "documentation",
                "input_tokens": 180,
                "output_tokens": 120,
            },
            {
                "provider": "dashscope",
                "model": "qwen2.5-coder",
                "task": "debugging",
                "input_tokens": 220,
                "output_tokens": 80,
            },
        ]

        for i, test_case in enumerate(test_cases):
            request_id = f"req_multi_{i:03d}"

            # 模拟API响应
            mock_response = {
                "usage": {
                    "prompt_tokens": test_case["input_tokens"],
                    "completion_tokens": test_case["output_tokens"],
                    "total_tokens": test_case["input_tokens"] + test_case["output_tokens"],
                },
                "model": test_case["model"],
            }

            # 记录成本
            record_id = self.integration.record_provider_request(
                request_id=request_id,
                provider_id=test_case["provider"],
                model_id=test_case["model"],
                task_kind=test_case["task"],
                input_text="测试输入文本",
                api_response=mock_response,
                estimated_tokens=False,
            )

            assert record_id is not None
            print(
                f"   记录 {i+1}: {test_case['provider']}/{test_case['model']} - {test_case['task']}"
            )

        # 验证所有记录
        records = self.cost_tracker.get_records()
        assert len(records) == len(test_cases)

        # 验证成本摘要
        summary = self.cost_tracker.get_summary()
        assert summary.total_requests == len(test_cases)

        # 验证每个provider的成本
        for test_case in test_cases:
            provider = test_case["provider"]
            model = test_case["model"]
            task = test_case["task"]

            # 验证provider存在
            assert provider in summary.by_provider, f"Provider {provider} 未在摘要中找到"

            # 验证模型存在
            assert model in summary.by_model, f"Model {model} 未在摘要中找到"

            # 验证任务类型存在
            assert task in summary.by_task_kind, f"Task kind {task} 未在摘要中找到"

        print(f"   总请求数: {summary.total_requests}")
        print(f"   总成本: ${summary.total_cost:.6f}")
        print(f"   Provider分布: {list(summary.by_provider.keys())}")
        print(f"   模型分布: {list(summary.by_model.keys())}")

        print("=== 多provider和多模型场景测试通过 ===")

    def test_token_estimation_fallback(self):
        """测试token估算fallback策略"""
        print("\n=== 测试token估算fallback策略 ===")

        # 测试场景1: 有API响应（最准确）
        print("1. 测试有API响应的场景...")
        record_id1 = self.integration.record_provider_request(
            request_id="req_fallback_001",
            provider_id="deepseek",
            model_id="deepseek-chat",
            task_kind="testing",
            input_text="这是一个测试文本。",
            api_response=self.mock_api_response,  # 提供API响应
            estimated_tokens=False,
        )

        records1 = self.cost_tracker.get_records(limit=1)
        record1 = records1[0]
        assert record1.input_tokens == 150  # 来自API响应
        assert record1.output_tokens == 75
        assert record1.estimated_tokens == False
        print(
            f"   API响应模式: 输入tokens={record1.input_tokens}, 输出tokens={record1.output_tokens}"
        )

        # 测试场景2: 只有脚本输出
        print("2. 测试只有脚本输出的场景...")
        record_id2 = self.integration.record_provider_request(
            request_id="req_fallback_002",
            provider_id="dashscope",
            model_id="qwen3.5-plus",
            task_kind="testing",
            input_text="这是另一个测试文本。",
            api_response=None,  # 无API响应
            provider_script_output=self.mock_script_output,  # 提供脚本输出
            estimated_tokens=False,
        )

        records2 = self.cost_tracker.get_records(limit=1)
        record2 = records2[0]
        assert record2.input_tokens == 120  # 来自脚本输出
        assert record2.output_tokens == 60
        assert record2.estimated_tokens == False
        print(
            f"   脚本输出模式: 输入tokens={record2.input_tokens}, 输出tokens={record2.output_tokens}"
        )

        # 测试场景3: 只有输入文本（需要估算）
        print("3. 测试只有输入文本的场景（估算模式）...")
        input_text = "这是一个需要估算token的测试文本。This is an English test text."
        record_id3 = self.integration.record_provider_request(
            request_id="req_fallback_003",
            provider_id="deepseek",
            model_id="deepseek-chat",
            task_kind="testing",
            input_text=input_text,
            api_response=None,  # 无API响应
            provider_script_output=None,  # 无脚本输出
            estimated_tokens=True,  # 启用估算
        )

        records3 = self.cost_tracker.get_records(limit=1)
        record3 = records3[0]
        assert record3.input_tokens > 0  # 估算值应该>0
        assert record3.output_tokens == 0  # 仅输入文本，无输出
        assert record3.estimated_tokens == True
        print(f"   估算模式: 输入tokens={record3.input_tokens}, 输出tokens={record3.output_tokens}")

        print("=== token估算fallback策略测试通过 ===")

    def test_storage_backend_migration(self):
        """测试存储后端迁移"""
        print("\n=== 测试存储后端迁移 ===")

        # 创建多个存储后端
        sqlite_backend = SQLiteStorageBackend(db_path=str(self.db_path))
        json_backend = JSONStorageBackend(file_path=str(self.json_path))
        memory_backend = MemoryStorageBackend(max_records=100)

        # 向SQLite添加测试数据
        test_records = []
        for i in range(5):
            record = CostRecord(
                id=f"test_mig_{i:03d}",
                request_id=f"req_mig_{i:03d}",
                timestamp=datetime.now() - timedelta(days=i),
                recorded_at=datetime.now(),
                provider_id="deepseek" if i % 2 == 0 else "dashscope",
                model_id="deepseek-chat" if i % 2 == 0 else "qwen3.5-plus",
                task_kind="migration_test",
                input_tokens=100 * (i + 1),
                output_tokens=50 * (i + 1),
                estimated_cost=0.001 * (i + 1),
                estimated_tokens=False,
            )
            sqlite_backend.record_cost(record)
            test_records.append(record)

        print(f"   SQLite中创建了 {len(test_records)} 条测试记录")

        # 从SQLite读取
        sqlite_records = sqlite_backend.get_records()
        assert len(sqlite_records) == 5

        # 迁移到JSON
        for record in sqlite_records:
            json_backend.record_cost(record)

        json_records = json_backend.get_records()
        assert len(json_records) == 5
        print(f"   成功迁移到JSON存储: {len(json_records)} 条记录")

        # 迁移到内存
        for record in json_records:
            memory_backend.record_cost(record)

        memory_records = memory_backend.get_records()
        assert len(memory_records) == 5
        print(f"   成功迁移到内存存储: {len(memory_records)} 条记录")

        # 验证数据一致性
        for i in range(5):
            sqlite_record = sqlite_records[i]
            json_record = json_records[i]
            memory_record = memory_records[i]

            assert sqlite_record.id == json_record.id == memory_record.id
            assert sqlite_record.provider_id == json_record.provider_id == memory_record.provider_id
            assert (
                sqlite_record.input_tokens == json_record.input_tokens == memory_record.input_tokens
            )

        print("=== 存储后端迁移测试通过 ===")

    def test_performance_and_scalability(self):
        """测试性能和扩展性"""
        print("\n=== 测试性能和扩展性 ===")

        batch_size = 100
        print(f"   批量插入 {batch_size} 条记录...")

        start_time = time.time()

        # 批量插入记录
        for i in range(batch_size):
            record = CostRecord(
                id=f"perf_test_{i:06d}",
                request_id=f"req_perf_{i:06d}",
                timestamp=datetime.now() - timedelta(minutes=i),
                recorded_at=datetime.now(),
                provider_id="deepseek" if i % 3 == 0 else "dashscope" if i % 3 == 1 else "openai",
                model_id=(
                    "deepseek-chat" if i % 3 == 0 else "qwen3.5-plus" if i % 3 == 1 else "gpt-4"
                ),
                task_kind="performance_test",
                input_tokens=100 + (i % 10) * 10,
                output_tokens=50 + (i % 10) * 5,
                estimated_cost=0.001 * (i % 5 + 1),
                estimated_tokens=False,
            )
            self.cost_tracker.record_request(
                request_id=record.request_id,
                provider_id=record.provider_id,
                model_id=record.model_id,
                task_kind=record.task_kind,
                input_tokens=record.input_tokens,
                output_tokens=record.output_tokens,
                estimated_tokens=record.estimated_tokens,
            )

        insert_time = time.time() - start_time
        print(f"   插入耗时: {insert_time:.3f} 秒")
        print(f"   平均每条记录: {insert_time/batch_size*1000:.2f} 毫秒")

        # 查询性能测试
        print("   查询性能测试...")

        start_time = time.time()
        records = self.cost_tracker.get_records(limit=1000)
        query_time = time.time() - start_time

        print(f"   查询 {len(records)} 条记录耗时: {query_time:.3f} 秒")
        assert len(records) == batch_size

        # 聚合性能测试
        print("   聚合性能测试...")

        start_time = time.time()
        summary = self.cost_tracker.get_summary()
        aggregation_time = time.time() - start_time

        print(f"   聚合计算耗时: {aggregation_time:.3f} 秒")
        assert summary.total_requests == batch_size

        # 分析引擎性能测试
        print("   分析引擎性能测试...")

        start_time = time.time()
        trend_analysis = self.analytics_engine.get_trend_analysis(granularity="hourly")
        analysis_time = time.time() - start_time

        print(f"   趋势分析耗时: {analysis_time:.3f} 秒")
        assert trend_analysis["success"] == True

        print("=== 性能和扩展性测试通过 ===")


def run_e2e_tests():
    """运行端到端测试"""
    print("=== 启动成本跟踪系统端到端测试 ===")

    # 创建测试实例
    test_suite = TestCostTrackerE2E()

    try:
        # 运行测试
        test_suite.setup_method()

        print("\n1. 运行完整集成工作流测试...")
        test_suite.test_full_integration_workflow()

        print("\n2. 运行多provider和多模型场景测试...")
        test_suite.test_multiple_providers_and_models()

        print("\n3. 运行token估算fallback策略测试...")
        test_suite.test_token_estimation_fallback()

        print("\n4. 运行存储后端迁移测试...")
        test_suite.test_storage_backend_migration()

        print("\n5. 运行性能和扩展性测试...")
        test_suite.test_performance_and_scalability()

        print("\n=== 所有端到端测试通过 ===")
        return True

    except Exception as e:
        print(f"\n=== 端到端测试失败: {e} ===")
        import traceback

        traceback.print_exc()
        return False

    finally:
        test_suite.teardown_method()


if __name__ == "__main__":
    success = run_e2e_tests()
    sys.exit(0 if success else 1)
