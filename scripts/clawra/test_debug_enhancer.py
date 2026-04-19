#!/usr/bin/env python3
"""
调试增强执行器
"""

import os
import sys

sys.path.append(os.path.dirname(__file__))

import logging

logging.basicConfig(level=logging.DEBUG)

from external.ROMA.doubao_cli_prototype import DoubaoCLI
from javascript_enhancer import EnhancedDoubaoCLI


def test_debug():
    print("=== 调试增强执行器 ===")

    # 创建实例
    doubao = DoubaoCLI()
    enhanced_doubao = EnhancedDoubaoCLI(doubao)

    print("\n1. 测试基础JavaScript执行...")
    result = enhanced_doubao.execute_javascript(1, 1, "document.title")
    print(f"结果: {result}")

    print("\n2. 检查执行器的统计...")
    stats = enhanced_doubao.get_stats()
    print(f"统计: {stats}")

    print("\n3. 测试智能元素查找（带详细调试）...")

    # 先打开AI页面
    print("\n首先打开豆包AI页面...")
    doubao.open_doubao_ai()
    import time

    time.sleep(3)  # 等待页面加载

    # 手动调用执行器方法以查看原始输出
    executor = enhanced_doubao.executor

    # 生成智能查询代码
    from javascript_enhancer import SelectorStrategy

    js_code = SelectorStrategy.create_smart_query("input")

    print(f"\n生成的JavaScript代码长度: {len(js_code)}")
    print(f"代码片段: {js_code[:200]}...")

    # 直接执行以查看原始输出
    print("\n执行智能查询...")
    raw_result = executor.base_executor(1, 1, js_code)
    print(f"原始输出: {raw_result}")

    # 使用增强执行器
    print("\n使用增强执行器...")
    enhanced_result = executor.execute_with_retry(js_code, 1, 1, "调试查找")
    print(f"增强结果: success={enhanced_result.success}, output={enhanced_result.output}")
    print(f"错误类型: {enhanced_result.error_type}, 错误消息: {enhanced_result.error_message}")

    # 尝试解析
    if enhanced_result.success:
        print("\n尝试解析输出...")
        output = enhanced_result.output
        if "JavaScript执行结果: " in output:
            json_str = output.split("JavaScript执行结果: ", 1)[1]
        else:
            json_str = output

        print(f"提取的JSON字符串: {json_str}")

        import json

        try:
            data = json.loads(json_str)
            print(f"解析成功: {data}")
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            print(f"JSON字符串长度: {len(json_str)}")
            print(f"JSON字符串内容: {json_str}")
    else:
        print("\n执行失败，检查错误...")

    print("\n=== 调试完成 ===")


if __name__ == "__main__":
    test_debug()
