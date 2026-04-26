#!/usr/bin/env python3
"""测试预计算功能"""

import time
from integrated_hexagram_state_manager import IntegratedHexagramStateManager


def test_precomputation():
    """测试预计算功能"""
    print("=== 状态分析预计算测试 ===")

    try:
        # 创建管理器但不预计算
        print("\n🔧 创建管理器（无预计算）...")
        start_time = time.time()
        manager = IntegratedHexagramStateManager("hetu_hexagram_mapping.json")
        manager.initialize_state("000000")
        init_time = time.time() - start_time
        print(f"  初始化时间: {init_time:.3f}秒")
        print(f"  初始缓存大小: {len(manager._analysis_cache)}")

        # 测试首次分析时间
        print("\n🔍 测试首次分析（无预计算）")
        test_states = ["000000", "111111", "010101", "101010"]
        first_times = []
        for state in test_states:
            start_time = time.time()
            analysis = manager.analyze_state(state)
            elapsed = time.time() - start_time
            first_times.append(elapsed)
            if analysis:
                print(f"  {state}: {elapsed:.6f}秒")

        avg_first_time = sum(first_times) / len(first_times)
        print(f"  平均首次分析时间: {avg_first_time:.6f}秒")

        # 执行预计算
        print("\n🔧 执行预计算...")
        precompute_start = time.time()
        manager.precompute_all_analysis()
        precompute_time = time.time() - precompute_start
        print(f"  预计算时间: {precompute_time:.3f}秒")
        print(f"  缓存大小: {len(manager._analysis_cache)}")

        # 测试预计算后的分析时间
        print("\n🔍 测试预计算后分析")
        cached_times = []
        for state in test_states:
            start_time = time.time()
            analysis = manager.analyze_state(state)
            elapsed = time.time() - start_time
            cached_times.append(elapsed)
            if analysis:
                print(f"  {state}: {elapsed:.6f}秒")

        avg_cached_time = sum(cached_times) / len(cached_times)
        print(f"  平均缓存分析时间: {avg_cached_time:.6f}秒")

        if avg_first_time > 0:
            speedup = (
                avg_first_time / avg_cached_time
                if avg_cached_time > 0
                else float("inf")
            )
            print(f"  加速比: {speedup:.1f}倍")

        # 性能对比：批量查询
        print("\n🔍 批量查询性能对比")
        import random

        # 生成1000个随机状态查询
        random_states = [f"{random.randint(0, 63):06b}" for _ in range(1000)]

        # 预计算版本的性能
        start_time = time.time()
        for state in random_states:
            _ = manager.analyze_state(state)
        cached_batch_time = time.time() - start_time

        print(f"  预计算版本 (1000次): {cached_batch_time:.3f}秒")
        print(f"  平均每查询: {cached_batch_time/1000*1000:.1f}ms")

        # 估算无预计算版本的性能（基于首次分析时间）
        # 假设有50%缓存命中率（实际会更低，因为随机）
        estimated_miss_rate = 0.5  # 保守估计
        estimated_hit_rate = 0.5
        estimated_time = (
            1000 * estimated_miss_rate * avg_first_time
            + 1000 * estimated_hit_rate * avg_cached_time
        )

        print(f"  估算无预计算版本 (50%命中率): {estimated_time:.3f}秒")
        print(f"  性能提升: {estimated_time/cached_batch_time:.1f}倍")

        # 内存使用分析
        print("\n💾 内存使用分析")
        print(
            f"  卦象缓存内存: {manager.cache_manager.hamming_matrix.memory_usage()/1024:.1f} KB"
        )
        print(f"  分析缓存条目: {len(manager._analysis_cache)}")
        # 粗略估算：每个StateAnalysis约500字节
        analysis_cache_mem = len(manager._analysis_cache) * 500
        print(f"  分析缓存估算: {analysis_cache_mem/1024:.1f} KB")
        print(
            f"  总缓存内存: {(manager.cache_manager.hamming_matrix.memory_usage() + analysis_cache_mem)/1024:.1f} KB"
        )

        print("\n🎉 预计算测试完成！")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_precomputation()
