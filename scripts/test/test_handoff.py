#!/usr/bin/env python3
"""
测试 handoff 集成
"""

import os
import sys

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 尝试导入 bridge
try:
    # 由于目录名有连字符，使用路径技巧
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "athena_bridge",
        "mini-agent/agent/core/athena_bridge.py"
    )
    bridge_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bridge_module)
    get_bridge = bridge_module.get_bridge
    print("导入成功")
except Exception as e:
    print(f"导入失败: {e}")
    # 备用方法：直接运行脚本
    exec(open("mini-agent/agent/core/athena_bridge.py").read())
    from athena_bridge import get_bridge

bridge = get_bridge()

# 测试 OpenHuman 任务
print("\n1. 测试 OpenHuman distill 任务:")
result = bridge.chat("把这个经验提炼成 Skill", {})
print(f"   成功: {result.get('success')}")
print(f"   领域: {result.get('domain')}")
print(f"   handoff_performed: {result.get('handoff_performed', '未找到')}")
if 'handoff' in result:
    handoff = result['handoff']
    print(f"   handoff 成功: {handoff.get('success', '未找到')}")
    print(f"   handoff 执行: {handoff.get('handoff_performed', '未找到')}")
    print(f"   消息: {handoff.get('message', '未找到')}")

print("\n2. 测试工程任务:")
result2 = bridge.chat("这是一个普通请求", {})
print(f"   成功: {result2.get('success')}")
print(f"   领域: {result2.get('domain')}")
print(f"   handoff_performed: {result2.get('handoff_performed', '未找到')}")
if 'handoff' in result2:
    handoff2 = result2['handoff']
    print(f"   handoff 执行: {handoff2.get('handoff_performed', '未找到')}")

print("\n3. 检查 handoff 逻辑是否生效:")
# 直接检查 handoff 实例
if hasattr(bridge, 'handoff'):
    print("   bridge 有 handoff 属性")
    # 测试 handoff 判断
    import importlib
    handoff_module = importlib.import_module("mini-agent.agent.core.runtime_handoff")
    HandoffRequest = getattr(handoff_module, "HandoffRequest")

    # 跳过，因为导入问题
else:
    print("   bridge 没有 handoff 属性")

print("\n✅ 测试完成")