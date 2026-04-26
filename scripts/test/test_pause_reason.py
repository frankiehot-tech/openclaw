#!/usr/bin/env python3
"""
快速验证 pause_reason 字段是否出现在队列 API 响应中。
"""

import sys

sys.path.insert(0, "/Volumes/1TB-M2/openclaw/scripts")

import json

from athena_web_desktop_compat import build_queue_payload


def main():
    payload = build_queue_payload()
    print("=== 队列 API 响应 ===")
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    # 检查每个 route 是否有 pause_reason 字段
    for route in payload.get("routes", []):
        print(f"\n路由: {route.get('name')}")
        print(f"  queue_status: {route.get('queue_status')}")
        print(f"  pause_reason: {route.get('pause_reason')}")
        if "pause_reason" not in route:
            print("  ⚠️ 缺少 pause_reason 字段")
        else:
            print("  ✅ 包含 pause_reason 字段")


if __name__ == "__main__":
    main()
