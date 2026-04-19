#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude Code Router 集成模块
用于 Athena Open Human 与 Claude Code Router 的深度集成

版本: 1.0.0
创建时间: 2026-04-07
"""

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """模型配置数据类"""

    provider: str
    model: str
    temperature: float
    max_tokens: int


@dataclass
class RoutingStrategy:
    """路由策略数据类"""

    fallback_enabled: bool
    health_check_interval: int
    circuit_breaker_failure_threshold: int
    circuit_breaker_reset_timeout: int


class ClaudeCodeIntegration:
    """Claude Code Router 集成类"""

    def __init__(
        self, config_path: str = "/Volumes/1TB-M2/openclaw/.openclaw/claude_code_integration.json"
    ):
        """
        初始化集成类

        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.base_url = self.config.get("base_url", "http://127.0.0.1:3000")
        self.api_key = self.config.get("api_key", "athena-openhuman-integration-key")
        self.timeout = self.config.get("timeout", 300)
        self.retry_count = self.config.get("retry_count", 3)

        # 加载模型映射
        self.model_mapping = self._load_model_mapping()

        # 加载路由策略
        self.routing_strategy = self._load_routing_strategy()

        # 状态跟踪
        self.last_health_check = 0
        self.circuit_breaker_states = {}
        self.provider_stats = {}

        logger.info(f"Claude Code 集成初始化完成，基础URL: {self.base_url}")

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            if not self.config_path.exists():
                logger.warning(f"配置文件不存在: {self.config_path}，使用默认配置")
                return {}

            with open(self.config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)

            integration_config = config_data.get("claude_code_integration", {})
            logger.info(f"成功加载配置文件: {self.config_path}")
            return integration_config

        except json.JSONDecodeError as e:
            logger.error(f"配置文件JSON格式错误: {e}")
            raise
        except Exception as e:
            logger.error(f"配置文件加载失败: {e}")
            return {}

    def _load_model_mapping(self) -> Dict[str, ModelConfig]:
        """加载模型映射配置"""
        model_mapping_config = self.config.get("model_mapping", {})
        model_mapping = {}

        for model_type, config in model_mapping_config.items():
            model_mapping[model_type] = ModelConfig(
                provider=config.get("provider", "deepseek-primary"),
                model=config.get("model", "deepseek-chat"),
                temperature=config.get("temperature", 0.7),
                max_tokens=config.get("max_tokens", 4000),
            )

        logger.info(f"加载了 {len(model_mapping)} 个模型映射")
        return model_mapping

    def _load_routing_strategy(self) -> RoutingStrategy:
        """加载路由策略配置"""
        routing_config = self.config.get("routing_strategy", {})
        circuit_breaker = routing_config.get("circuit_breaker", {})

        return RoutingStrategy(
            fallback_enabled=routing_config.get("fallback_enabled", True),
            health_check_interval=routing_config.get("health_check_interval", 30),
            circuit_breaker_failure_threshold=circuit_breaker.get("failure_threshold", 5),
            circuit_breaker_reset_timeout=circuit_breaker.get("reset_timeout", 300),
        )

    def check_health(self) -> bool:
        """检查服务健康状态"""
        try:
            health_url = f"{self.base_url}/health"
            response = requests.get(health_url, timeout=10)

            if response.status_code == 200:
                self.last_health_check = time.time()
                logger.debug("服务健康检查通过")
                return True
            else:
                logger.warning(f"服务健康检查失败: HTTP {response.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"服务健康检查异常: {e}")
            return False

    def get_provider_health(self, provider_name: str) -> bool:
        """检查特定提供商健康状态"""
        # 如果断路器处于打开状态且未超时，直接返回失败
        if provider_name in self.circuit_breaker_states:
            state = self.circuit_breaker_states[provider_name]
            if (
                state["state"] == "open"
                and time.time() - state["opened_at"]
                < self.routing_strategy.circuit_breaker_reset_timeout
            ):
                logger.warning(f"提供商 {provider_name} 断路器处于打开状态")
                return False

        # 简单健康检查 - 尝试一个轻量级请求
        try:
            # 这里可以添加更具体的提供商健康检查
            # 暂时返回True，假设提供商健康
            return True
        except Exception as e:
            logger.warning(f"提供商 {provider_name} 健康检查失败: {e}")
            return False

    def _update_circuit_breaker(self, provider_name: str, success: bool):
        """更新断路器状态"""
        if provider_name not in self.circuit_breaker_states:
            self.circuit_breaker_states[provider_name] = {
                "state": "closed",
                "failure_count": 0,
                "opened_at": 0,
            }

        state = self.circuit_breaker_states[provider_name]

        if success:
            # 成功调用，重置计数器
            state["failure_count"] = 0
            if state["state"] == "open":
                state["state"] = "half-open"
        else:
            # 失败调用，增加计数器
            state["failure_count"] += 1
            if state["failure_count"] >= self.routing_strategy.circuit_breaker_failure_threshold:
                state["state"] = "open"
                state["opened_at"] = time.time()
                logger.error(f"提供商 {provider_name} 断路器打开")

    def call_model(
        self, prompt: str, model_type: str = "athena_default", **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        调用模型

        Args:
            prompt: 用户提示
            model_type: 模型类型 (athena_default, athena_reasoning, athena_code, athena_background)
            **kwargs: 额外参数

        Returns:
            API响应数据或None
        """
        # 检查服务健康
        if time.time() - self.last_health_check > self.routing_strategy.health_check_interval:
            if not self.check_health():
                logger.error("服务健康检查失败，无法调用模型")
                return None

        # 获取模型配置
        if model_type not in self.model_mapping:
            logger.warning(f"未知的模型类型: {model_type}，使用默认配置")
            model_type = "athena_default"

        model_config = self.model_mapping[model_type]

        # 检查提供商健康
        if not self.get_provider_health(model_config.provider):
            if self.routing_strategy.fallback_enabled:
                logger.warning(f"提供商 {model_config.provider} 不可用，尝试备用方案")
                # 这里可以添加备用逻辑
                return None
            else:
                logger.error(f"提供商 {model_config.provider} 不可用且未启用备用策略")
                return None

        # 准备请求参数
        payload = {
            "model": model_config.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", model_config.temperature),
            "max_tokens": kwargs.get("max_tokens", model_config.max_tokens),
        }

        # 添加可选参数
        if "top_p" in kwargs:
            payload["top_p"] = kwargs["top_p"]
        if "frequency_penalty" in kwargs:
            payload["frequency_penalty"] = kwargs["frequency_penalty"]
        if "presence_penalty" in kwargs:
            payload["presence_penalty"] = kwargs["presence_penalty"]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Athena-OpenHuman/1.0.0",
        }

        # 重试逻辑
        for attempt in range(self.retry_count):
            try:
                start_time = time.time()

                response = requests.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=self.timeout,
                )

                duration = time.time() - start_time

                if response.status_code == 200:
                    result = response.json()

                    # 更新统计信息
                    self._update_provider_stats(
                        model_config.provider, success=True, duration=duration
                    )
                    self._update_circuit_breaker(model_config.provider, success=True)

                    logger.info(
                        f"模型调用成功: {model_type} -> {model_config.provider}/{model_config.model}, 耗时: {duration:.2f}秒"
                    )
                    return result

                else:
                    error_msg = f"API调用失败: HTTP {response.status_code}"
                    if response.text:
                        try:
                            error_data = response.json()
                            error_msg += f" - {error_data.get('error', {}).get('message', response.text[:200])}"
                        except:
                            error_msg += f" - {response.text[:200]}"

                    logger.warning(f"{error_msg} (尝试 {attempt + 1}/{self.retry_count})")

                    # 更新统计信息
                    self._update_provider_stats(
                        model_config.provider, success=False, duration=duration
                    )
                    self._update_circuit_breaker(model_config.provider, success=False)

                    # 如果是服务器错误，重试
                    if response.status_code >= 500:
                        if attempt < self.retry_count - 1:
                            wait_time = 2**attempt  # 指数退避
                            logger.info(f"等待 {wait_time} 秒后重试...")
                            time.sleep(wait_time)
                        continue
                    else:
                        # 客户端错误，不重试
                        break

            except requests.exceptions.Timeout:
                logger.warning(f"请求超时 (尝试 {attempt + 1}/{self.retry_count})")
                self._update_provider_stats(
                    model_config.provider, success=False, duration=self.timeout
                )
                self._update_circuit_breaker(model_config.provider, success=False)

                if attempt < self.retry_count - 1:
                    wait_time = 2**attempt
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)

            except requests.exceptions.RequestException as e:
                logger.error(f"请求异常: {e} (尝试 {attempt + 1}/{self.retry_count})")
                self._update_provider_stats(model_config.provider, success=False, duration=0)
                self._update_circuit_breaker(model_config.provider, success=False)

                if attempt < self.retry_count - 1:
                    wait_time = 2**attempt
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)

        logger.error(f"所有重试尝试均失败: {model_type}")
        return None

    def _update_provider_stats(self, provider_name: str, success: bool, duration: float):
        """更新提供商统计信息"""
        if provider_name not in self.provider_stats:
            self.provider_stats[provider_name] = {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "total_duration": 0.0,
                "avg_duration": 0.0,
            }

        stats = self.provider_stats[provider_name]
        stats["total_calls"] += 1
        stats["total_duration"] += duration

        if success:
            stats["successful_calls"] += 1
        else:
            stats["failed_calls"] += 1

        if stats["successful_calls"] > 0:
            stats["avg_duration"] = stats["total_duration"] / stats["successful_calls"]

    def get_provider_statistics(self) -> Dict[str, Any]:
        """获取提供商统计信息"""
        return self.provider_stats

    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """获取断路器状态"""
        return self.circuit_breaker_states

    def batch_call(
        self, prompts: List[str], model_type: str = "athena_default", **kwargs
    ) -> List[Optional[Dict[str, Any]]]:
        """
        批量调用模型

        Args:
            prompts: 提示列表
            model_type: 模型类型
            **kwargs: 额外参数

        Returns:
            响应列表
        """
        results = []

        for i, prompt in enumerate(prompts):
            logger.info(f"处理批量调用 {i+1}/{len(prompts)}")
            result = self.call_model(prompt, model_type, **kwargs)
            results.append(result)

            # 避免速率限制
            if i < len(prompts) - 1:
                time.sleep(0.5)

        return results


# 便捷函数
def get_integration_instance() -> ClaudeCodeIntegration:
    """获取集成实例（单例模式）"""
    if not hasattr(get_integration_instance, "_instance"):
        get_integration_instance._instance = ClaudeCodeIntegration()
    return get_integration_instance._instance


def test_connection() -> bool:
    """测试连接"""
    try:
        integration = get_integration_instance()
        return integration.check_health()
    except Exception as e:
        logger.error(f"连接测试失败: {e}")
        return False


def simple_call(prompt: str, model_type: str = "athena_default") -> Optional[str]:
    """
    简单调用函数

    Args:
        prompt: 用户提示
        model_type: 模型类型

    Returns:
        响应文本或None
    """
    try:
        integration = get_integration_instance()
        result = integration.call_model(prompt, model_type)

        if result and "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        else:
            return None

    except Exception as e:
        logger.error(f"简单调用失败: {e}")
        return None


# 主模块测试
if __name__ == "__main__":
    print("=== Claude Code 集成模块测试 ===")

    # 创建集成实例
    integration = ClaudeCodeIntegration()

    # 测试健康检查
    print("1. 健康检查...")
    if integration.check_health():
        print("   ✅ 服务健康")
    else:
        print("   ❌ 服务异常")

    # 测试模型调用
    print("\n2. 测试模型调用...")
    test_prompt = "你好，这是一个测试消息。请回复'测试成功'。"
    result = integration.call_model(test_prompt, "athena_default")

    if result:
        print("   ✅ 模型调用成功")
        response_text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        print(f"   响应: {response_text[:100]}...")
    else:
        print("   ❌ 模型调用失败")

    # 显示统计信息
    print("\n3. 提供商统计信息:")
    stats = integration.get_provider_statistics()
    for provider, stat in stats.items():
        print(f"   {provider}: {stat['successful_calls']}/{stat['total_calls']} 成功")

    print("\n=== 测试完成 ===")
