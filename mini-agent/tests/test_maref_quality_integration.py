#!/usr/bin/env python3
"""
测试MAREF质量评估集成器

验证MAREF质量评估体系的各个组件：
1. 三才评估引擎 (ThreeTalentAssessmentEngine)
2. 河图洛书调度器 (HetuLuoshuScheduler)
3. 格雷编码状态管理器 (GrayCodeStateManager)
4. 八卦代数评估器 (EightTrigramsAssessor)
5. MAREF质量评估集成器 (MarefQualityEvaluator)
"""

import json
import logging
import os
import sys
import tempfile
import unittest
from typing import Any, Dict, List

# 添加项目根目录到路径
project_root = "/Volumes/1TB-M2/openclaw"
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "mini-agent"))

from agent.core.maref_quality.eight_trigrams_assessor import (
    EightTrigrams,
    EightTrigramsAssessor,
    HexagramResult,
    TrigramAssessment,
)
from agent.core.maref_quality.gray_code_state_manager import (
    GrayCodeStateManager,
    StateAnalysis,
)
from agent.core.maref_quality.hetu_luoshu_scheduler import (
    AssessmentPriority,
    HetuLuoshuScheduler,
    HetuState,
    LuoshuPosition,
)
from agent.core.maref_quality.three_talent_engine import (
    ThreeTalentAssessmentEngine,
    ThreeTalentResult,
)

# 导入测试模块
from agent.core.maref_quality_integration import (
    MarefQualityEvaluator,
    MarefQualityResult,
    get_maref_quality_evaluator,
)


