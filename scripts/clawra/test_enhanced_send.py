#!/usr/bin/env python3
"""
测试增强版豆包AI消息发送
"""

import os
import sys
import time

sys.path.append(os.path.dirname(__file__))

from external.ROMA.doubao_cli_prototype import DoubaoCLI


def test_enhanced_send():
    print("=== 测试增强版豆包AI消息发送 ===")

    # 创建实例
    doubao = DoubaoCLI()

    print("1. 测试基础豆包功能...")
    try:
        version = doubao.get_version()
        print(f"✅ 豆包版本: {version}")
    except Exception as e:
        print(f"❌ 获取版本失败: {e}")
        return False

    print("\n2. 测试打开豆包AI页面...")
    try:
        result = doubao.open_doubao_ai()
        print(f"✅ {result}")
        time.sleep(3)  # 等待页面加载
    except Exception as e:
        print(f"❌ 打开AI页面失败: {e}")
        return False

    print("\n3. 测试增强JavaScript执行...")
    try:
        result = doubao.execute_javascript(1, 1, "document.title")
        print(f"✅ JavaScript执行结果: {result}")
    except Exception as e:
        print(f"❌ JavaScript执行失败: {e}")
        print("提示：需要在豆包中启用'允许Apple事件中的JavaScript'")
        print("路径：查看 > 开发者 > 允许Apple事件中的JavaScript")
        return False

    print("\n4. 测试增强发送消息功能...")
    try:
        test_message = "你好，这是一个增强版发送测试消息"
        print(f"发送测试消息: {test_message}")

        # 使用增强版发送
        result = doubao.enhanced.send_message_to_ai(test_message, use_enhanced=True)
        print(f"✅ 发送结果: {result}")

        # 等待发送完成
        print("等待5秒让消息发送完成...")
        time.sleep(5)

        return True

    except Exception as e:
        print(f"❌ 发送消息失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        print("\n=== 测试完成 ===")


if __name__ == "__main__":
    success = test_enhanced_send()
    if success:
        print("\n🎉 增强版消息发送测试通过")
        sys.exit(0)
    else:
        print("\n⚠️  增强版消息发送测试失败")
        sys.exit(1)
