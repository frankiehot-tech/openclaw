#!/usr/bin/env python3
"""
Qwen Router 测试脚本
测试 vision_router.py 中的 describe_with_qwen 函数
"""

import os
import sys

# 添加 agent_system 到路径
project_root = "/Volumes/1TB-M2/openclaw"
sys.path.insert(0, os.path.join(project_root, "agent_system"))

from vision.vision_router import describe_with_qwen

# 测试图片路径
IMAGE_PATH = "/Users/frankie/Desktop/phase13_6_qwen_test/input/screen.png"


def main():
    print("=== Qwen Router 测试 ===")
    print(f"输入图片: {IMAGE_PATH}")

    # 检查图片是否存在
    if not os.path.exists(IMAGE_PATH):
        print(f"错误: 图片不存在 - {IMAGE_PATH}")
        sys.exit(1)

    # 调用 Qwen 描述
    result = describe_with_qwen(IMAGE_PATH)

    print(f"\n返回结果: {result}")

    if result.get("ok"):
        print(f"\n最终输出: {result.get('text')}")
        return 0
    else:
        print(f"\n失败: {result.get('error')}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
