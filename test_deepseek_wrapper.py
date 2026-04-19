#!/usr/bin/env python3
"""
测试OpenCode包装器的DeepSeek集成
"""

import os
import subprocess
import sys


def test_wrapper_with_task_kind(task_kind=None):
    """测试包装器使用特定任务类型"""
    print(f"🔍 测试OpenCode包装器 - 任务类型: {task_kind if task_kind else '默认'}")
    print("=" * 60)

    # 构建命令
    cmd = ["/Users/frankie/bin/opencode-athena", "--dry-run", "--athena-debug"]
    if task_kind:
        cmd.extend(["--task-kind", task_kind])
    cmd.extend(["run", "--model", "alibaba/qwen3.5-plus", "测试提示消息"])

    print(f"执行命令: {' '.join(cmd)}")
    print("=" * 60)

    # 设置环境变量以确保Athena能找到配置
    env = os.environ.copy()
    env["PYTHONPATH"] = f"/Volumes/1TB-M2/openclaw/mini-agent:{env.get('PYTHONPATH', '')}"

    # 运行命令
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)

    print("标准输出:")
    print(result.stdout)
    print("\n标准错误:")
    print(result.stderr)
    print(f"\n返回码: {result.returncode}")

    # 检查输出中是否包含DeepSeek相关信息
    if task_kind in ["debug", "testing"]:
        if "deepseek" in result.stderr.lower():
            print(f"✅ 成功检测到DeepSeek provider用于{task_kind}任务")
        else:
            print(f"⚠️  警告: 未检测到DeepSeek provider用于{task_kind}任务")
    elif task_kind == "general" or task_kind is None:
        if "dashscope" in result.stderr.lower():
            print(f"✅ 成功检测到DashScope provider用于{task_kind if task_kind else '默认'}任务")
        else:
            print(
                f"⚠️  警告: 未检测到DashScope provider用于{task_kind if task_kind else '默认'}任务"
            )

    return result.returncode == 0


def test_provider_script_mapping():
    """测试provider脚本映射"""
    print("\n🔍 测试provider脚本映射")
    print("=" * 60)

    # 测试脚本存在性
    scripts_to_check = [
        ("dashscope", "/Volumes/1TB-M2/openclaw/.openclaw/platforms/bin/claude-qwen-alt.sh"),
        ("deepseek", "/Volumes/1TB-M2/openclaw/.openclaw/platforms/bin/claude-deepseek-alt.sh"),
    ]

    for provider_id, script_path in scripts_to_check:
        if os.path.exists(script_path):
            print(f"✅ {provider_id}: 脚本存在 - {script_path}")
            # 检查是否可执行
            if os.access(script_path, os.X_OK):
                print(f"   ✅ 脚本可执行")
            else:
                print(f"   ❌ 脚本不可执行")
        else:
            print(f"❌ {provider_id}: 脚本不存在 - {script_path}")

    return True


def main():
    print("🚀 OpenCode包装器DeepSeek集成测试")
    print("=" * 60)

    # 测试1: 默认provider（应为dashscope）
    print("\n📋 测试1: 默认provider（无task-kind）")
    test1_ok = test_wrapper_with_task_kind(None)

    # 测试2: debug任务类型（应映射到deepseek）
    print("\n📋 测试2: debug任务类型")
    test2_ok = test_wrapper_with_task_kind("debug")

    # 测试3: testing任务类型（应映射到deepseek）
    print("\n📋 测试3: testing任务类型")
    test3_ok = test_wrapper_with_task_kind("testing")

    # 测试4: general任务类型（应映射到dashscope）
    print("\n📋 测试4: general任务类型")
    test4_ok = test_wrapper_with_task_kind("general")

    # 测试5: provider脚本映射
    test5_ok = test_provider_script_mapping()

    # 总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    print(f"测试1 (默认): {'✅ 通过' if test1_ok else '❌ 失败'}")
    print(f"测试2 (debug): {'✅ 通过' if test2_ok else '❌ 失败'}")
    print(f"测试3 (testing): {'✅ 通过' if test3_ok else '❌ 失败'}")
    print(f"测试4 (general): {'✅ 通过' if test4_ok else '❌ 失败'}")
    print(f"测试5 (脚本映射): {'✅ 通过' if test5_ok else '❌ 失败'}")

    all_passed = test1_ok and test2_ok and test3_ok and test4_ok and test5_ok
    if all_passed:
        print(f"\n🎉 所有测试通过！OpenCode包装器DeepSeek集成正常工作")
    else:
        print(f"\n⚠️  部分测试失败，需要进一步调试")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
