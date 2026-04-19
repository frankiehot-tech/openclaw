#!/usr/bin/env python3
"""
成本跟踪系统单元测试

测试CostTracker核心功能，包括：
1. 存储后端（SQLite、JSON、内存）
2. 成本记录和查询
3. 成本摘要计算
4. 分析引擎功能
"""

import json
import os
import shutil
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict

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
    SQLiteStorageBackend,
    StorageBackend,
)
from mini_agent.agent.core.cost_tracker_analytics import CostAnalyticsEngine
from mini_agent.agent.core.cost_tracker_json_storage import JSONStorageBackend
from mini_agent.agent.core.cost_tracker_memory_storage import MemoryStorageBackend


class TestCostRecord:
    """CostRecord数据类测试"""

    def test_cost_record_creation(self):
        """测试CostRecord创建"""
        timestamp = datetime.now()
        recorded_at = datetime.now()

        record = CostRecord(
            id="test_001",
            request_id="req_001",
            timestamp=timestamp,
            recorded_at=recorded_at,
            provider_id="deepseek",
            model_id="deepseek-chat",
            task_kind="testing",
            input_tokens=100,
            output_tokens=50,
            estimated_cost=0.0015,
            estimated_tokens=False,
        )

        assert record.id == "test_001"
        assert record.request_id == "req_001"
        assert record.provider_id == "deepseek"
        assert record.model_id == "deepseek-chat"
        assert record.task_kind == "testing"
        assert record.input_tokens == 100
        assert record.output_tokens == 50
        assert record.estimated_cost == 0.0015
        assert record.estimated_tokens == False

    def test_cost_record_to_dict(self):
        """测试CostRecord转换为字典"""
        timestamp = datetime.now()
        recorded_at = datetime.now()

        record = CostRecord(
            id="test_001",
            request_id="req_001",
            timestamp=timestamp,
            recorded_at=recorded_at,
            provider_id="deepseek",
            model_id="deepseek-chat",
            task_kind="testing",
            input_tokens=100,
            output_tokens=50,
            estimated_cost=0.0015,
            estimated_tokens=False,
        )

        record_dict = record.to_dict()
        assert record_dict["id"] == "test_001"
        assert record_dict["provider_id"] == "deepseek"
        assert record_dict["model_id"] == "deepseek-chat"
        assert record_dict["input_tokens"] == 100
        assert record_dict["output_tokens"] == 50
        assert record_dict["estimated_cost"] == 0.0015
        assert "timestamp" in record_dict
        assert "recorded_at" in record_dict

    def test_cost_record_from_dict(self):
        """测试从字典创建CostRecord"""
        timestamp = datetime.now()
        recorded_at = datetime.now()

        record_dict = {
            "id": "test_002",
            "request_id": "req_002",
            "timestamp": timestamp.isoformat(),
            "recorded_at": recorded_at.isoformat(),
            "provider_id": "dashscope",
            "model_id": "qwen3.5-plus",
            "task_kind": "debug",
            "input_tokens": 200,
            "output_tokens": 100,
            "estimated_cost": 0.0030,
            "estimated_tokens": True,
            "status": "recorded",
        }

        record = CostRecord.from_dict(record_dict)
        assert record.id == "test_002"
        assert record.request_id == "req_002"
        assert record.provider_id == "dashscope"
        assert record.model_id == "qwen3.5-plus"
        assert record.task_kind == "debug"
        assert record.input_tokens == 200
        assert record.output_tokens == 100
        assert record.estimated_cost == 0.0030
        assert record.estimated_tokens == True


