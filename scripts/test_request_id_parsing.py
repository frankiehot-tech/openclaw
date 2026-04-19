#!/usr/bin/env python3
"""
测试RequestIDGenerator的解析能力
"""

import sys

sys.path.insert(0, "/Volumes/1TB-M2/openclaw/mini-agent")

from agent.core.request_id_generator import RequestIDGenerator


def main():
    generator = RequestIDGenerator()

    # 测试各种格式
    test_ids = [
        "exp_run_20260417_100957_5_9",  # 实验记录格式
        "req_20260417_092513_d9fd25d3",  # 成本记录格式
        "exp_req_20260417_212706_f071b6c9",  # 标准格式
        "test_req_20260417_212706_abc123",  # 测试格式
        "exp_run_20260417_100957_5",  # 缺少部分
        "invalid_format",  # 无效格式
    ]

    for rid in test_ids:
        parsed = generator.parse(rid)
        print(f"ID: {rid}")
        print(f"  标准格式: {parsed['is_standard_format']}")
        print(f"  前缀: {parsed['prefix']}")
        print(f"  时间戳: {parsed['timestamp_str']}")
        print(f"  唯一ID: {parsed['unique_id']}")
        print(f"  时间对象: {parsed['timestamp']}")
        print()

    # 测试时间窗口匹配
    print("=== 时间窗口匹配测试 ===")
    id1 = "exp_run_20260417_100957_5_9"
    id2 = "req_20260417_092513_d9fd25d3"

    timestamp1 = generator.extract_timestamp(id1)
    timestamp2 = generator.extract_timestamp(id2)

    print(f"ID1时间戳: {timestamp1}")
    print(f"ID2时间戳: {timestamp2}")

    if timestamp1 and timestamp2:
        time_diff = abs((timestamp1 - timestamp2).total_seconds())
        print(f"时间差: {time_diff}秒 ({time_diff/3600:.2f}小时)")

        # 测试不同时间窗口
        for window in [300, 1800, 3600, 7200]:  # 5分钟, 30分钟, 1小时, 2小时
            match = generator.match_time_window(id1, id2, window)
            print(f"  窗口{window}秒: {'匹配' if match else '不匹配'}")


if __name__ == "__main__":
    main()
