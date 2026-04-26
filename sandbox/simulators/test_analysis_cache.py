#!/usr/bin/env python3
"""测试状态分析缓存功能"""

import sys
import time

# 添加项目根目录到路径
sys.path.insert(0, "/Volumes/1TB-M2/openclaw")

from integrated_hexagram_state_manager import IntegratedHexagramStateManager


def test_analysis_cache():
    """测试分析缓存性能"""
    print("=== 状态分析缓存测试 ===")

    try:
        # 创建管理器
        manager = IntegratedHexagramStateManager("hetu_hexagram_mapping.json")
        manager.initialize_state("000000")

        # 测试1: 首次分析（缓存未命中）
        print("\n🔍 测试1: 首次分析（缓存未命中）")
        start_time = time.time()
        analysis1 = manager.analyze_state("010101")
        first_time = time.time() - start_time

        if analysis1:
            print(
                f"  卦象: {analysis1.hexagram_name} ({analysis1.binary_representation})"
            )
            print(f"  质量评分: {analysis1.quality_score:.2f}/10")
            print(f"  到完美状态距离: {analysis1.evolution_distance_to_perfect}")
            print(f"  计算时间: {first_time:.6f}秒")

        # 测试2: 相同状态再次分析（缓存命中）
        print("\n🔍 测试2: 缓存命中测试")
        start_time = time.time()
        analysis2 = manager.analyze_state("010101")
        cached_time = time.time() - start_time

        if analysis2:
            print(f"  质量评分: {analysis2.quality_score:.2f}/10")
            print(f"  计算时间: {cached_time:.6f}秒")
            print(
                f"  加速比: {first_time/cached_time:.1f}倍"
                if cached_time > 0
                else "N/A"
            )

        # 测试3: 不同状态分析
        print("\n🔍 测试3: 不同状态分析")
        test_states = ["000000", "111111", "010101", "101010"]
        for state in test_states:
            start_time = time.time()
            analysis = manager.analyze_state(state)
            elapsed = time.time() - start_time
            if analysis:
                print(
                    f"  {state}: {analysis.hexagram_name}, 质量 {analysis.quality_score:.1f}, 时间 {elapsed:.6f}秒"
                )

        # 测试4: 批量性能测试
        print("\n🔍 测试4: 批量性能测试")
        import random

        # 生成随机状态列表（有重复）
        random_states = [f"{random.randint(0, 63):06b}" for _ in range(1000)]

        # 无缓存版本（模拟）：每次重新计算
        print("  模拟无缓存版本（1000次）...")
        # 这里我们无法直接禁用缓存，但可以估算
        # 首次计算时间可以作为无缓存基准
        if analysis1:
            estimated_no_cache = first_time * 1000
            print(f"  估算无缓存时间: {estimated_no_cache:.3f}秒")

        # 有缓存版本（实际）
        print("  有缓存版本（1000次，有重复）...")
        start_time = time.time()
        for state in random_states:
            _ = manager.analyze_state(state)
        actual_with_cache = time.time() - start_time

        print(f"  实际缓存时间: {actual_with_cache:.3f}秒")

        # 估算缓存命中率（根据重复情况）
        unique_states = set(random_states)
        hit_rate = (1000 - len(unique_states)) / 1000 * 100
        print(f"  估算缓存命中率: {hit_rate:.1f}% ({len(unique_states)}个唯一状态)")

        # 测试5: 缓存大小
        print("\n🔍 测试5: 缓存统计")
        cache_size = len(manager._analysis_cache)
        print(f"  缓存条目数: {cache_size}/64")
        print(f"  内存估算: {cache_size * 500:.0f} 字节 (approx)")

        print("\n🎉 状态分析缓存测试完成！")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_analysis_cache()
