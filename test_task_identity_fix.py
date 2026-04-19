#!/usr/bin/env python3
"""
测试TaskIdentityContract修复效果
测试日志中发现的argparse错误ID是否能够被正确规范化
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from contracts.task_identity import TaskIdentity, TaskIdentityContract

# 测试日志中发现的错误ID
problematic_ids = [
    "-Agent-基因递归演进-engineering-plan-20260413-095313-task-20260413-095313",
    "-engineering-plan-20260413-095917-task-20260413-095917",
    "-engineering-plan-20260413-095917-task-20260413-095918",
    "-engineering-plan-20260413-095918-task-20260413-095918",
    "-engineering-plan-20260413-095918-task-20260413-095919",
    "-engineering-plan-20260413-095919-task-20260413-095919",
    "-engineering-plan-20260413-095920-task-20260413-095920",
    "-engineering-plan-20260413-121453-task-20260413-121453",
    "-engineering-plan-20260413-121456-task-20260413-121456",
    "-engineering-plan-20260413-220651-task-20260413-220651",
    "-engineering-plan-20260413-220654-task-20260413-220654",
]

print("=== TaskIdentityContract修复测试 ===")
print(f"测试{len(problematic_ids)}个日志中的错误ID")

contract = TaskIdentityContract()

# 1. 审计问题ID
print("\n1. ID审计报告:")
audit = contract.audit_existing_ids(problematic_ids)
print(f"   总计: {audit['total_ids']}个ID")
print(f"   问题ID: {audit['argparse_unsafe_count']}个")
print(f"   问题比例: {audit['problematic_percentage']:.2f}%")

# 2. 批量规范化
print("\n2. 批量规范化结果:")
normalized = contract.bulk_normalize(problematic_ids)

for raw_id, task_id in normalized.items():
    print(f"   {raw_id[:60]}...")
    print(f"     → {task_id.id}")
    print(f"     argparse安全: {task_id.is_argparse_safe()}")
    print()

# 3. 验证argparse安全性
print("\n3. argparse安全性验证:")
all_safe = all(task_id.is_argparse_safe() for task_id in normalized.values())
if all_safe:
    print("   ✅ 所有ID现在都argparse安全")
else:
    unsafe = [tid for raw_id, tid in normalized.items() if not tid.is_argparse_safe()]
    print(f"   ❌ 仍有{len(unsafe)}个ID不安全")
    for tid in unsafe:
        print(f"      - {tid.id}")

# 4. 测试快速修复函数
print("\n4. 快速修复函数测试:")
from contracts.task_identity import fix_argparse_id, validate_id_for_argparse

test_id = "-engineering-plan-20260413-121456-task-20260413-121456"
fixed = fix_argparse_id(test_id)
print(f"   原始: {test_id}")
print(f"   修复后: {fixed}")
print(f"   安全: {validate_id_for_argparse(fixed)}")

print("\n=== 测试完成 ===")
