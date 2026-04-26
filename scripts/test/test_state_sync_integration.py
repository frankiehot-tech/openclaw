#!/usr/bin/env python3
"""
测试StateSyncContract集成到athena_ai_plan_runner.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scripts.athena_ai_plan_runner import load_route_state, set_route_item_state


def main():
    print("🚀 测试StateSyncContract集成")
    print("=" * 60)

    # 创建一个测试route
    test_route = {
        "queue_id": "openhuman_aiplan_build_priority_20260328",
        "queue_state_path": "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_build_priority_20260328.json",
    }

    # 加载当前状态
    route_state = load_route_state(test_route)
    print(f"✅ 加载队列状态成功: queue_id={test_route['queue_id']}")

    # 获取一个测试任务ID（查找第一个任务）
    items = route_state.get("items", {})
    if not items:
        print("⚠️  队列中没有任务，无法测试")
        return 1

    test_item_id = list(items.keys())[0]
    print(f"🔍 使用测试任务ID: {test_item_id}")

    # 测试1: 使用StateSyncContract更新状态
    print(f"\n🧪 测试1: 使用StateSyncContract更新状态")
    print(f"   更新: status='testing', progress_percent=50")

    try:
        set_route_item_state(
            test_route,
            route_state,
            test_item_id,
            status="testing",
            progress_percent=50,
            test_flag="state_sync_test",
        )
        print("✅ set_route_item_state调用成功")

        # 验证更新是否生效
        updated_state = load_route_state(test_route)
        updated_item = updated_state.get("items", {}).get(test_item_id, {})

        if updated_item.get("status") == "testing" and updated_item.get("progress_percent") == 50:
            print("✅ 状态更新验证成功")
            print(
                f"   更新后的状态: status={updated_item.get('status')}, progress_percent={updated_item.get('progress_percent')}"
            )

            # 检查是否有test_flag字段（StateSyncContract可能不会保留这个字段）
            if "test_flag" in updated_item:
                print("⚠️  test_flag字段被保留（可能使用了原机制）")
            else:
                print("ℹ️  test_flag字段未保留（可能使用了StateSyncContract）")
        else:
            print("⚠️  状态更新验证失败")
            print(f"   实际状态: {updated_item}")

    except Exception as e:
        print(f"❌ set_route_item_state调用失败: {str(e)}")
        import traceback

        traceback.print_exc()
        return 1

    # 测试2: 恢复原状态
    print(f"\n🧪 测试2: 恢复原状态")
    original_status = items[test_item_id].get("status", "completed")
    original_progress = items[test_item_id].get("progress_percent", 100)

    print(f"   恢复: status={original_status}, progress_percent={original_progress}")

    try:
        set_route_item_state(
            test_route,
            updated_state,
            test_item_id,
            status=original_status,
            progress_percent=original_progress,
        )
        print("✅ 状态恢复成功")
    except Exception as e:
        print(f"❌ 状态恢复失败: {str(e)}")
        return 1

    print(f"\n📊 测试完成总结")
    print(f"   - 队列ID: {test_route['queue_id']}")
    print(f"   - 测试任务: {test_item_id}")
    print(f"   - 原状态: status={original_status}, progress={original_progress}")
    print(f"   - 测试状态已恢复")

    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⏹️ 用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