class TestMemoryStorageBackend:
    """内存存储后端测试"""

    def setup_method(self):
        """每个测试方法前执行"""
        self.backend = MemoryStorageBackend(max_records=5)

    def test_record_cost(self):
        """测试记录成本"""
        record = CostRecord(
            id="test_mem_001",
            request_id="req_mem_001",
            timestamp=datetime.now(),
            recorded_at=datetime.now(),
            provider_id="deepseek",
            model_id="deepseek-chat",
            task_kind="testing",
            input_tokens=100,
            output_tokens=50,
            estimated_cost=0.0015,
            estimated_tokens=False,
        )

        success = self.backend.record_cost(record)
        assert success == True

        records = self.backend.get_records()
        assert len(records) == 1
        assert records[0].id == "test_mem_001"

    def test_get_records_with_filter(self):
        """测试带过滤的记录获取"""
        # 添加多个记录
        for i in range(3):
            record = CostRecord(
                id=f"test_mem_{i:03d}",
                request_id=f"req_mem_{i:03d}",
                timestamp=datetime.now() - timedelta(days=i),
                recorded_at=datetime.now(),
                provider_id="deepseek" if i % 2 == 0 else "dashscope",
                model_id="deepseek-chat" if i % 2 == 0 else "qwen3.5-plus",
                task_kind="testing",
                input_tokens=100 * (i + 1),
                output_tokens=50 * (i + 1),
                estimated_cost=0.001 * (i + 1),
                estimated_tokens=False,
            )
            self.backend.record_cost(record)

        # 测试provider过滤
        deepseek_records = self.backend.get_records(provider_id="deepseek")
        assert len(deepseek_records) == 2  # 第0和第2条记录

        # 测试时间过滤
        yesterday = date.today() - timedelta(days=1)
        recent_records = self.backend.get_records(start_date=yesterday)
        assert len(recent_records) >= 2  # 今天和昨天的记录

    def test_get_summary(self):
        """测试获取成本摘要"""
        # 添加记录
        for i in range(3):
            record = CostRecord(
                id=f"test_sum_{i:03d}",
                request_id=f"req_sum_{i:03d}",
                timestamp=datetime.now() - timedelta(days=i),
                recorded_at=datetime.now(),
                provider_id="deepseek" if i % 2 == 0 else "dashscope",
                model_id="deepseek-chat" if i % 2 == 0 else "qwen3.5-plus",
                task_kind="testing",
                input_tokens=100 * (i + 1),
                output_tokens=50 * (i + 1),
                estimated_cost=0.001 * (i + 1),
                estimated_tokens=False,
            )
            self.backend.record_cost(record)

        summary = self.backend.get_summary()
        assert summary.total_requests == 3
        assert summary.total_cost == 0.006  # 0.001 + 0.002 + 0.003
        assert "deepseek" in summary.by_provider
        assert "dashscope" in summary.by_provider

    def test_capacity_control(self):
        """测试容量控制"""
        backend = MemoryStorageBackend(max_records=3)

        # 添加4条记录，应该只保留最新的3条
        for i in range(4):
            record = CostRecord(
                id=f"test_cap_{i:03d}",
                request_id=f"req_cap_{i:03d}",
                timestamp=datetime.now() - timedelta(hours=i),
                recorded_at=datetime.now(),
                provider_id="test",
                model_id="test-model",
                task_kind="capacity_test",
                input_tokens=100,
                output_tokens=50,
                estimated_cost=0.001,
                estimated_tokens=False,
            )
            backend.record_cost(record)

        records = backend.get_records()
        assert len(records) == 3  # 应该只保留3条记录
        # 最早的第0条记录应该被移除
        record_ids = [r.id for r in records]
        assert "test_cap_000" not in record_ids


class TestSQLiteStorageBackend:
    """SQLite存储后端测试"""

    def setup_method(self):
        """每个测试方法前执行"""
        # 创建临时目录用于测试数据库
        self.temp_dir = tempfile.mkdtemp(prefix="cost_test_")
        self.db_path = Path(self.temp_dir) / "test_cost.db"
        self.backend = SQLiteStorageBackend(db_path=str(self.db_path))

    def teardown_method(self):
        """每个测试方法后执行"""
        # 清理临时目录
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """测试后端初始化"""
        assert self.backend.conn is not None
        assert os.path.exists(self.db_path)

    def test_record_cost_and_retrieve(self):
        """测试记录成本和检索"""
        record = CostRecord(
            id="test_sql_001",
            request_id="req_sql_001",
            timestamp=datetime.now(),
            recorded_at=datetime.now(),
            provider_id="deepseek",
            model_id="deepseek-chat",
            task_kind="testing",
            input_tokens=150,
            output_tokens=75,
            estimated_cost=0.0020,
            estimated_tokens=False,
        )

        success = self.backend.record_cost(record)
        assert success == True

        records = self.backend.get_records()
        assert len(records) == 1
        retrieved_record = records[0]
        assert retrieved_record.id == "test_sql_001"
        assert retrieved_record.provider_id == "deepseek"
        assert retrieved_record.input_tokens == 150
        assert retrieved_record.output_tokens == 75
        assert retrieved_record.estimated_cost == 0.0020

    def test_get_summary_empty(self):
        """测试空数据库的成本摘要"""
        summary = self.backend.get_summary()
        assert summary.total_requests == 0
        assert summary.total_cost == 0.0
        assert summary.by_provider == {}
        assert summary.by_model == {}

    def test_get_summary_with_data(self):
        """测试有数据的成本摘要"""
        # 添加多条记录
        for i in range(3):
            record = CostRecord(
                id=f"test_sql_sum_{i:03d}",
                request_id=f"req_sql_sum_{i:03d}",
                timestamp=datetime.now() - timedelta(days=i),
                recorded_at=datetime.now(),
                provider_id="deepseek" if i % 2 == 0 else "dashscope",
                model_id="deepseek-chat" if i % 2 == 0 else "qwen3.5-plus",
                task_kind="testing",
                input_tokens=100 * (i + 1),
                output_tokens=50 * (i + 1),
                estimated_cost=0.001 * (i + 1),
                estimated_tokens=False,
            )
            self.backend.record_cost(record)

        summary = self.backend.get_summary()
        assert summary.total_requests == 3
        assert summary.total_cost == 0.006  # 0.001 + 0.002 + 0.003
        assert len(summary.by_provider) == 2
        assert "deepseek" in summary.by_provider
        assert "dashscope" in summary.by_provider


