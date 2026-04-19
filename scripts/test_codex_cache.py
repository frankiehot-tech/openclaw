#!/usr/bin/env python3
"""
Codex缓存回归验证测试

验证最小缓存闭环:
1. miss -> write -> hit 流程
2. 错误签名或失效策略负路径测试
3. 命中统计冒烟测试
"""

import json
import logging
import os
import sys
import tempfile
import time
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 添加 mini-agent 目录到路径
mini_agent_dir = project_root / "mini_agent"
if str(mini_agent_dir) not in sys.path:
    sys.path.insert(0, str(mini_agent_dir))

# 也添加实际的 mini-agent 目录
mini_agent_actual = project_root / "mini-agent"
if str(mini_agent_actual) not in sys.path:
    sys.path.insert(0, str(mini_agent_actual))

try:
    from mini_agent.agent.core.codex_cache import (
        CacheEntry,
        CacheSource,
        CacheStatus,
        CodexCache,
        MatchStrategy,
        SimilarityMatcher,
        TaskSignatureNormalizer,
    )
except ImportError as e:
    # 尝试使用绝对导入
    import sys

    sys.path.insert(0, "/Volumes/1TB-M2/openclaw/mini-agent")
    sys.path.insert(0, "/Volumes/1TB-M2/openclaw")
    from mini_agent.agent.core.codex_cache import (
        CacheEntry,
        CacheSource,
        CacheStatus,
        CodexCache,
        MatchStrategy,
        SimilarityMatcher,
        TaskSignatureNormalizer,
    )

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_miss_write_hit_loop() -> bool:
    """
    测试 miss -> write -> hit 闭环

    步骤:
    1. 查询不存在的内容 (miss)
    2. 写入缓存
    3. 再次查询相同内容 (hit)
    4. 验证命中
    """
    print("=== 测试 miss -> write -> hit 闭环 ===")

    # 使用临时目录
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir) / "test_cache"
        cache = CodexCache(cache_dir=cache_dir, memory_limit=10)

        test_input = "How to implement binary search in Python?"
        test_payload = {
            "answer": "def binary_search(arr, target):\n    left, right = 0, len(arr)-1\n    while left <= right:\n        mid = (left + right) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    return -1",
            "complexity": "O(log n)",
            "language": "Python",
        }

        # 1. 首次查询 (应为miss)
        print(f"1. 首次查询: '{test_input[:50]}...'")
        result1 = cache.get(test_input, source=CacheSource.CODEX_PLAN.value)

        if result1.status != CacheStatus.MISS:
            print(f"   ❌ 预期 MISS, 实际得到: {result1.status.value}")
            return False

        print(f"   ✅ 正确得到 MISS")

        # 2. 写入缓存
        print("2. 写入缓存...")
        entry = cache.put(
            raw_input=test_input,
            payload=test_payload,
            source=CacheSource.CODEX_PLAN.value,
            estimated_save_seconds=3.0,
            estimated_save_tokens=100,
        )
        print(f"   创建条目: 键={entry.key}, 签名={entry.normalized_signature[:30]}...")

        # 3. 再次查询 (应为hit)
        print("3. 再次查询...")
        result2 = cache.get(test_input, source=CacheSource.CODEX_PLAN.value)

        if result2.status != CacheStatus.HIT:
            print(f"   ❌ 预期 HIT, 实际得到: {result2.status.value}")
            return False

        if not result2.entry or result2.entry.key != entry.key:
            print(f"   ❌ 返回的条目键不匹配")
            return False

        if result2.match_strategy != MatchStrategy.EXACT:
            print(
                f"   ❌ 预期 EXACT 匹配策略, 实际得到: {result2.match_strategy.value if result2.match_strategy else 'None'}"
            )
            return False

        print(f"   ✅ 正确得到 HIT (精确匹配)")
        if result2.entry:
            print(f"   命中次数: {result2.entry.hit_count}")

        # 4. 验证负载内容
        if not result2.entry or result2.entry.payload.get("answer") != test_payload["answer"]:
            print("   ❌ 负载内容不匹配")
            return False

        print("   ✅ 负载内容正确")

        # 5. 验证统计
        stats = cache.get_stats()
        if stats["total_hits"] != 1:
            print(f"   ❌ 预期总命中数=1, 实际={stats['total_hits']}")
            return False

        if stats["total_misses"] != 1:
            print(f"   ❌ 预期总未命中数=1, 实际={stats['total_misses']}")
            return False

        print(f"   ✅ 统计正确: 命中={stats['total_hits']}, 未命中={stats['total_misses']}")

        return True


