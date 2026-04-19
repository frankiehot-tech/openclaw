#!/usr/bin/env python3
"""测试状态转换原因记录集成"""

import sys

sys.path.insert(0, ".")

from external.ROMA.hexagram_state_manager import HexagramStateManager
from maref_memory_integration import wrap_state_manager_transition
from maref_memory_manager import MAREFMemoryManager, MemoryEntryType


def test_hexagram_with_reason():
    """测试状态管理器支持reason参数"""
    print("=== 测试状态管理器支持reason参数 ===")

    # 创建状态管理器
    manager = HexagramStateManager("000000")

    # 测试1: 不带reason参数（向后兼容）
    print("\n1. 测试不带reason参数（向后兼容）:")
    success = manager.transition("000001")
    print(f"   转换成功: {success}, 状态: {manager.current_state}")
    print(f"   历史记录: {manager.state_history[-1]}")

    # 测试2: 带reason参数
    print("\n2. 测试带reason参数:")
    success = manager.transition("000011", reason="测试原因")
    print(f"   转换成功: {success}, 状态: {manager.current_state}")
    print(f"   历史记录: {manager.state_history[-1]}")

    # 检查历史记录中是否包含reason
    history = manager.state_history
    has_reason_unknown = "reason" in history[0] and history[0]["reason"] == "unknown"
    has_reason_test = "reason" in history[1] and history[1]["reason"] == "测试原因"

    print(f"\n3. 验证历史记录:")
    print(f"   第一条记录包含reason='unknown': {has_reason_unknown}")
    print(f"   第二条记录包含reason='测试原因': {has_reason_test}")

    return has_reason_unknown and has_reason_test


def test_wrapper_with_reason():
    """测试包装器传递reason参数"""
    print("\n=== 测试包装器传递reason参数 ===")

    # 创建状态管理器和内存管理器
    manager = HexagramStateManager("000000")
    memory_manager = MAREFMemoryManager()

    # 包装状态管理器
    wrapped = wrap_state_manager_transition(manager, memory_manager)

    # 调用包装后的transition，带reason参数
    print("\n1. 调用包装后的transition:")
    success = wrapped.transition(
        new_state="000001", trigger_agent="test_agent", reason="包装器测试原因"
    )
    print(f"   转换成功: {success}, 状态: {manager.current_state}")

    # 检查状态管理器的历史记录
    print(f"\n2. 状态管理器历史记录:")
    print(f"   {manager.state_history[-1]}")

    # 检查内存管理器中的记录
    print(f"\n3. 检查内存管理器记录:")
    # 查询最新的状态转换记录
    entries = memory_manager.query_memory(
        entry_type=MemoryEntryType.STATE_TRANSITION, source_agent="test_agent", limit=1
    )

    if entries:
        entry = entries[0]
        print(f"   内存记录ID: {entry.entry_id}")
        print(f"   内容: {entry.content}")
        print(f"   触发者: {entry.source_agent}")

        # 验证原因是否正确记录
        content = entry.content
        reason_in_memory = content.get("transition_reason")
        print(f"   内存中的reason: {reason_in_memory}")

        return reason_in_memory == "包装器测试原因"
    else:
        print("   未找到内存记录")
        return False


if __name__ == "__main__":
    print("测试状态转换原因记录集成\n")

    test1_passed = test_hexagram_with_reason()
    test2_passed = test_wrapper_with_reason()

    print("\n=== 测试结果 ===")
    print(f"状态管理器reason支持: {'✅ 通过' if test1_passed else '❌ 失败'}")
    print(f"包装器reason传递: {'✅ 通过' if test2_passed else '❌ 失败'}")

    if test1_passed and test2_passed:
        print("\n✅ 所有测试通过")
        sys.exit(0)
    else:
        print("\n❌ 测试失败")
        sys.exit(1)
