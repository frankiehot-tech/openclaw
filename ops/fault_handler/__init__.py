"""
统一故障处理模块 — 替代分散的 51 个 fix_*.py 脚本

设计原则:
1. 每个故障类型对应一个 Handler，而非一个脚本
2. Handler 有明确的: 触发条件 → 修复动作 → 验证步骤
3. 修复不成功 → 自动升级告警 (而非再写 fix_v2.py)
4. 幂等性: 同一故障不重复处理

使用方式:
    from ops.fault_handler import FaultRegistry
    registry = FaultRegistry.auto_discover()
    registry.handle(fault_context)
"""
