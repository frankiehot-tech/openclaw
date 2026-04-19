#!/usr/bin/env python3
"""
测试Python导入缓存问题
"""

import importlib
import os
import sys

# 添加路径
sys.path.append(os.path.dirname(__file__))

# 第一次导入
print("=== 第一次导入 maref_roma_integration ===")
import maref_roma_integration

print(f"模块: {maref_roma_integration}")
print(f"模块路径: {maref_roma_integration.__file__}")
print(f"类: {maref_roma_integration.MarefRomaIntegration}")

# 检查create_agent方法
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
    print("\n尝试调用create_agent...")
    try:
        agent = instance.create_agent("guardian")
        print(f"✅ create_agent调用成功: {agent}")
    except Exception as e:
        print(f"❌ create_agent调用失败: {e}")
except Exception as e:
    print(f"❌ 实例化失败: {e}")

# 重新加载模块
print("\n=== 重新加载模块 ===")
importlib.reload(maref_roma_integration)
print(f"模块重新加载完成")

# 再次检查
print("\n再次检查...")
maref_class = maref_roma_integration.MarefRomaIntegration
print(f"方法列表: {[m for m in dir(maref_class) if 'create' in m or 'agent' in m]}")

# 尝试实例化
print("\n尝试重新实例化...")
try:
    instance = maref_class()
    print(f"实例化成功: {instance}")

    # 检查实例方法
    print(f"实例方法: {[m for m in dir(instance) if 'create' in m or 'agent' in m]}")

    # 尝试调用create_agent
    print("\n尝试调用create_agent...")
    try:
        agent = instance.create_agent("guardian")
        print(f"✅ create_agent调用成功: {agent}")
    except Exception as e:
        print(f"❌ create_agent调用失败: {e}")
except Exception as e:
    print(f"❌ 实例化失败: {e}")

print("\n=== 测试完成 ===")
