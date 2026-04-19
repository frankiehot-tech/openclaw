#!/usr/bin/env python3
"""全域压力测试集成测试"""

import asyncio
import json
import time
from datetime import datetime

import requests


def test_claude_code_integration():
    """测试Claude Code集成"""
    try:
        response = requests.post(
            "http://127.0.0.1:3000/v1/chat/completions",
            headers={
                "Authorization": "Bearer athena-openhuman-integration-key",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": "集成测试消息"}],
                "max_tokens": 50,
            },
            timeout=30,
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Claude Code集成测试失败: {e}")
        return False


def test_queue_operations():
    """测试队列操作"""
    try:
        # 检查队列文件状态
        import glob
        import os

        queue_files = glob.glob(".openclaw/plan_queue/*.json")
        if len(queue_files) == 0:
            return False

        # 读取一个队列文件验证完整性
        with open(queue_files[0], "r") as f:
            data = json.load(f)

        return "queue_id" in data and "items" in data
    except Exception as e:
        print(f"队列操作测试失败: {e}")
        return False


def test_system_health():
    """测试系统健康状态"""
    try:
        # 检查关键进程
        import psutil

        critical_processes = ["athena_ai_plan_runner", "claude-code-router"]
        running_processes = [p.info["name"] for p in psutil.process_iter(["name"])]

        for proc in critical_processes:
            if not any(proc in p for p in running_processes):
                return False

        return True
    except Exception as e:
        print(f"系统健康测试失败: {e}")
        return False


async def run_integration_tests():
    """运行集成测试套件"""
    tests = [
        ("Claude Code集成", test_claude_code_integration),
        ("队列操作", test_queue_operations),
        ("系统健康", test_system_health),
    ]

    results = {}

    for test_name, test_func in tests:
        print(f"🧪 执行测试: {test_name}")

        start_time = time.time()
        success = test_func()
        duration = time.time() - start_time

        results[test_name] = {
            "success": success,
            "duration": duration,
            "timestamp": datetime.now().isoformat(),
        }

        status = "✅ 通过" if success else "❌ 失败"
        print(f"   {status} | 耗时: {duration:.2f}秒")

        # 测试间隔
        await asyncio.sleep(5)

    return results


async def main():
    """主函数"""
    print("🚀 开始集成测试套件")
    print("=" * 50)

    # 运行测试
    results = await run_integration_tests()

    # 输出总结
    print("\n📊 集成测试总结:")
    print("=" * 50)

    passed = sum(1 for r in results.values() if r["success"])
    total = len(results)

    print(f"通过率: {passed}/{total} ({passed/total*100:.1f}%)")

    # 保存结果
    output_dir = "workspace/full_domain_stress_test_20260408"
    with open(f"{output_dir}/integration_test_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n📁 测试结果已保存到: {output_dir}/integration_test_results.json")


if __name__ == "__main__":
    asyncio.run(main())
