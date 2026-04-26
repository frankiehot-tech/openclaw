#!/usr/bin/env python3
"""
DashScope配置与Athena多LLM策略对齐测试
验证所有组件使用一致的配置
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import yaml


def test_environment_variables():
    """测试环境变量一致性"""
    print("🔍 测试环境变量一致性")
    print("=" * 60)

    # 关键环境变量
    key_vars = [
        "DASHSCOPE_API_KEY",
        "DASHSCOPE_API_BASE_URL",
        "ANTHROPIC_BASE_URL",
        "ANTHROPIC_MODEL",
        "OPENAI_BASE_URL",
        "OPENAI_API_KEY",
    ]

    issues = []
    for var in key_vars:
        value = os.environ.get(var)
        if value:
            # 隐藏敏感信息
            display_value = value
            if "KEY" in var or "TOKEN" in var:
                if len(value) > 16:
                    display_value = f"{value[:8]}...{value[-8:]}"
            print(f"  {var}: {display_value}")

            # 检查DashScope端点
            if var.endswith("_BASE_URL") and value:
                if "dashscope.aliyuncs.com" not in value:
                    issues.append(f"{var} 不包含正确的DashScope域名: {value}")
        else:
            print(f"  {var}: ❌ 未设置")
            if var in ["DASHSCOPE_API_KEY", "DASHSCOPE_API_BASE_URL"]:
                issues.append(f"缺少必需的环境变量: {var}")

    return issues


def test_athena_provider_config():
    """测试Athena provider配置"""
    print("\n🔍 测试Athena Provider配置")
    print("=" * 60)

    config_path = "/Volumes/1TB-M2/openclaw/mini-agent/config/athena_providers.yaml"
    issues = []

    if not os.path.exists(config_path):
        issues.append(f"Athena provider配置文件不存在: {config_path}")
        return issues

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # 检查DashScope配置
        dashscope_config = config.get("providers", {}).get("dashscope", {})
        if not dashscope_config:
            issues.append("Athena配置中缺少dashscope provider")
            return issues

        print(f"  Provider ID: {dashscope_config.get('id')}")
        print(f"  标签: {dashscope_config.get('label')}")
        print(f"  基础URL: {dashscope_config.get('base_url')}")
        print(f"  API模式: {dashscope_config.get('api_mode')}")
        print(f"  默认模型: {dashscope_config.get('default_model')}")

        # 验证端点
        base_url = dashscope_config.get("base_url", "")
        if not base_url:
            issues.append("DashScope配置中缺少base_url")
        elif "dashscope.aliyuncs.com" not in base_url:
            issues.append(f"DashScope base_url不包含正确域名: {base_url}")

        # 验证API模式
        api_mode = dashscope_config.get("api_mode", "")
        if api_mode != "openai-compatible":
            issues.append(f"DashScope API模式应为'openai-compatible'，实际为: {api_mode}")

        # 检查默认配置
        defaults = config.get("defaults", {})
        primary_provider = defaults.get("primary_provider", "")
        primary_model = defaults.get("primary_model", "")

        print(f"\n  默认Provider: {primary_provider}")
        print(f"  默认模型: {primary_model}")

        if primary_provider != "dashscope":
            issues.append(f"默认provider应为'dashscope'，实际为: {primary_provider}")

    except Exception as e:
        issues.append(f"读取Athena配置时出错: {e}")

    return issues


def test_opencode_wrapper():
    """测试OpenCode包装器"""
    print("\n🔍 测试OpenCode包装器")
    print("=" * 60)

    wrapper_path = "/Volumes/1TB-M2/openclaw/bin/opencode-athena"
    issues = []

    if not os.path.exists(wrapper_path):
        issues.append(f"OpenCode包装器不存在: {wrapper_path}")
        return issues

    # 测试包装器的--env-only选项
    try:
        result = subprocess.run(
            [wrapper_path, "--env-only"], capture_output=True, text=True, env=os.environ.copy()
        )

        if result.returncode != 0:
            issues.append(f"OpenCode包装器执行失败: {result.stderr[:200]}")

        # 检查关键输出
        output = result.stdout + result.stderr
        checks = [
            ("DASHSCOPE_API_BASE_URL", "DashScope端点设置"),
            ("ANTHROPIC_BASE_URL", "Anthropic兼容端点"),
            ("从Athena获取DashScope配置", "Athena集成"),
        ]

        for check_text, check_name in checks:
            if check_text in output:
                print(f"  ✓ {check_name}: 正常")
            else:
                issues.append(f"包装器缺少{check_name}: {check_text}")

    except Exception as e:
        issues.append(f"测试OpenCode包装器时出错: {e}")

    return issues


def test_qwen_alternative_script():
    """测试Qwen替代脚本"""
    print("\n🔍 测试Qwen替代脚本")
    print("=" * 60)

    script_path = "/Volumes/1TB-M2/openclaw/.openclaw/platforms/bin/claude-qwen-alt.sh"
    issues = []

    if not os.path.exists(script_path):
        issues.append(f"Qwen替代脚本不存在: {script_path}")
        return issues

    # 检查脚本配置
    try:
        with open(script_path, "r", encoding="utf-8") as f:
            content = f.read()

        checks = [
            ("DASHSCOPE_COMPATIBLE_URL", "DashScope兼容URL配置"),
            ("https://dashscope.aliyuncs.com/compatible-mode/v1", "正确的端点URL"),
            ("qwen3.6-plus", "默认模型"),
        ]

        for check_text, check_name in checks:
            if check_text in content:
                print(f"  ✓ {check_name}: 正常")
            else:
                issues.append(f"Qwen脚本缺少{check_name}")

    except Exception as e:
        issues.append(f"检查Qwen脚本时出错: {e}")

    return issues


def test_dashscope_api_connection():
    """测试DashScope API连接"""
    print("\n🔍 测试DashScope API连接")
    print("=" * 60)

    issues = []
    api_key = os.environ.get("DASHSCOPE_API_KEY")

    if not api_key:
        issues.append("未设置DASHSCOPE_API_KEY环境变量")
        return issues

    # 测试模型列表API
    try:
        import requests

        # 测试原生DashScope API
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        # 测试OpenAI兼容端点
        print("  测试OpenAI兼容端点...")
        response = requests.get(
            "https://dashscope.aliyuncs.com/compatible-mode/v1/models", headers=headers, timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            model_count = len(data.get("data", []))
            print(f"  ✓ OpenAI兼容端点正常，找到{model_count}个模型")
        else:
            issues.append(f"OpenAI兼容端点请求失败: {response.status_code}")

        # 测试原生DashScope API
        print("  测试原生DashScope API...")
        response = requests.get(
            "https://dashscope.aliyuncs.com/api/v1/models?page_size=5", headers=headers, timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                model_count = len(data.get("output", {}).get("models", []))
                print(f"  ✓ 原生DashScope API正常，找到{model_count}个模型")
            else:
                issues.append(f"原生DashScope API返回错误: {data.get('message')}")
        else:
            issues.append(f"原生DashScope API请求失败: {response.status_code}")

    except ImportError:
        issues.append("缺少requests库，跳过API连接测试")
    except Exception as e:
        issues.append(f"测试DashScope API连接时出错: {e}")

    return issues


def test_queue_runner_config():
    """测试队列运行器配置"""
    print("\n🔍 测试队列运行器配置")
    print("=" * 60)

    runner_path = "/Volumes/1TB-M2/openclaw/scripts/athena_ai_plan_runner.py"
    issues = []

    if not os.path.exists(runner_path):
        issues.append(f"队列运行器不存在: {runner_path}")
        return issues

    # 检查OpenCode调用
    try:
        with open(runner_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 检查是否使用包装器
        if "/Volumes/1TB-M2/openclaw/bin/opencode-athena" in content:
            print("  ✓ 队列运行器使用OpenCode包装器")
        else:
            issues.append("队列运行器未使用OpenCode包装器")

        # 检查OpenCode相关配置
        checks = [
            ("executor.*=.*['\"]opencode['\"]", "执行器配置"),
            ("opencode_build", "运行器模式"),
        ]

        for pattern, check_name in checks:
            import re

            if re.search(pattern, content):
                print(f"  ✓ {check_name}: 正常")
            else:
                issues.append(f"队列运行器缺少{check_name}")

    except Exception as e:
        issues.append(f"检查队列运行器时出错: {e}")

    return issues


def main():
    """主函数"""
    print("🚀 DashScope配置与Athena多LLM策略对齐测试")
    print("=" * 60)

    all_issues = []

    # 运行所有测试
    tests = [
        ("环境变量", test_environment_variables),
        ("Athena Provider配置", test_athena_provider_config),
        ("OpenCode包装器", test_opencode_wrapper),
        ("Qwen替代脚本", test_qwen_alternative_script),
        ("DashScope API连接", test_dashscope_api_connection),
        ("队列运行器", test_queue_runner_config),
    ]

    for test_name, test_func in tests:
        issues = test_func()
        all_issues.extend([f"{test_name}: {issue}" for issue in issues])

    # 输出总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)

    if all_issues:
        print(f"❌ 发现 {len(all_issues)} 个问题:")
        for i, issue in enumerate(all_issues, 1):
            print(f"  {i}. {issue}")

        print("\n💡 建议:")
        print("  1. 检查环境变量设置")
        print("  2. 验证Athena provider配置")
        print("  3. 确保OpenCode包装器正确配置")
        print("  4. 测试DashScope API连接")

        return 1
    else:
        print("✅ 所有测试通过！DashScope配置与Athena多LLM策略对齐正常。")
        print("\n🎯 配置状态:")
        print("  • 环境变量一致性: ✓")
        print("  • Athena Provider配置: ✓")
        print("  • OpenCode包装器: ✓")
        print("  • Qwen替代方案: ✓")
        print("  • DashScope API连接: ✓")
        print("  • 队列运行器集成: ✓")

        return 0


if __name__ == "__main__":
    sys.exit(main())
