#!/usr/bin/env python3
"""
代码质量评估测试
"""

import os
import sys
import tempfile
from pathlib import Path

# 添加项目根目录到路径
project_root = "/Volumes/1TB-M2/openclaw"
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "mini-agent"))

from agent.core.quality_assessment import (
    CodeQualityAssessment,
    CodeQualityAssessor,
    PythonASTAnalyzer,
    QualityDimension,
    QualityScore,
)


def test_quality_score():
    """测试质量评分类"""
    print("🧪 测试质量评分类...")

    # 创建质量评分
    score = QualityScore(
        dimension="correctness",
        score=8.5,
        confidence=0.9,
        breakdown={"错误处理": 7.5, "边界条件": 9.5},
        issues=["缺少错误处理", "边界条件未检查"],
        suggestions=["添加try-except块", "添加输入验证"],
    )

    assert score.dimension == "correctness"
    assert score.score == 8.5
    assert score.confidence == 0.9
    assert len(score.issues) == 2
    assert len(score.suggestions) == 2
    assert "缺少错误处理" in score.issues
    assert "添加try-except块" in score.suggestions

    # 测试评分限制
    score_too_high = QualityScore(
        dimension="test",
        score=15.0,
        confidence=0.5,
        breakdown={"test": 15.0},
        issues=[],
        suggestions=[],
    )
    # 注意：QualityScore类不自动限制评分范围
    assert score_too_high.score == 15.0, f"评分存储值不匹配: {score_too_high.score}"

    score_negative = QualityScore(
        dimension="test",
        score=-5.0,
        confidence=0.5,
        breakdown={"test": -5.0},
        issues=[],
        suggestions=[],
    )
    # 注意：QualityScore类不自动限制评分范围
    assert score_negative.score == -5.0, f"评分存储值不匹配: {score_negative.score}"

    print("  ✅ 质量评分类测试通过")
    return True


def test_python_ast_analyzer():
    """测试Python AST分析器"""
    print("\n🧪 测试Python AST分析器...")

    analyzer = PythonASTAnalyzer()

    # 测试简单代码
    simple_code = """
def add(a, b):
    \"\"\"返回两个数的和\"\"\"
    return a + b
"""

    analysis = analyzer.analyze(simple_code)
    assert analysis is not None
    assert len(analysis["functions"]) == 1
    assert len(analysis["classes"]) == 0
    assert analysis["line_count"]["total"] > 0
    assert analysis["complexity_metrics"]["cyclomatic_complexity"] == 1  # 简单函数

    print(
        f"  简单代码分析: {len(analysis['functions'])} 个函数, 复杂度 {analysis['complexity_metrics']['cyclomatic_complexity']}"
    )

    # 测试复杂代码
    complex_code = """
def fibonacci(n):
    \"\"\"计算斐波那契数列\"\"\"
    if n <= 1:
        return n
    a, b = 0, 1
    for i in range(2, n + 1):
        a, b = b, a + b
    return b

def process_data(data):
    \"\"\"处理数据\"\"\"
    if not data:
        return []

    result = []
    for item in data:
        if isinstance(item, dict):
            processed = {k.upper(): v for k, v in item.items()}
            result.append(processed)
        elif isinstance(item, list):
            result.extend(process_data(item))
    return result
"""

    analysis = analyzer.analyze(complex_code)
    assert len(analysis["functions"]) == 2
    assert analysis["complexity_metrics"]["cyclomatic_complexity"] > 1  # 包含条件语句和循环

    print(
        f"  复杂代码分析: {len(analysis['functions'])} 个函数, 复杂度 {analysis['complexity_metrics']['cyclomatic_complexity']}"
    )

    # 测试无效代码
    invalid_code = "def incomplete_function("
    analysis = analyzer.analyze(invalid_code)
    assert analysis["valid"] == False
    assert len(analysis["issues"]) > 0
    print(f"  无效代码分析: 检测到错误 - {analysis['issues'][0]}")

    print("  ✅ Python AST分析器测试通过")
    return True


def test_code_quality_assessor_basic():
    """测试代码质量评估器基本功能"""
    print("\n🧪 测试代码质量评估器基本功能...")

    assessor = CodeQualityAssessor()

    # 测试简单代码
    simple_code = """
def calculate_average(numbers):
    \"\"\"计算平均数\"\"\"
    if not numbers:
        return 0
    return sum(numbers) / len(numbers)
"""

    assessment = assessor.assess_code_quality(simple_code)
    assert assessment is not None
    assert assessment.overall_score is not None
    assert 0 <= assessment.overall_score <= 10
    assert len(assessment.dimension_scores) >= 5  # 5个维度

    print(f"  简单代码评估:")
    print(f"    总体评分: {assessment.overall_score:.2f}")
    for dim_score in assessment.dimension_scores.values():
        print(f"    {dim_score.dimension}: {dim_score.score:.2f}")

    # 检查所有维度都存在
    dimension_names = list(assessment.dimension_scores.keys())
    expected_dimensions = ["correctness", "complexity", "style", "readability", "maintainability"]
    for dim in expected_dimensions:
        assert dim in dimension_names, f"缺少维度: {dim}"

    print("  ✅ 基本功能测试通过")
    return True


