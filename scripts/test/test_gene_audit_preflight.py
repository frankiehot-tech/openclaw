#!/usr/bin/env python3
"""测试基因管理审计任务的预检验证"""

import sys

sys.path.insert(0, "/Volumes/1TB-M2/openclaw/scripts")

from athena_ai_plan_runner import validate_build_preflight

# 读取指令文件
instruction_path = (
    "/Volumes/1TB-M2/openclaw/OpenHuman-Athena-OpenHuman基因管理Agent工程实施方案-VSCode执行指令.md"
)

with open(instruction_path, "r", encoding="utf-8") as f:
    instruction_text = f.read()

# 创建模拟的item对象
item = {
    "id": "gene_mgmt_audit",
    "title": "OpenHuman-Athena-基因管理系统实施审计-Codex审计指令",
    "instruction_path": instruction_path,
    "stage": "build",
    "executor": "opencode",
    "metadata": {
        "priority": "S0",
        "lane": "build_auto",
        "epic": "gene_management",
        "category": "audit",
        "phase": "G3",
    },
}

print("🔍 测试基因管理审计任务预检验证...")
print(f"📄 指令文件: {instruction_path}")
print(f"📏 文件行数: {len(instruction_text.splitlines())}")
print(f"📋 任务标题: {item['title']}")
print(f"🏷️  Epic: {item['metadata']['epic']}")

# 测试预检验证
passed, reason, should_manual_hold = validate_build_preflight(
    instruction_text=instruction_text, item=item, max_targets=8, require_acceptance=True
)

print(f"\n📊 测试结果:")
print(f"   通过: {passed}")
print(f"   原因: {reason}")
print(f"   应降级为manual_hold: {should_manual_hold}")

if passed:
    print("✅ 预检验证通过！任务应该可以正常执行。")
else:
    print("❌ 预检验证失败。原因:")
    print(f"   {reason}")
    if should_manual_hold:
        print("   任务应降级为manual_hold状态")

# 测试错误场景：非基因管理任务
print("\n🔍 测试非基因管理审计任务...")
item2 = {
    "id": "other_audit",
    "title": "其他系统审计-Codex审计指令",
    "instruction_path": instruction_path,
    "metadata": {"epic": "other_epic"},
}

passed2, reason2, should_manual_hold2 = validate_build_preflight(
    instruction_text=instruction_text, item=item2, max_targets=8, require_acceptance=True
)

print(f"   通过: {passed2}")
print(f"   原因: {reason2}")
print(f"   应降级为manual_hold: {should_manual_hold2}")

# 测试没有item的情况
print("\n🔍 测试没有item的情况...")
passed3, reason3, should_manual_hold3 = validate_build_preflight(
    instruction_text=instruction_text, item=None, max_targets=8, require_acceptance=True
)

print(f"   通过: {passed3}")
print(f"   原因: {reason3}")
print(f"   应降级为manual_hold: {should_manual_hold3}")
