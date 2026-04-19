#!/usr/bin/env python3
"""
测试性能优化效果
"""

import sys
import time
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from external.ROMA.hexagram_state_manager import HexagramStateManager
from maref_memory_integration import (
    get_memory_manager,
    init_memory_manager,
    wrap_state_manager_transition,
)
from run_maref_daily_report import create_integration_environment


def test_performance_mode():
    """测试性能模式"""
    print("=== 性能优化测试 ===")

    # 测试1: 性能模式
    print("\n1. 测试性能模式...")

    # 重置内存管理器单例
    import maref_memory_integration

    if hasattr(maref_memory_integration, "_memory_manager_instance"):
        if maref_memory_integration._memory_manager_instance:
            if hasattr(maref_memory_integration._memory_manager_instance, "close"):
                maref_memory_integration._memory_manager_instance.close()
        maref_memory_integration._memory_manager_instance = None

    # 初始化性能模式内存管理器
    memory_manager = init_memory_manager(performance_mode=True)
    print(f"  性能模式已启用: {memory_manager.performance_mode}")

    # 创建集成环境
    state_manager, agents = create_integration_environment()

    # 测试状态转换性能
    test_transitions = ["000001", "000011", "000111", "000000"]

    perf_times = []
    for i, state in enumerate(test_transitions):
        start_time = time.perf_counter()
        success = state_manager.transition(
            new_state=state, trigger_agent="tester", reason="性能测试"
        )
        elapsed = time.perf_counter() - start_time
        elapsed_ms = elapsed * 1000
        perf_times.append(elapsed_ms)
        print(f"  转换 {i+1}: {state} - {elapsed_ms:.3f}ms - {'成功' if success else '失败'}")

    avg_perf_time = sum(perf_times) / len(perf_times) if perf_times else 0
    print(f"  性能模式平均时间: {avg_perf_time:.3f}ms")

    # 获取性能统计
    stats = memory_manager.get_performance_stats()
    print(
        f"  性能统计: 同步写入={stats['sync_write_count']}, 异步写入={stats['async_write_count']}"
    )

    # 测试2: 正常模式
    print("\n2. 测试正常模式...")

    # 重置内存管理器单例
    if hasattr(maref_memory_integration, "_memory_manager_instance"):
        if maref_memory_integration._memory_manager_instance:
            if hasattr(maref_memory_integration._memory_manager_instance, "close"):
                maref_memory_integration._memory_manager_instance.close()
        maref_memory_integration._memory_manager_instance = None

    # 初始化正常模式内存管理器
    memory_manager = init_memory_manager(performance_mode=False)
    print(f"  性能模式已禁用: {memory_manager.performance_mode}")

    # 创建集成环境
    state_manager, agents = create_integration_environment()

    # 测试状态转换性能
    normal_times = []
    for i, state in enumerate(test_transitions):
        start_time = time.perf_counter()
        success = state_manager.transition(
            new_state=state, trigger_agent="tester", reason="性能测试"
        )
        elapsed = time.perf_counter() - start_time
        elapsed_ms = elapsed * 1000
        normal_times.append(elapsed_ms)
        print(f"  转换 {i+1}: {state} - {elapsed_ms:.3f}ms - {'成功' if success else '失败'}")

    avg_normal_time = sum(normal_times) / len(normal_times) if normal_times else 0
    print(f"  正常模式平均时间: {avg_normal_time:.3f}ms")

    # 获取性能统计
    stats = memory_manager.get_performance_stats()
    print(
        f"  性能统计: 同步写入={stats['sync_write_count']}, 异步写入={stats['async_write_count']}, 队列大小={stats['queue_size']}"
    )

    # 性能比较
    print("\n=== 性能比较 ===")
    print(f"性能模式: {avg_perf_time:.3f}ms")
    print(f"正常模式: {avg_normal_time:.3f}ms")
    print(
        f"性能提升: {((avg_normal_time - avg_perf_time) / avg_normal_time * 100):.1f}%"
        if avg_normal_time > 0
        else "N/A"
    )

    # 检查是否达到0.5ms阈值
    threshold = 0.5
    perf_meets = avg_perf_time <= threshold
    normal_meets = avg_normal_time <= threshold

    print(f"\n=== 阈值检查 (目标: {threshold}ms) ===")
    print(f"性能模式: {'✅ 达标' if perf_meets else '❌ 未达标'} ({avg_perf_time:.3f}ms)")
    print(f"正常模式: {'✅ 达标' if normal_meets else '❌ 未达标'} ({avg_normal_time:.3f}ms)")

    # 清理
    memory_manager.close()

    return perf_meets, normal_meets, avg_perf_time, avg_normal_time


def test_async_writer():
    """测试异步写入器"""
    print("\n=== 测试异步写入器 ===")

    # 重置内存管理器单例
    import maref_memory_integration

    if hasattr(maref_memory_integration, "_memory_manager_instance"):
        if maref_memory_integration._memory_manager_instance:
            if hasattr(maref_memory_integration._memory_manager_instance, "close"):
                maref_memory_integration._memory_manager_instance.close()
        maref_memory_integration._memory_manager_instance = None

    # 初始化正常模式内存管理器（启用异步写入）
    memory_manager = init_memory_manager(performance_mode=False)

    # 快速创建多个状态转换
    from maref_memory_integration import record_state_transition

    print("创建100个状态转换记录...")
    start_time = time.perf_counter()

    for i in range(100):
        record_state_transition(
            from_state=f"{i:06b}",
            to_state=f"{(i+1)%64:06b}",
            trigger_agent="tester",
            transition_reason=f"测试转换 {i}",
        )

    elapsed = time.perf_counter() - start_time
    print(f"创建100个记录耗时: {elapsed:.3f}秒")
    print(f"平均每个记录: {(elapsed/100*1000):.3f}ms")

    # 获取性能统计
    stats = memory_manager.get_performance_stats()
    print(
        f"性能统计: 同步写入={stats['sync_write_count']}, 异步写入={stats['async_write_count']}, 队列大小={stats['queue_size']}"
    )

    # 等待异步写入完成
    print("等待异步写入完成...")
    time.sleep(2)

    # 再次获取统计
    stats = memory_manager.get_performance_stats()
    print(
        f"异步写入后统计: 同步写入={stats['sync_write_count']}, 异步写入={stats['async_write_count']}, 队列大小={stats['queue_size']}"
    )

    memory_manager.close()


if __name__ == "__main__":
    try:
        perf_meets, normal_meets, perf_time, normal_time = test_performance_mode()

        # 如果正常模式未达标，测试异步写入器
        if not normal_meets:
            test_async_writer()

        print("\n=== 测试总结 ===")
        if perf_meets:
            print("✅ 性能模式已达到0.5ms阈值")
        else:
            print("❌ 性能模式未达到0.5ms阈值")

        if normal_meets:
            print("✅ 正常模式已达到0.5ms阈值")
        else:
            print("❌ 正常模式未达到0.5ms阈值，需要进一步优化")

    except Exception as e:
        print(f"测试失败: {e}")
        import traceback

        traceback.print_exc()