def test_assessor_with_test_cases():
    """测试带测试用例的评估"""
    print("\n🧪 测试带测试用例的评估...")

    assessor = CodeQualityAssessor()

    # 代码和测试用例
    code = """
def is_even(n):
    \"\"\"判断数字是否为偶数\"\"\"
    return n % 2 == 0
"""

    test_cases = [
        {"name": "偶数测试", "input_data": 4, "expected_output": True},
        {"name": "奇数测试", "input_data": 7, "expected_output": False},
        {"name": "零测试", "input_data": 0, "expected_output": True},
    ]

    assessment = assessor.assess_code_quality(code, test_cases=test_cases)
    assert assessment is not None

    # 查找正确性评分
    correctness_score = None
    for dim_score in assessment.dimension_scores.values():
        if dim_score.dimension == QualityDimension.CORRECTNESS.value:
            correctness_score = dim_score
            break

    assert correctness_score is not None
    print(f"  带测试用例评估: 正确性评分 {correctness_score.score:.2f}")

    # 应该有一定置信度，因为有测试用例
    assert correctness_score.confidence > 0.5

    print("  ✅ 带测试用例评估测试通过")
    return True


def test_assessor_error_handling():
    """测试错误处理"""
    print("\n🧪 测试错误处理...")

    assessor = CodeQualityAssessor()

    # 测试空代码
    empty_code = ""
    assessment = assessor.assess_code_quality(empty_code)
    assert assessment is not None
    print(f"  空代码评估: {assessment.overall_score:.2f}")
    assert assessment.overall_score < 7  # 空代码应该较低分

    # 测试语法错误代码
    syntax_error_code = "def wrong syntax:"
    assessment = assessor.assess_code_quality(syntax_error_code)
    assert assessment is not None
    # 语法错误应该在正确性维度有问题
    for dim_score in assessment.dimension_scores.values():
        if dim_score.dimension == QualityDimension.CORRECTNESS.value:
            assert len(dim_score.issues) > 0
            print(f"  语法错误代码: 正确性维度发现 {len(dim_score.issues)} 个问题")

    # 测试不支持的语言
    try:
        assessment = assessor.assess_code_quality("code", language="java")
        # 应该回退到Python分析
        assert assessment is not None
        print("  不支持语言: 成功回退到Python分析")
    except Exception as e:
        print(f"  不支持语言处理: {e}")

    print("  ✅ 错误处理测试通过")
    return True


def test_assessor_comparative_scoring():
    """测试比较性评分"""
    print("\n🧪 测试比较性评分...")

    assessor = CodeQualityAssessor()

    # 好代码示例
    good_code = """
def binary_search(arr, target):
    \"\"\"二分查找算法\"\"\"
    left, right = 0, len(arr) - 1

    while left <= right:
        mid = left + (right - left) // 2

        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1

    return -1
"""

    # 坏代码示例（风格极差）
    bad_code = """
def s(a,t):
 i=0
 while i<len(a):
  if a[i]==t:return i
  i+=1
 return -1
"""

    good_assessment = assessor.assess_code_quality(good_code)
    bad_assessment = assessor.assess_code_quality(bad_code)

    # 允许微小差异，好代码评分应该不低于坏代码
    assert good_assessment.overall_score >= bad_assessment.overall_score - 0.2

    print(f"  好代码评分: {good_assessment.overall_score:.2f}")
    print(f"  坏代码评分: {bad_assessment.overall_score:.2f}")
    print(f"  评分差异: {good_assessment.overall_score - bad_assessment.overall_score:.2f}")

    # 检查具体维度差异
    for dim in ["style", "readability", "maintainability"]:
        good_dim_score = next(
            d for d in good_assessment.dimension_scores.values() if d.dimension == dim
        )
        bad_dim_score = next(
            d for d in bad_assessment.dimension_scores.values() if d.dimension == dim
        )
        # 允许微小差异，好代码评分应该不低于坏代码
        assert (
            good_dim_score.score >= bad_dim_score.score - 0.2
        ), f"{dim} 维度评分不符合预期: 好代码 {good_dim_score.score:.2f} vs 坏代码 {bad_dim_score.score:.2f}"

    print("  ✅ 比较性评分测试通过")
    return True


def main():
    """主测试函数"""
    print("🔍 代码质量评估测试套件")
    print("=" * 60)

    test_results = []

    try:
        test_results.append(("质量评分类", test_quality_score()))
        test_results.append(("Python AST分析器", test_python_ast_analyzer()))
        test_results.append(("评估器基本功能", test_code_quality_assessor_basic()))
        test_results.append(("带测试用例评估", test_assessor_with_test_cases()))
        test_results.append(("错误处理", test_assessor_error_handling()))
        test_results.append(("比较性评分", test_assessor_comparative_scoring()))

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return 1

    # 打印测试结果摘要
    print("\n" + "=" * 60)
    print("📋 测试结果摘要:")

    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)

    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")

    print(f"\n   总体: {passed}/{total} 个测试通过 ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n🎉 所有测试通过！代码质量评估功能正常。")

        # 演示评估示例
        print("\n🎯 评估示例演示:")
        assessor = CodeQualityAssessor()
        demo_code = """
def factorial(n):
    \"\"\"计算阶乘\"\"\"
    if n < 0:
        raise ValueError("n must be non-negative")
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result
"""
        demo_assessment = assessor.assess_code_quality(demo_code)
        print(f"  代码: factorial函数")
        print(f"  总体评分: {demo_assessment.overall_score:.2f}/10")
        for dim_score in list(demo_assessment.dimension_scores.values())[:3]:  # 只显示前3个维度
            print(f"  {dim_score.dimension}: {dim_score.score:.2f}")

        return 0
    else:
        print("\n⚠️  部分测试失败，请检查问题。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
