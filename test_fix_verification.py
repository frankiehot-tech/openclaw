#!/usr/bin/env python3
"""验证queue_item_from_manifest修复"""

import sys
from pathlib import Path

# 添加scripts目录到路径
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

try:
    import athena_web_desktop_compat as compat

    print("✅ 导入模块成功")
except Exception as e:
    print(f"❌ 导入失败: {e}")
    sys.exit(1)

# 模拟数据
mock_route = {
    "route_id": "aiplan_gene_management",
    "queue_id": "openhuman_aiplan_gene_management_20260405",
    "name": "基因管理",
    "manifest_path": "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_gene_management_20260405.json",
}

mock_manifest_item = {
    "id": "test_task_123",
    "title": "测试任务",
    "entry_stage": "build",
    "risk_level": "medium",
    "metadata": {},
}

mock_route_state = {
    "items": {"test_task_123": {"status": "pending", "progress_percent": 0}},
    "current_item_ids": [],
}

print(f"\n🧪 测试queue_item_from_manifest函数...")
try:
    result = compat.queue_item_from_manifest(mock_route, mock_manifest_item, mock_route_state)
    print(f"✅ 函数调用成功")
    print(f"   返回字典键: {list(result.keys())}")

    # 检查关键字段
    missing = []
    if "task_id" not in result:
        missing.append("task_id")
    if "route_id" not in result:
        missing.append("route_id")

    if missing:
        print(f"❌ 缺失字段: {missing}")
    else:
        print(f"✅ 包含关键字段:")
        print(f"   task_id: {result.get('task_id')}")
        print(f"   route_id: {result.get('route_id')}")

    # 打印所有字段
    print(f"\n📋 所有字段值:")
    for key, value in sorted(result.items()):
        print(f"   {key}: {repr(value)[:80]}")

except Exception as e:
    print(f"❌ 函数调用失败: {e}")
    import traceback

    traceback.print_exc()

# 测试实际队列数据
print(f"\n📊 测试实际队列数据...")
try:
    # 导入build_queue_payload
    from athena_web_desktop_compat import build_queue_payload

    payload = build_queue_payload()
    routes = payload.get("routes", [])
    print(f"✅ 获取到 {len(routes)} 个队列")

    for route in routes:
        queue_id = route.get("queue_id")
        items = route.get("items", [])
        print(f"\n  队列: {queue_id}, 任务数: {len(items)}")

        if items:
            first_item = items[0]
            print(f"    第一个任务的键: {list(first_item.keys())}")

            # 检查字段
            if "task_id" in first_item and "route_id" in first_item:
                print(f"    ✅ 包含task_id和route_id字段")
                print(f"      task_id: {first_item.get('task_id')}")
                print(f"      route_id: {first_item.get('route_id')}")
            else:
                print(f"    ❌ 缺少task_id或route_id字段")
                missing = []
                if "task_id" not in first_item:
                    missing.append("task_id")
                if "route_id" not in first_item:
                    missing.append("route_id")
                print(f"      缺失: {missing}")

                # 查看实际包含的字段
                print(f"      实际字段: {list(first_item.keys())}")
                break

except Exception as e:
    print(f"❌ 测试实际队列失败: {e}")
    import traceback

    traceback.print_exc()

print(f"\n✅ 验证完成")