class TestCostTracker:
    """CostTracker集成测试"""

    def setup_method(self):
        """每个测试方法前执行"""
        self.temp_dir = tempfile.mkdtemp(prefix="cost_tracker_test_")
        self.db_path = Path(self.temp_dir) / "tracker_test.db"

        self.tracker = CostTracker(storage_backend="sqlite", config={"db_path": str(self.db_path)})

    def teardown_method(self):
        """每个测试方法后执行"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_record_request(self):
        """测试记录API请求"""
        record_id = self.tracker.record_request(
            request_id="req_tracker_001",
            provider_id="deepseek",
            model_id="deepseek-chat",
            task_kind="testing",
            input_tokens=200,
            output_tokens=100,
            estimated_tokens=False,
        )

        assert record_id.startswith("req_tracker_001") or record_id.startswith("cost_")

        # 验证记录已保存
        records = self.tracker.get_records()
        assert len(records) == 1
        assert records[0].provider_id == "deepseek"

    def test_get_records_proxy(self):
        """测试代理get_records方法"""
        # 添加多条记录
        for i in range(3):
            self.tracker.record_request(
                request_id=f"req_proxy_{i:03d}",
                provider_id="deepseek" if i % 2 == 0 else "dashscope",
                model_id="deepseek-chat" if i % 2 == 0 else "qwen3.5-plus",
                task_kind="testing",
                input_tokens=100 * (i + 1),
                output_tokens=50 * (i + 1),
                estimated_tokens=False,
            )

        # 测试过滤
        deepseek_records = self.tracker.get_records(provider_id="deepseek")
        assert len(deepseek_records) == 2

        # 测试限制
        limited_records = self.tracker.get_records(limit=2)
        assert len(limited_records) == 2

    def test_get_summary_proxy(self):
        """测试代理get_summary方法"""
        # 添加记录
        for i in range(3):
            self.tracker.record_request(
                request_id=f"req_summary_{i:03d}",
                provider_id="deepseek" if i % 2 == 0 else "dashscope",
                model_id="deepseek-chat" if i % 2 == 0 else "qwen3.5-plus",
                task_kind="testing",
                input_tokens=100 * (i + 1),
                output_tokens=50 * (i + 1),
                estimated_tokens=False,
            )

        summary = self.tracker.get_summary()
        assert summary.total_requests == 3
        assert summary.total_cost > 0
        assert len(summary.by_provider) == 2


class TestCostAnalyticsEngine:
    """成本分析引擎测试"""

    def setup_method(self):
        """每个测试方法前执行"""
        self.temp_dir = tempfile.mkdtemp(prefix="analytics_test_")
        self.db_path = Path(self.temp_dir) / "analytics_test.db"

        self.tracker = CostTracker(storage_backend="sqlite", config={"db_path": str(self.db_path)})

        # 添加测试数据
        for i in range(7):  # 最近7天的数据
            for j in range(2):  # 每天2条记录
                self.tracker.record_request(
                    request_id=f"req_analytics_{i}_{j}",
                    provider_id="deepseek" if j % 2 == 0 else "dashscope",
                    model_id="deepseek-chat" if j % 2 == 0 else "qwen3.5-plus",
                    task_kind="testing" if i % 2 == 0 else "debug",
                    input_tokens=100 + i * 10,
                    output_tokens=50 + i * 5,
                    estimated_tokens=False,
                )

        self.engine = CostAnalyticsEngine(cost_tracker=self.tracker)

    def teardown_method(self):
        """每个测试方法后执行"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_trend_analysis(self):
        """测试趋势分析"""
        analysis = self.engine.get_trend_analysis(granularity="daily")
        assert analysis["success"] == True
        assert "period" in analysis
        assert "trends" in analysis
        assert "statistics" in analysis
        assert analysis["granularity"] == "daily"

        # 应该有数据
        if analysis["statistics"]["total_cost"] > 0:
            assert len(analysis["trends"]) > 0

    def test_provider_comparison(self):
        """测试provider对比分析"""
        analysis = self.engine.get_provider_comparison()
        assert analysis["success"] == True
        assert "providers" in analysis
        assert "total_cost" in analysis

        # 至少有两个provider
        assert len(analysis["providers"]) >= 2

    def test_task_kind_analysis(self):
        """测试任务类型分析"""
        analysis = self.engine.get_task_kind_analysis()
        assert analysis["success"] == True
        assert "task_kind_analysis" in analysis

        # 应该有两种任务类型
        assert len(analysis["task_kind_analysis"]) >= 2

    def test_cost_optimization_plan(self):
        """测试成本优化计划"""
        plan = self.engine.get_cost_optimization_plan(target_reduction_percentage=10.0)
        assert plan["success"] == True
        assert "current_monthly_cost" in plan
        assert "target_reduction_percentage" in plan
        assert "estimated_savings" in plan
        assert "optimization_measures" in plan

    def test_health_score(self):
        """测试健康度评分"""
        score = self.engine.get_health_score()
        assert score["success"] == True
        assert "overall_score" in score
        assert "category_scores" in score
        assert "recommendations" in score

        # 分数应在0-100之间
        assert 0 <= score["overall_score"] <= 100


