#!/usr/bin/env python3
"""测试缓存集成功能"""

import sys
import time

# 添加项目根目录到路径
sys.path.insert(0, "/Volumes/1TB-M2/openclaw")

from integrated_hexagram_state_manager import IntegratedHexagramStateManager


def test_hamming_distance_cache():
    """测试汉明距离缓存功能"""
    print("=== 汉明距离缓存集成测试 ===")

    try:
        # 创建管理器
        manager = IntegratedHexagramStateManager("hetu_hexagram_mapping.json")
        manager.initialize_state("000000")

        # 测试1: 基本汉明距离计算
        print("\n🔍 测试1: 基本汉明距离计算")
        test_pairs = [
            ("000000", "000001"),  # 距离1
            ("000000", "111111"),  # 距离6
            ("010101", "101010"),  # 距离6
            ("001001", "110110"),  # 距离5
        ]

        for state1, state2 in test_pairs:
            distance = manager.hamming_distance(state1, state2)
            print(f"  {state1} → {state2}: 距离 = {distance}")

        # 测试2: 批量性能测试
        print("\n🔍 测试2: 批量性能测试（1000次计算）")
        import random

        start_time = time.time()
        for _ in range(1000):
            i = random.randint(0, 63)
            j = random.randint(0, 63)
            state1 = f"{i:06b}"
            state2 = f"{j:06b}"
            _ = manager.hamming_distance(state1, state2)
        elapsed = time.time() - start_time

        print(
            f"  1000次汉明距离计算耗时: {elapsed:.3f}秒 ({elapsed/1000*1000:.1f}ms/次)"
        )

        # 测试3: 缓存管理器访问
        print("\n🔍 测试3: 缓存管理器功能")
        cache = manager.cache_manager
        print(f"  缓存版本: {cache.cache_version}")
        print(f"  缓存已初始化: {cache._initialized}")

        # 测试4: 路径查找缓存
        print("\n🔍 测试4: 路径查找缓存")
        path = cache.find_path("000000", "111111")
        print(f"  000000 → 111111 路径: {' → '.join(path)}")
        print(f"  路径长度: {len(path)}")

        # 测试5: 河图-卦象映射缓存
        print("\n🔍 测试5: 河图-卦象映射缓存")
        from integrated_hexagram_state_manager import HetuState

        nearest = cache.select_nearest_hexagram("010101", HetuState.COMPLETED)
        print(f"  010101 到 COMPLETED 的最近卦象: {nearest}")

        print("\n🎉 缓存集成测试完成！")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_hamming_distance_cache()