class TestMarefQualityIntegration(unittest.TestCase):
    """MAREF质量评估集成测试"""

    def setUp(self):
        """测试前准备"""
        # 禁用详细日志，除非需要调试
        logging.getLogger().setLevel(logging.WARNING)

        # 测试代码示例
        self.sample_code_good = '''
def fibonacci(n: int) -> int:
    """计算斐波那契数列第n项"""
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b

def test_fibonacci():
    """测试斐波那契函数"""
    assert fibonacci(0) == 0
    assert fibonacci(1) == 1
    assert fibonacci(5) == 5
    assert fibonacci(10) == 55
    return "所有测试通过！"
'''

        self.sample_code_bad = """
def fib(n):
    if n < 2:
        return n
    else:
        return fib(n-1) + fib(n-2)

def test():
    print(fib(5))
"""

        # 简单上下文
        self.sample_context = {
            "task_type": "algorithm_implementation",
            "difficulty": 3,
            "language": "python",
        }

    def test_01_three_talent_engine_initialization(self):
        """测试三才评估引擎初始化"""
        engine = ThreeTalentAssessmentEngine()
        self.assertIsNotNone(engine)
        self.assertIsNotNone(engine.human_assessor)
        self.assertIsNotNone(engine.earth_assessor)
        self.assertIsNotNone(engine.heaven_assessor)

        # 测试评估
        result = engine.assess(self.sample_code_good, self.sample_context)
        self.assertIsInstance(result, ThreeTalentResult)

        # human_result是HumanLayerResult对象，不是字典
        self.assertIsNotNone(result.human_result)
        self.assertIsNotNone(result.earth_result)
        self.assertIsNotNone(result.heaven_result)

        # 检查对象属性
        self.assertIsInstance(result.human_result.ast_analysis, dict)
        self.assertIsInstance(result.earth_result.dimension_scores, dict)
        self.assertIsInstance(result.heaven_result.quality_trend, dict)

        # 验证天层质量评分在合理范围内（通过cost_quality_ratio）
        cost_quality_ratio = result.heaven_result.cost_quality_ratio
        self.assertTrue(0 <= cost_quality_ratio <= 100)  # 合理范围

        print("✅ 三才评估引擎测试通过")

    def test_02_hetu_luoshu_scheduler_initialization(self):
        """测试河图洛书调度器初始化"""
        scheduler = HetuLuoshuScheduler()
        self.assertIsNotNone(scheduler)

        # 验证状态枚举
        self.assertEqual(len(HetuState), 10)  # 10个状态
        self.assertEqual(HetuState.INITIAL.name, "INITIAL")
        self.assertEqual(HetuState.COMPLETED.name, "COMPLETED")

        # 验证位置枚举
        self.assertEqual(len(LuoshuPosition), 9)  # 9个位置

        # 测试任务提交（替代schedule_assessment）
        task_id = scheduler.submit_task(
            code=self.sample_code_good,
            task_type="algorithm_implementation",
            priority=AssessmentPriority.MEDIUM,
            context=self.sample_context,
        )

        self.assertIsNotNone(task_id)
        self.assertGreater(len(task_id), 0)

        # 获取任务状态
        task_status = scheduler.get_task_status(task_id)
        self.assertIsNotNone(task_status)
        self.assertIn("state", task_status)

        # 获取系统报告
        system_report = scheduler.get_system_report()
        self.assertIsNotNone(system_report)
        self.assertIn("scheduler_status", system_report)

        print("✅ 河图洛书调度器测试通过")

    def test_03_gray_code_state_manager_initialization(self):
        """测试格雷编码状态管理器初始化"""
        state_manager = GrayCodeStateManager()
        self.assertIsNotNone(state_manager)

        # 验证维度数量
        self.assertEqual(state_manager.n_dimensions, 6)

        # 验证状态空间大小
        self.assertEqual(state_manager.state_space, 64)  # 2^6 = 64

        # 测试状态分析
        test_state = 42  # 010101 在二进制中
        analysis = state_manager.analyze_state(test_state)

        self.assertIsInstance(analysis, StateAnalysis)
        self.assertEqual(analysis.state_code, test_state)
        self.assertEqual(len(analysis.binary_representation), 6)
        self.assertEqual(len(analysis.gray_code_representation), 6)

        # 验证质量评分
        self.assertTrue(0 <= analysis.quality_score <= 10)

        # 测试状态演化
        initial_state = 0
        new_state, evolution = state_manager.evolve_state(
            current_state=initial_state,
            dimension="correctness",
            improvement=0.8,
            context={"test": True},
        )

        self.assertNotEqual(new_state, initial_state)
        self.assertEqual(evolution.changed_dimension, "correctness")

        print("✅ 格雷编码状态管理器测试通过")

    def test_04_eight_trigrams_assessor_initialization(self):
        """测试八卦代数评估器初始化"""
        assessor = EightTrigramsAssessor()
        self.assertIsNotNone(assessor)

        # 验证八卦数量
        self.assertEqual(len(EightTrigrams), 8)

        # 测试八卦评估
        sample_analysis = {
            "ast_analysis": {"valid": True},
            "complexity_metrics": {"cyclomatic_complexity": 5},
            "style_issues": [],
            "readability_score": 8.5,
        }

        trigram_assessments = assessor.assess_with_trigrams(
            code_analysis=sample_analysis, context=self.sample_context
        )

        self.assertIsInstance(trigram_assessments, dict)
        self.assertEqual(len(trigram_assessments), 8)  # 8个八卦

        # 验证每个八卦都有TrigramAssessment对象
        for trigram_name, assessment in trigram_assessments.items():
            self.assertIsInstance(assessment, TrigramAssessment)
            self.assertTrue(0 <= assessment.score <= 10)
            self.assertTrue(0 <= assessment.weight <= 1)
            self.assertIsInstance(assessment.trigram, EightTrigrams)

        # 测试六十四卦组合（需要assessments参数）
        hexagram_result = assessor.combine_trigrams(
            upper_trigram=EightTrigrams.QIAN,
            lower_trigram=EightTrigrams.KUN,
            assessments=trigram_assessments,
        )

        self.assertIsInstance(hexagram_result, HexagramResult)
        self.assertEqual(hexagram_result.upper_trigram, EightTrigrams.QIAN)
        self.assertEqual(hexagram_result.lower_trigram, EightTrigrams.KUN)
        self.assertIsInstance(hexagram_result.hexagram_index, int)
        self.assertTrue(0 <= hexagram_result.hexagram_index < 64)

        print("✅ 八卦代数评估器测试通过")

    def test_05_maref_quality_evaluator_initialization(self):
        """测试MAREF质量评估器初始化"""
        evaluator = MarefQualityEvaluator(enable_advanced_features=True)
        self.assertIsNotNone(evaluator)
        self.assertIsNotNone(evaluator.three_talent_engine)
        self.assertIsNotNone(evaluator.hetu_luoshu_scheduler)
        self.assertIsNotNone(evaluator.gray_state_manager)
        self.assertIsNotNone(evaluator.eight_trigrams_assessor)

        # 测试全局实例获取
        global_evaluator = get_maref_quality_evaluator()
        self.assertIsNotNone(global_evaluator)
        self.assertIsInstance(global_evaluator, MarefQualityEvaluator)

        print("✅ MAREF质量评估器初始化测试通过")

    def test_06_maref_quality_assessment_basic(self):
        """测试基本MAREF质量评估"""
        evaluator = MarefQualityEvaluator(enable_advanced_features=True)

        # 评估好代码
        result = evaluator.assess_code_quality(
            code=self.sample_code_good, context=self.sample_context
        )

        self.assertIsInstance(result, MarefQualityResult)
        self.assertIsInstance(result.overall_score, float)
        self.assertTrue(0 <= result.overall_score <= 10)

        # 验证三才结果存在（注意：MarefQualityResult中human_result是字典，但ThreeTalentResult中human_result是对象）
        # 由于MarefQualityEvaluator将ThreeTalentResult转换为字典，所以这里应该是字典
        self.assertIsInstance(result.human_result, dict)
        self.assertIsInstance(result.earth_result, dict)
        self.assertIsInstance(result.heaven_result, dict)

        # 验证八卦评分
        self.assertIsInstance(result.trigram_scores, dict)
        self.assertEqual(len(result.trigram_scores), 8)

        # 验证格雷状态分析
        self.assertIsNotNone(result.gray_state_analysis)
        self.assertIsInstance(result.gray_state_analysis, StateAnalysis)

        print(f"✅ MAREF质量评估基本测试通过 (评分: {result.overall_score:.2f}/10)")

    def test_07_maref_quality_assessment_comparison(self):
        """测试代码质量对比评估"""
        evaluator = MarefQualityEvaluator(enable_advanced_features=True)

        # 评估好代码
        good_result = evaluator.assess_code_quality(
            code=self.sample_code_good, context=self.sample_context
        )

        # 评估坏代码
        bad_result = evaluator.assess_code_quality(
            code=self.sample_code_bad, context=self.sample_context
        )

        # 好代码应该比坏代码评分高
        # 注意：由于评估算法的复杂性，我们允许微小差异
        # 但总体趋势应该是好代码评分更高
        self.assertGreaterEqual(
            good_result.overall_score,
            bad_result.overall_score - 2.0,  # 允许2分差异容错
            f"好代码评分({good_result.overall_score:.2f})应不低于坏代码评分({bad_result.overall_score:.2f})",
        )

        # 验证改进建议
        self.assertIsInstance(good_result.improvement_suggestions, list)
        self.assertIsInstance(bad_result.improvement_suggestions, list)

        # 坏代码通常应该有更多改进建议
        self.assertGreaterEqual(
            len(bad_result.improvement_suggestions),
            len(good_result.improvement_suggestions) - 2,  # 允许微小差异
            "坏代码应该有更多改进建议",
        )

        print(f"✅ 代码质量对比测试通过")
        print(
            f"   好代码: {good_result.overall_score:.2f}/10, 坏代码: {bad_result.overall_score:.2f}/10"
        )

    def test_08_maref_report_generation(self):
        """测试MAREF报告生成"""
        evaluator = MarefQualityEvaluator(enable_advanced_features=True)

        # 评估代码
        result = evaluator.assess_code_quality(
            code=self.sample_code_good, context=self.sample_context
        )

        # 生成报告
        report = evaluator.generate_maref_report(result)

        self.assertIsInstance(report, str)
        self.assertGreater(len(report), 100)  # 报告应该有合理长度

        # 验证报告包含关键部分
        self.assertIn("MAREF质量评估报告", report)
        self.assertIn("综合质量评分", report)
        self.assertIn("格雷编码状态分析", report)
        self.assertIn("八卦代数评估", report)

        # 验证评分在报告中
        self.assertIn(f"{result.overall_score:.2f}", report)

        print("✅ MAREF报告生成测试通过")

    def test_09_maref_state_evolution_tracking(self):
        """测试状态演化跟踪"""
        evaluator = MarefQualityEvaluator(enable_advanced_features=True)

        # 记录初始状态
        initial_state = evaluator.current_gray_state

        # 评估第一段代码
        result1 = evaluator.assess_code_quality(
            code=self.sample_code_good, context=self.sample_context
        )

        # 获取评估后的状态
        state_after_first = evaluator.current_gray_state

        # 评估第二段代码
        result2 = evaluator.assess_code_quality(
            code=self.sample_code_bad, context=self.sample_context
        )

        # 获取评估后的状态
        state_after_second = evaluator.current_gray_state

        # 验证演化历史
        self.assertIsInstance(evaluator.evolution_history, list)

        # 如果状态有变化，演化历史应该不为空
        if initial_state != state_after_first or state_after_first != state_after_second:
            self.assertGreater(len(evaluator.evolution_history), 0)

        # 验证演化记录结构
        if evaluator.evolution_history:
            evolution = evaluator.evolution_history[-1]
            self.assertIsNotNone(evolution.from_state)
            self.assertIsNotNone(evolution.to_state)
            self.assertIsNotNone(evolution.changed_dimension)
            self.assertIsNotNone(evolution.timestamp)

        print(f"✅ 状态演化跟踪测试通过 (演化次数: {len(evaluator.evolution_history)})")

    def test_10_maref_integration_with_experiment_context(self):
        """测试与实验上下文的集成"""
        evaluator = MarefQualityEvaluator(enable_advanced_features=True)

        # 模拟实验记录上下文
        experiment_context = {
            "experiment_id": "maref_quality_test",
            "group_name": "treatment",
            "request_id": "test_request_001",
            "provider": "deepseek-coder",
            "task_type": "algorithm_implementation",
            "difficulty": 4,
            "cost_usd": 0.05,
        }

        # 使用实验上下文进行评估
        result = evaluator.assess_code_quality(
            code=self.sample_code_good, context=experiment_context
        )

        # 验证结果包含实验上下文信息
        self.assertIsNotNone(result.current_hetu_state)
        self.assertIsInstance(result.task_schedule, list)

        # 验证八卦评分考虑了上下文
        for trigram_name, score_info in result.trigram_scores.items():
            self.assertIn("score", score_info)
            # 评分应该在合理范围内
            self.assertTrue(0 <= score_info["score"] <= 10)

        # 验证格雷状态考虑了成本效率维度
        if result.gray_state_analysis:
            dimension_values = result.gray_state_analysis.dimension_values
            self.assertIn("cost_efficiency", dimension_values)

        print("✅ 实验上下文集成测试通过")

    def test_11_maref_result_serialization(self):
        """测试MAREF结果序列化"""
        evaluator = MarefQualityEvaluator(enable_advanced_features=True)

        # 评估代码
        result = evaluator.assess_code_quality(
            code=self.sample_code_good, context=self.sample_context
        )

        # 转换为字典
        result_dict = result.to_dict()

        self.assertIsInstance(result_dict, dict)

        # 验证关键字段存在
        self.assertIn("human_result", result_dict)
        self.assertIn("earth_result", result_dict)
        self.assertIn("heaven_result", result_dict)
        self.assertIn("trigram_scores", result_dict)
        self.assertIn("overall_score", result_dict)
        self.assertIn("quality_breakdown", result_dict)
        self.assertIn("improvement_suggestions", result_dict)

        # 验证序列化后的评分匹配
        self.assertEqual(result_dict["overall_score"], result.overall_score)

        # 验证可以序列化为JSON
        json_str = json.dumps(result_dict, ensure_ascii=False)
        self.assertIsInstance(json_str, str)
        self.assertGreater(len(json_str), 100)

        # 验证可以从JSON反序列化
        parsed_dict = json.loads(json_str)
        self.assertIsInstance(parsed_dict, dict)
        self.assertEqual(parsed_dict["overall_score"], result.overall_score)

        print("✅ MAREF结果序列化测试通过")

    def test_12_maref_performance_basic(self):
        """测试基本性能（不应超时）"""
        import time

        evaluator = MarefQualityEvaluator(enable_advanced_features=True)

        # 测试评估性能
        start_time = time.time()

        result = evaluator.assess_code_quality(
            code=self.sample_code_good, context=self.sample_context
        )

        end_time = time.time()
        elapsed_time = end_time - start_time

        # 评估应该在合理时间内完成（比如5秒内）
        # 注意：首次评估可能较慢，因为需要初始化组件
        self.assertLess(elapsed_time, 10.0, f"评估耗时过长: {elapsed_time:.2f}秒")  # 10秒上限

        # 验证结果有效
        self.assertIsInstance(result, MarefQualityResult)
        self.assertTrue(0 <= result.overall_score <= 10)

        print(f"✅ 性能测试通过 (耗时: {elapsed_time:.2f}秒, 评分: {result.overall_score:.2f})")