class TestCostEstimationStrategy:
    """成本估算策略测试"""

    def test_token_estimation(self):
        """测试token估算"""
        strategy = CostEstimationStrategy()

        # 测试中英文混合文本
        text = "这是一个测试。This is a test."
        estimated_tokens = strategy.estimate_tokens(text)

        # 估算应该合理
        assert estimated_tokens > 0
        # 中文字符大约1.5字符/token，英文字符大约4字符/token
        chinese_chars = len([c for c in text if "\u4e00" <= c <= "\u9fff"])
        english_chars = len(text) - chinese_chars
        expected_min = chinese_chars / 2 + english_chars / 5  # 宽松的下限
        expected_max = chinese_chars * 2 + english_chars * 2  # 宽松的上限
        assert expected_min <= estimated_tokens <= expected_max

    def test_extract_tokens_from_provider_script(self):
        """测试从provider脚本提取tokens"""
        strategy = CostEstimationStrategy()

        # 模拟包含tokens信息的脚本输出
        mock_output = """
        Some debug info...
        {"usage": {"prompt_tokens": 150, "completion_tokens": 75, "total_tokens": 225}}
        Some more debug info...
        """

        tokens = strategy.extract_tokens_from_provider_script(mock_output)
        assert tokens is not None
        assert "input_tokens" in tokens
        assert "output_tokens" in tokens
        assert tokens["input_tokens"] == 150
        assert tokens["output_tokens"] == 75

    def test_multi_level_fallback(self):
        """测试多层级fallback策略"""
        strategy = CostEstimationStrategy()

        # 测试1: 提供API响应
        api_response = {"usage": {"prompt_tokens": 200, "completion_tokens": 100}}
        tokens1 = strategy.estimate_cost_tokens(
            provider_id="deepseek",
            model_id="deepseek-chat",
            api_response=api_response,
            fallback_text="一些文本",
        )
        assert tokens1["input_tokens"] == 200
        assert tokens1["output_tokens"] == 100
        assert tokens1["source"] == "api_response"

        # 测试2: 提供脚本输出（无API响应）
        script_output = '{"usage": {"prompt_tokens": 150, "completion_tokens": 50}}'
        tokens2 = strategy.estimate_cost_tokens(
            provider_id="deepseek",
            model_id="deepseek-chat",
            api_response=None,
            provider_script_output=script_output,
            fallback_text="一些文本",
        )
        assert tokens2["input_tokens"] == 150
        assert tokens2["output_tokens"] == 50
        assert tokens2["source"] == "provider_script"

        # 测试3: 仅提供fallback文本
        tokens3 = strategy.estimate_cost_tokens(
            provider_id="deepseek",
            model_id="deepseek-chat",
            api_response=None,
            provider_script_output=None,
            fallback_text="这是一个测试文本。",
        )
        assert tokens3["input_tokens"] > 0
        assert tokens3["output_tokens"] == 0  # 仅输入文本
        assert tokens3["source"] == "estimation"


def run_all_tests():
    """运行所有测试"""
    import pytest

    # 切换到测试目录
    test_dir = Path(__file__).parent
    os.chdir(test_dir.parent)
    # 运行测试
    pytest.main([str(test_dir / "test_cost_tracker.py"), "-v"])


if __name__ == "__main__":
    run_all_tests()
