#!/usr/bin/env python3
"""测试状态转换原因记录修复"""

import os
import sys

sys.path.append(os.path.dirname(__file__))

from maref_memory_integration import wrap_state_manager_transition
from maref_memory_manager import MAREFMemoryManager


# 模拟一个简单的状态管理器类用于测试
class MockStateManager:
    def __init__(self, initial_state="000000"):
        self.current_state = initial_state

    def transition(self, new_state):
        print(f"MockStateManager.transition called with new_state={new_state}")
        # 简单的模拟转换
        self.current_state = new_state
        return True

    def get_hexagram_name(self, state=None):
        return "䷁坤为地"


def test_reason_recording():
    """测试状态转换原因记录"""
    print("=== 测试状态转换原因记录 ===")

    # 初始化内存管理器
    memory_manager = MAREFMemoryManager()

    # 创建模拟状态管理器
    state_manager = MockStateManager("000000")

    # 包装状态管理器
    wrapped_manager = wrap_state_manager_transition(state_manager, memory_manager)

    # 测试状态转换，带有reason参数
    print("\n1. 测试带reason的状态转换...")
    success = wrapped_manager.transition(
        new_state="000001",
        trigger_agent="test_agent",
        context={"test": True},
        reason="测试状态转换原因",
    )

    print(f"转换结果: {success}")
    print(f"当前状态: {state_manager.current_state}")

    # 检查数据库中的记录
    print("\n2. 检查数据库记录...")
    try:
        conn = memory_manager.conn
        cursor = conn.cursor()
        cursor.execute("""
            SELECT content_json, timestamp, source_agent
            FROM memory_entries
            WHERE entry_type = 'state_transition'
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        result = cursor.fetchone()

        if result:
            import json

            content_json, timestamp, source_agent = result
            content = json.loads(content_json)
            print(f"最新状态转换记录:")
            print(f"  源状态: {content.get('from_state')}")
            print(f"  目标状态: {content.get('to_state')}")
            print(f"  原因: {content.get('transition_reason', '未找到')}")
            print(f"  触发者: {source_agent}")
            print(f"  时间: {timestamp}")

            # 验证reason是否正确
            if content.get("transition_reason") == "测试状态转换原因":
                print("✅ 原因记录正确")
                return True
            else:
                print(
                    f"❌ 原因记录不正确: 期望'测试状态转换原因', 实际'{content.get('transition_reason')}'"
                )
                return False
        else:
            print("❌ 没有找到状态转换记录")
            return False

    except Exception as e:
        print(f"❌ 检查数据库时出错: {e}")
        return False


def test_empty_reason():
    """测试空reason的处理"""
    print("\n=== 测试空reason处理 ===")

    memory_manager = MAREFMemoryManager()
    state_manager = MockStateManager("000001")
    wrapped_manager = wrap_state_manager_transition(state_manager, memory_manager)

    print("\n3. 测试空reason状态转换...")
    success = wrapped_manager.transition(
        new_state="000011", trigger_agent="test_agent2", reason=""  # 空字符串
    )

    print(f"转换结果: {success}")

    # 检查数据库
    try:
        conn = memory_manager.conn
        cursor = conn.cursor()
        cursor.execute("""
            SELECT content_json FROM memory_entries
            WHERE entry_type = 'state_transition'
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        result = cursor.fetchone()

        if result:
            import json

            content = json.loads(result[0])
            reason = content.get("transition_reason", "")
            print(f"空reason记录值: '{reason}'")
            if reason == "":
                print("✅ 空reason正确处理")
                return True
            else:
                print(f"❌ 空reason处理不正确: '{reason}'")
                return False
    except Exception as e:
        print(f"❌ 检查数据库时出错: {e}")
        return False


if __name__ == "__main__":
    print("开始测试状态转换原因记录修复")

    test1 = test_reason_recording()
    test2 = test_empty_reason()

    if test1 and test2:
        print("\n✅ 所有测试通过")
    else:
        print("\n❌ 测试失败")
        sys.exit(1)
