#!/usr/bin/env python3
"""简单测试状态转换原因记录"""

import json
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(__file__))

from maref_memory_manager import MAREFMemoryManager


def test_direct_record():
    """直接测试record_state_transition方法"""
    print("=== 直接测试record_state_transition方法 ===")

    # 初始化内存管理器
    memory_manager = MAREFMemoryManager()

    # 直接调用record_state_transition
    print("\n1. 记录带reason的状态转换...")
    entry_id = memory_manager.record_state_transition(
        from_state="000000",
        to_state="000001",
        trigger_agent="test_direct",
        context={"direct_test": True},
        transition_reason="直接测试原因",
    )

    print(f"记录ID: {entry_id}")

    # 直接从数据库检查
    db_path = "/Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db"
    print(f"\n2. 检查数据库: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 查找刚刚创建的记录
    cursor.execute(
        """
        SELECT content_json, source_agent
        FROM memory_entries
        WHERE entry_id = ?
    """,
        (entry_id,),
    )

    result = cursor.fetchone()
    conn.close()

    if result:
        content_json, source_agent = result
        content = json.loads(content_json)
        print(f"记录内容:")
        print(f"  源状态: {content.get('from_state')}")
        print(f"  目标状态: {content.get('to_state')}")
        print(f"  原因: {content.get('transition_reason')}")
        print(f"  触发者: {source_agent}")

        if content.get("transition_reason") == "直接测试原因":
            print("✅ 直接记录测试通过")
            return True
        else:
            print(f"❌ 原因不匹配: '{content.get('transition_reason')}'")
            return False
    else:
        print("❌ 未找到记录")
        return False


def test_wrapper_integration():
    """测试包装器集成"""
    print("\n=== 测试包装器集成 ===")

    from maref_memory_integration import wrap_state_manager_transition

    # 模拟状态管理器
    class MockStateManager:
        def __init__(self):
            self.current_state = "000000"

        def transition(self, new_state):
            print(f"  原始transition调用: {self.current_state} -> {new_state}")
            self.current_state = new_state
            return True

    # 初始化内存管理器
    memory_manager = MAREFMemoryManager()

    # 创建状态管理器并包装
    state_manager = MockStateManager()
    print("\n3. 包装状态管理器...")
    wrapped = wrap_state_manager_transition(state_manager, memory_manager)

    print("\n4. 调用包装后的transition...")
    # 现在transition方法应该接受额外参数
    success = wrapped.transition(
        new_state="000010", trigger_agent="wrapper_test", reason="包装器测试原因"
    )

    print(f"调用结果: {success}, 当前状态: {state_manager.current_state}")

    # 检查数据库
    db_path = "/Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT content_json, source_agent
        FROM memory_entries
        WHERE entry_type = 'state_transition'
        ORDER BY timestamp DESC
        LIMIT 1
    """)

    result = cursor.fetchone()
    conn.close()

    if result:
        content_json, source_agent = result
        content = json.loads(content_json)
        print(f"\n5. 最新记录:")
        print(f"  源状态: {content.get('from_state')}")
        print(f"  目标状态: {content.get('to_state')}")
        print(f"  原因: {content.get('transition_reason')}")
        print(f"  触发者: {source_agent}")

        if source_agent == "wrapper_test" and content.get("transition_reason") == "包装器测试原因":
            print("✅ 包装器集成测试通过")
            return True
        else:
            print(f"❌ 记录不匹配")
            return False
    else:
        print("❌ 未找到记录")
        return False


if __name__ == "__main__":
    print("测试状态转换原因记录")

    test1 = test_direct_record()
    test2 = test_wrapper_integration()

    if test1 and test2:
        print("\n✅ 所有测试通过")
    else:
        print("\n❌ 测试失败")
        sys.exit(1)
