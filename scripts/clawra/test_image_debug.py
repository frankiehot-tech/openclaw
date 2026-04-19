#!/usr/bin/env python3
"""
测试图像URL模式调试 - 非交互式版本
"""

import os
import sys

sys.path.append(os.path.dirname(__file__))

# 导入调试模块的函数
from debug_doubao_images import capture_all_images, suggest_detection_rules


def main():
    print("=== 非交互式图像URL模式调试 ===")

    # 捕获初始图像
    initial_data = capture_all_images()

    if initial_data:
        print("\n✅ 初始图像捕获完成")

        # 直接测试图像生成并再次捕获
        print("\n=== 自动测试图像生成并捕获 ===")
        # 我们需要导入test_image_generation_and_capture
        from debug_doubao_images import test_image_generation_and_capture

        generated_data = test_image_generation_and_capture()

    # 提供改进建议
    suggest_detection_rules()

    print("\n✅ 调试完成！")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