def test_similarity_matching() -> bool:
    """
    测试相似性匹配

    步骤:
    1. 写入一个条目
    2. 用相似但不同的查询来匹配
    3. 验证相似性匹配命中
    """
    print("\n=== 测试相似性匹配 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir) / "test_cache"
        cache = CodexCache(cache_dir=cache_dir, memory_limit=10)

        # 原始输入
        original_input = "Implement quicksort algorithm in Python"
        original_payload = {
            "answer": "def quicksort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[len(arr)//2]\n    left = [x for x in arr if x < pivot]\n    middle = [x for x in arr if x == pivot]\n    right = [x for x in arr if x > pivot]\n    return quicksort(left) + middle + quicksort(right)",
            "complexity": "O(n log n) average, O(n²) worst",
        }

        # 写入缓存
        entry = cache.put(
            raw_input=original_input,
            payload=original_payload,
            source=CacheSource.CODEX_PLAN.value,
        )

        print(f"写入条目: '{original_input}'")

        # 相似查询
        similar_queries = [
            "Python code for quicksort implementation",
            "How to write quicksort in Python?",
            "Quicksort algorithm Python version",
        ]

        hit_count = 0

        for i, query in enumerate(similar_queries, 1):
            print(f"\n{i}. 查询相似问题: '{query}'")
            result = cache.get(query, source=CacheSource.CODEX_PLAN.value)

            if result.status == CacheStatus.HIT:
                hit_count += 1
                print(f"   ✅ 命中! 相似度: {result.similarity_score:.2f}")
                print(
                    f"   匹配策略: {result.match_strategy.value if result.match_strategy else 'N/A'}"
                )
                print(f"   解释: {result.explanation}")

                if result.similarity_score < 0.6:
                    print(f"   ⚠️ 相似度较低: {result.similarity_score:.2f}")
            else:
                print(f"   ⚠️ 未命中 (状态: {result.status.value}) - 相似度可能低于阈值")

        # 至少有一个命中即认为测试通过
        if hit_count > 0:
            print(f"\n✅ 相似性匹配测试通过: {hit_count}/{len(similar_queries)} 个查询命中")
            return True
        else:
            print(f"\n❌ 相似性匹配测试失败: 0/{len(similar_queries)} 个查询命中")
            return False


def test_negative_paths() -> bool:
    """
    测试负路径 (错误签名或失效策略)

    步骤:
    1. 测试过期条目
    2. 测试完全不同内容的查询
    3. 测试空输入
    """
    print("\n=== 测试负路径 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir) / "test_cache"
        cache = CodexCache(cache_dir=cache_dir, memory_limit=10)

        all_passed = True

        # 1. 测试过期条目
        print("1. 测试过期条目...")
        test_input = "What is the capital of France?"
        test_payload = {"answer": "Paris"}

        # 创建TTL很短的条目
        entry = cache.put(
            raw_input=test_input,
            payload=test_payload,
            source=CacheSource.CODEX_PLAN.value,
            ttl_seconds=1,  # 1秒TTL
        )

        print(f"   创建条目，TTL=1秒")

        # 立即查询 (应为hit)
        result1 = cache.get(test_input)
        if result1.status != CacheStatus.HIT:
            print(f"   ❌ 预期立即查询为HIT, 实际: {result1.status.value}")
            all_passed = False
        else:
            print(f"   ✅ 立即查询命中")

        # 等待过期
        time.sleep(1.5)

        # 再次查询 (应为expired)
        result2 = cache.get(test_input)
        if result2.status != CacheStatus.EXPIRED:
            print(f"   ❌ 预期过期后为EXPIRED, 实际: {result2.status.value}")
            all_passed = False
        else:
            print(f"   ✅ 条目正确过期")

        # 2. 测试完全不同内容的查询
        print("\n2. 测试完全不同内容...")
        cache.put(
            raw_input="Python programming tutorial",
            payload={"content": "Learn Python basics"},
            source=CacheSource.CODEX_PLAN.value,
        )

        unrelated_query = "What is the weather forecast for tomorrow?"
        result = cache.get(unrelated_query)

        if result.status != CacheStatus.MISS:
            print(f"   ❌ 预期不相关查询为MISS, 实际: {result.status.value}")
            all_passed = False
        else:
            print(f"   ✅ 不相关查询正确返回MISS")

        # 3. 测试空输入
        print("\n3. 测试空输入...")
        empty_result = cache.get("")
        if empty_result.status != CacheStatus.MISS:
            print(f"   ❌ 预期空输入为MISS, 实际: {empty_result.status.value}")
            all_passed = False
        else:
            print(f"   ✅ 空输入正确处理")

        # 4. 测试规范化器
        print("\n4. 测试签名规范化器...")
        normalizer = TaskSignatureNormalizer()

        test_cases = [
            ("Hello, World! How are you?", "hello how world you"),
            (
                "The quick brown fox jumps over the lazy dog",
                "brown dog fox jumps lazy over quick",
            ),
            ("Python programming for beginners", "beginners programming python"),
        ]

        for input_text, expected in test_cases:
            normalized = normalizer.normalize(input_text)
            if normalized != expected:
                print(f"   ❌ 规范化失败: '{input_text}'")
                print(f"       预期: '{expected}'")
                print(f"       实际: '{normalized}'")
                all_passed = False
            else:
                print(f"   ✅ '{input_text[:20]}...' -> '{normalized}'")

        return all_passed


def test_stats_smoke() -> bool:
    """
    测试命中统计冒烟测试

    验证统计功能正常工作
    """
    print("\n=== 测试命中统计冒烟测试 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir) / "test_cache"
        cache = CodexCache(cache_dir=cache_dir, memory_limit=10)

        # 生成一些测试数据
        test_cases = [
            ("Question 1 about Python", {"ans": "Answer 1"}),
            ("Question 2 about Java", {"ans": "Answer 2"}),
            ("Question 3 about JavaScript", {"ans": "Answer 3"}),
        ]

        # 写入缓存
        for input_text, payload in test_cases:
            cache.put(
                raw_input=input_text,
                payload=payload,
                source=CacheSource.CODEX_PLAN.value,
                estimated_save_seconds=2.0,
                estimated_save_tokens=50,
            )

        # 进行一些查询 (混合命中/未命中)
        queries = [
            "Question 1 about Python",  # 命中 (精确)
            "Python question 1",  # 可能相似性命中
            "Question about Java",  # 可能相似性命中
            "Unknown question",  # 未命中
            "JavaScript related question",  # 可能相似性命中
        ]

        for query in queries:
            result = cache.get(query)
            status_str = result.status.value
            if result.entry:
                status_str += f" (相似度: {result.similarity_score:.2f})"
            print(f"   查询: '{query[:30]}...' -> {status_str}")

        # 获取统计
        stats = cache.get_stats()
        report = cache.generate_report()

        print(f"\n统计摘要:")
        print(f"   总条目数: {stats['total_entries']}")
        print(f"   总命中数: {stats['total_hits']}")
        print(f"   总未命中数: {stats['total_misses']}")
        print(f"   命中率: {stats['hit_rate']:.2%}")
        print(f"   总节省时间: {stats['total_save_seconds']:.1f}秒")
        print(f"   平均每次命中节省: {stats['avg_save_seconds_per_hit']:.1f}秒")

        print(f"\n报告健康状态: {report['health']['status']}")
        print(f"缓存位置: {report['cache_location']}")

        # 验证基本统计完整性
        required_keys = ["total_entries", "total_hits", "total_misses", "hit_rate"]
        for key in required_keys:
            if key not in stats:
                print(f"   ❌ 缺少统计键: {key}")
                return False

        if not isinstance(stats["hit_rate"], float):
            print(f"   ❌ 命中率应为浮点数")
            return False

        if stats["hit_rate"] < 0 or stats["hit_rate"] > 1:
            print(f"   ❌ 命中率超出范围: {stats['hit_rate']}")
            return False

        print("   ✅ 统计冒烟测试通过")
        return True


def test_integration_with_existing_artifacts() -> bool:
    """
    测试与现有artifacts/metrics系统的集成

    验证缓存报告可以输出到现有metrics系统
    """
    print("\n=== 测试与现有artifacts/metrics系统集成 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir) / "test_cache"
        cache = CodexCache(cache_dir=cache_dir, memory_limit=10)

        # 模拟一些使用
        for i in range(5):
            cache.put(
                raw_input=f"Test question {i} about caching",
                payload={"answer": f"Test answer {i}"},
                source=(
                    CacheSource.CODEX_PLAN.value if i % 2 == 0 else CacheSource.CODEX_REVIEW.value
                ),
                estimated_save_seconds=1.5 * i,
                estimated_save_tokens=30 * i,
            )

        # 生成报告
        report = cache.generate_report()

        # 验证报告结构
        required_report_keys = [
            "timestamp",
            "cache_location",
            "memory_entries",
            "stats",
            "health",
        ]
        for key in required_report_keys:
            if key not in report:
                print(f"   ❌ 报告缺少键: {key}")
                return False

        # 验证报告可以序列化为JSON (模拟写入文件)
        try:
            report_json = json.dumps(report, indent=2)
            print(f"   ✅ 报告可序列化为JSON ({len(report_json)} 字符)")

            # 模拟写入到现有artifacts目录
            artifacts_dir = Path(tmpdir) / "workspace" / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)

            report_file = artifacts_dir / "codex_cache_report.json"
            with open(report_file, "w") as f:
                json.dump(report, f, indent=2)

            print(f"   ✅ 报告写入文件: {report_file}")

            # 验证文件可读
            with open(report_file, "r") as f:
                loaded_report = json.load(f)

            if loaded_report["timestamp"] == report["timestamp"]:
                print(f"   ✅ 报告文件可正确读取")
            else:
                print(f"   ❌ 报告文件读取失败")
                return False

        except Exception as e:
            print(f"   ❌ 报告序列化/写入失败: {e}")
            return False

        # 输出报告摘要供检查
        print(f"\n报告摘要:")
        print(f"   缓存位置: {report['cache_location']}")
        print(f"   内存条目: {report['memory_entries']}")
        print(f"   命中率: {report['stats']['hit_rate']:.2%}")
        print(f"   健康状态: {report['health']['status']}")
        print(f"   总节省时间: {report['health']['total_savings_seconds']:.1f}秒")

        return True


def main() -> int:
    """主测试函数"""
    print("Codex缓存回归验证测试")
    print("=" * 50)

    test_results = []

    # 运行所有测试
    test_functions = [
        ("miss_write_hit_loop", test_miss_write_hit_loop),
        ("similarity_matching", test_similarity_matching),
        ("negative_paths", test_negative_paths),
        ("stats_smoke", test_stats_smoke),
        ("integration_with_artifacts", test_integration_with_existing_artifacts),
    ]

    for test_name, test_func in test_functions:
        try:
            print(f"\n>>> 运行测试: {test_name}")
            success = test_func()
            test_results.append((test_name, success))

            if success:
                print(f"✅ 测试 {test_name} 通过")
            else:
                print(f"❌ 测试 {test_name} 失败")

        except Exception as e:
            print(f"❌ 测试 {test_name} 异常: {e}")
            import traceback

            traceback.print_exc()
            test_results.append((test_name, False))

    # 汇总结果
    print("\n" + "=" * 50)
    print("测试结果汇总:")

    passed = sum(1 for _, success in test_results if success)
    total = len(test_results)

    for test_name, success in test_results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {test_name:30} {status}")

    print(f"\n总计: {passed}/{total} 个测试通过 ({passed / total * 100:.1f}%)")

    if passed == total:
        print("\n🎉 所有测试通过! Codex缓存系统验证完成。")
        return 0
    else:
        print("\n⚠️  部分测试失败，需要检查实现。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
