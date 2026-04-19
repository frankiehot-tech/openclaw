#!/usr/bin/env python3
"""
测试create_agent修复
"""

import importlib
import os
import sys

# 添加路径
sys.path.append(os.path.dirname(__file__))

# 重新加载模块
print("=== 重新加载maref_roma_integration ===")
if "maref_roma_integration" in sys.modules:
    del sys.modules["maref_roma_integration"]

import maref_roma_integration

importlib.reload(maref_roma_integration)

# 检查方法
print(f"\n检查create_agent方法...")
maref_class = maref_roma_integration.MarefRomaIntegration
print(f"方法列表: {[m for m in dir(maref_class) if 'create' in m or 'agent' in m]}")

# 尝试实例化
print("\n尝试实例化...")
try:
    instance = maref_class()
    print(f"实例化成功: {instance}")

    # 检查实例方法
    print(f"实例方法: {[m for m in dir(instance) if 'create' in m or 'agent' in m]}")

    # 尝试调用create_agent
    print("\n尝试调用create_agent('guardian', 'guardian_supervision')...")
    try:
        agent = instance.create_agent("guardian", "guardian_supervision")
        print(f"✅ create_agent调用成功: {agent}")

        # 检查agent_id属性
        if hasattr(agent, "agent_id"):
            print(f"   智能体ID: {agent.agent_id}")
        else:
            print(f"   警告: 智能体缺少agent_id属性")

        # 检查智能体类型
        if hasattr(agent, "agent_type"):
            print(f"   智能体类型: {agent.agent_type}")

    except Exception as e:
        print(f"❌ create_agent调用失败: {e}")
        import traceback

        traceback.print_exc()
except Exception as e:
    print(f"❌ 实例化失败: {e}")
    import traceback

    traceback.print_exc()

print("\n=== 测试完成 ===")
