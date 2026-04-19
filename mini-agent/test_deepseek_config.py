#!/usr/bin/env python3
"""
测试DeepSeek配置是否在Athena Provider Registry中正确加载
"""

import logging
import os
import sys

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.core.provider_registry import ProviderRegistry


def test_deepseek_config():
    """测试DeepSeek配置"""
    print("🔍 测试DeepSeek配置加载...")

    try:
        # 获取Provider Registry实例
        registry = ProviderRegistry()
        print(f"✅ Provider Registry 加载成功")
        print(f"   版本: {registry.get_config().version}")

        # 检查DeepSeek provider是否存在
        config = registry.get_config()
        providers = config.providers
        print(f"✅ 共找到 {len(providers)} 个 provider")

        # 查找DeepSeek
        deepseek_provider = None
        for provider_id, provider in providers.items():
            print(f"   - {provider_id}: {provider.label}")
            if provider_id == "deepseek":
                deepseek_provider = provider

        if deepseek_provider:
            print(f"✅ DeepSeek provider 找到!")
            print(f"   ID: {deepseek_provider.id}")
            print(f"   标签: {deepseek_provider.label}")
            print(f"   基础URL: {deepseek_provider.base_url}")
            print(f"   认证环境变量: {deepseek_provider.auth_env_key}")
            print(f"   默认模型: {deepseek_provider.default_model}")
            print(f"   成本模式: {deepseek_provider.cost_mode}")

            # 检查环境变量
            api_key = os.environ.get(deepseek_provider.auth_env_key)
            if api_key:
                print(f"✅ DeepSeek API密钥已设置 (长度: {len(api_key)})")
            else:
                print(f"⚠️  DeepSeek API密钥未设置: {deepseek_provider.auth_env_key}")
                print(f"   提示: 设置环境变量 {deepseek_provider.auth_env_key}")

            # 检查模型
            models = deepseek_provider.models
            print(f"✅ 共 {len(models)} 个模型:")
            for model_id, model in models.items():
                print(f"   - {model_id}: {model.label}")
                print(f"     输入成本: {model.cost_per_1k_input} 元/1k")
                print(f"     输出成本: {model.cost_per_1k_output} 元/1k")

        else:
            print(f"❌ DeepSeek provider 未找到!")
            print(f"   请检查 athena_providers.yaml 配置")

        # 检查任务类型映射
        config = registry.get_config()
        task_map = config.task_kind_provider_map
        print(f"✅ 任务类型映射:")
        for task_kind, provider_id in task_map.items():
            print(f"   - {task_kind} -> {provider_id}")

        # 检查debug/testing任务是否映射到deepseek
        if task_map.get("debug") == "deepseek":
            print(f"✅ debug任务已正确映射到DeepSeek")
        else:
            print(f"⚠️  debug任务未映射到DeepSeek: {task_map.get('debug')}")

        if task_map.get("testing") == "deepseek":
            print(f"✅ testing任务已正确映射到DeepSeek")
        else:
            print(f"⚠️  testing任务未映射到DeepSeek: {task_map.get('testing', '未定义')}")

        # 成本对比分析
        print(f"\n💰 成本对比分析:")
        dashscope_cost = None
        deepseek_cost = None

        for provider_id, provider in providers.items():
            if provider_id == "dashscope" and provider.models:
                # 获取第一个模型
                first_model = list(provider.models.values())[0]
                dashscope_cost = first_model.cost_per_1k_input
                print(f"   DashScope ({first_model.id}): {dashscope_cost} 元/1k输入")
            elif provider_id == "deepseek" and provider.models:
                # 获取第一个模型
                first_model = list(provider.models.values())[0]
                deepseek_cost = first_model.cost_per_1k_input
                print(f"   DeepSeek ({first_model.id}): {deepseek_cost} 元/1k输入")

        if dashscope_cost and deepseek_cost:
            savings = (dashscope_cost - deepseek_cost) / dashscope_cost * 100
            print(f"   💰 成本节省: {savings:.1f}%")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    print("=" * 60)
    print("DeepSeek配置测试")
    print("=" * 60)

    success = test_deepseek_config()

    print("=" * 60)
    if success:
        print("✅ 测试完成")
    else:
        print("❌ 测试失败")
    print("=" * 60)