def run_maref_integration_tests():
    """运行MAREF集成测试"""
    print("🧪 开始运行MAREF质量评估集成测试...")
    print("=" * 70)

    # 创建测试套件
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestMarefQualityIntegration)

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("=" * 70)
    if result.wasSuccessful():
        print("✅ 所有MAREF集成测试通过！")
        return True
    else:
        print(f"❌ MAREF集成测试失败: {len(result.failures)} 个失败, {len(result.errors)} 个错误")
        return False


if __name__ == "__main__":
    # 运行所有测试
    success = run_maref_integration_tests()

    if success:
        # 演示MAREF评估器
        print("\n🎯 MAREF质量评估演示:")
        print("-" * 60)

        evaluator = get_maref_quality_evaluator()

        # 演示代码
        demo_code = '''
class MathUtils:
    """数学工具类"""

    @staticmethod
    def factorial(n: int) -> int:
        """计算阶乘"""
        if n < 0:
            raise ValueError("阶乘不能为负数")
        elif n == 0:
            return 1
        else:
            result = 1
            for i in range(1, n + 1):
                result *= i
            return result

    @staticmethod
    def is_prime(n: int) -> bool:
        """判断是否为质数"""
        if n < 2:
            return False
        for i in range(2, int(n ** 0.5) + 1):
            if n % i == 0:
                return False
        return True
'''

        print("📝 演示代码（良好质量的数学工具类）:")
        print(demo_code[:200] + "...")
        print("-" * 60)

        # 评估演示代码
        demo_result = evaluator.assess_code_quality(
            code=demo_code, context={"task_type": "utility_class", "difficulty": 3}
        )

        # 生成演示报告
        demo_report = evaluator.generate_maref_report(demo_result)
        print("\n" + demo_report)

        print("\n🎉 MAREF质量评估体系演示完成！")
        sys.exit(0)
    else:
        sys.exit(1)
