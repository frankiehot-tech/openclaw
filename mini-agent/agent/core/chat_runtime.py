#!/usr/bin/env python3
"""
Chat Runtime - 聊天运行时统一封装

提供单一事实源：
1. 统一封装聊天主 provider 选择
2. 统一封装 fallback 选择
3. 统一封装 status probe / degraded reason
4. 提供给 athena_bridge.py 调用的最小清晰接口

状态对象至少包含：
- chat_state
- chat_backend
- chat_selected_model
- chat_reason
- chat_primary
- chat_fallback
"""

import json
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ChatState(Enum):
    """聊天状态枚举"""

    OK = "ok"
    FALLBACK_ONLY = "fallback_only"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class ChatRuntimeConfig:
    """Chat Runtime 配置"""

    version: str
    primary: Dict[str, str]  # provider_id, model_id
    fallback: Dict[str, str]  # provider_id, model_id
    timeout: int  # 毫秒
    probe_cache_ttl: int  # 毫秒
    degraded_reason: str
    status: str


@dataclass
class ChatRuntimeStatus:
    """聊天运行时状态对象"""

    chat_state: str  # ChatState 值
    chat_backend: str  # 当前使用的 provider_id
    chat_selected_model: str  # 当前使用的 model_id
    chat_reason: str  # 状态原因
    chat_primary: Dict[str, str]  # 主 provider/model
    chat_fallback: Dict[str, str]  # 备用 provider/model
    last_probe_time: float = 0.0
    probe_cache: Dict[str, Any] = field(default_factory=dict)


class ChatRuntime:
    """Chat Runtime 单例"""

    _instance = None
    _config = None
    _status = None
    _registry = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
            cls._instance._load_registry()
            cls._instance._initialize_status()
        return cls._instance

    def _load_config(self):
        """加载 chat_runtime.json 配置"""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "config",
            "chat_runtime.json",
        )

        if not os.path.exists(config_path):
            logger.warning(f"chat_runtime.json 不存在: {config_path}，使用内存默认配置")
            self._config = self._create_default_config()
            return

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                raw_config = json.load(f)
        except Exception as e:
            logger.error(f"加载 chat_runtime.json 失败: {e}，使用内存默认配置")
            self._config = self._create_default_config()
            return

        self._config = ChatRuntimeConfig(
            version=raw_config.get("version", "1.0"),
            primary=raw_config.get(
                "primary", {"provider_id": "dashscope", "model_id": "qwen3.5-plus"}
            ),
            fallback=raw_config.get(
                "fallback", {"provider_id": "ollama_local", "model_id": "qwen2.5:3b"}
            ),
            timeout=raw_config.get("timeout", 30000),
            probe_cache_ttl=raw_config.get("probe_cache_ttl", 60000),
            degraded_reason=raw_config.get("degraded_reason", ""),
            status=raw_config.get("status", "healthy"),
        )
        logger.info(
            f"Chat Runtime 配置加载完成: primary={self._config.primary}, fallback={self._config.fallback}"
        )

    def _create_default_config(self) -> ChatRuntimeConfig:
        """创建内存默认配置"""
        return ChatRuntimeConfig(
            version="1.0",
            primary={"provider_id": "dashscope", "model_id": "qwen3.5-plus"},
            fallback={"provider_id": "ollama_local", "model_id": "qwen2.5:3b"},
            timeout=30000,
            probe_cache_ttl=60000,
            degraded_reason="",
            status="healthy",
        )

    def _load_registry(self):
        """加载 provider registry"""
        try:
            from .provider_registry import get_registry

            self._registry = get_registry()
            logger.info("Provider Registry 加载成功")
        except ImportError as e:
            logger.warning(f"无法导入 provider_registry: {e}")
            self._registry = None

    def _initialize_status(self):
        """初始化状态对象"""
        self._status = ChatRuntimeStatus(
            chat_state=ChatState.UNKNOWN.value,
            chat_backend=self._config.primary["provider_id"],
            chat_selected_model=self._config.primary["model_id"],
            chat_reason="初始状态",
            chat_primary=self._config.primary,
            chat_fallback=self._config.fallback,
            last_probe_time=0.0,
            probe_cache={},
        )

    def get_config(self) -> ChatRuntimeConfig:
        """获取配置"""
        return self._config

    def get_status(self) -> ChatRuntimeStatus:
        """获取当前状态对象"""
        return self._status

    def get_chat_state(self) -> Dict[str, Any]:
        """获取聊天状态（最小清晰接口）"""
        status = self._status
        return {
            "chat_state": status.chat_state,
            "chat_backend": status.chat_backend,
            "chat_selected_model": status.chat_selected_model,
            "chat_reason": status.chat_reason,
            "chat_primary": status.chat_primary,
            "chat_fallback": status.chat_fallback,
            "timestamp": time.time(),
        }

    def select_provider_for_task(
        self, task_kind: str = "general", domain: str = "engineering"
    ) -> Tuple[str, str]:
        """
        根据任务类型和领域选择 provider 和 model

        Args:
            task_kind: 任务类型 (coding_plan, general, openhuman, distillation, long_context, debug)
            domain: 领域 (engineering, openhuman)

        Returns:
            (provider_id, model_id)
        """
        # 如果有 registry，使用其映射逻辑
        if self._registry:
            try:
                # 如果 domain 是 openhuman，任务类型设为 openhuman
                if domain == "openhuman":
                    task_kind = "openhuman"
                elif task_kind == "general" and domain == "engineering":
                    # 默认逻辑
                    pass

                provider_id, model_id = self._registry.resolve_provider_for_task(task_kind)
                logger.info(
                    f"Registry 选择 provider: {provider_id}, model: {model_id} for task_kind={task_kind}, domain={domain}"
                )

                # 更新状态
                self._update_selection(
                    provider_id,
                    model_id,
                    f"registry selection for {task_kind}/{domain}",
                )
                return provider_id, model_id
            except Exception as e:
                logger.warning(f"Registry 选择失败: {e}，使用配置默认值")

        # 降级到配置默认值
        provider_id = self._config.primary["provider_id"]
        model_id = self._config.primary["model_id"]
        self._update_selection(provider_id, model_id, "fallback to config primary")
        return provider_id, model_id

    def get_fallback(self) -> Tuple[str, str]:
        """获取 fallback provider 和 model"""
        fallback = self._config.fallback
        return fallback["provider_id"], fallback["model_id"]

    def probe_status(self, force: bool = False) -> Dict[str, Any]:
        """
        探测 provider 状态

        Args:
            force: 强制探测，忽略缓存

        Returns:
            探测结果
        """
        current_time = time.time()
        cache_ttl = self._config.probe_cache_ttl / 1000.0  # 毫秒转秒

        # 检查缓存
        if (
            not force
            and self._status.last_probe_time > 0
            and (current_time - self._status.last_probe_time) < cache_ttl
        ):
            logger.debug(f"使用缓存的探测结果，缓存TTL: {cache_ttl}s")
            return self._status.probe_cache

        # 执行实际探测
        probe_result = self._perform_probe()

        # 更新缓存
        self._status.last_probe_time = current_time
        self._status.probe_cache = probe_result

        # 更新状态
        self._update_state_from_probe(probe_result)

        return probe_result

    def _perform_probe(self) -> Dict[str, Any]:
        """执行实际探测"""
        # 简化探测：检查环境变量和网络连通性
        primary_provider = self._config.primary["provider_id"]
        fallback_provider = self._config.fallback["provider_id"]

        probe_results = {
            "timestamp": time.time(),
            "primary": self._probe_provider(primary_provider),
            "fallback": self._probe_provider(fallback_provider),
            "overall": "healthy",
            "degraded_reason": "",
        }

        # 确定整体状态
        primary_healthy = probe_results["primary"]["healthy"]
        fallback_healthy = probe_results["fallback"]["healthy"]

        if not primary_healthy and not fallback_healthy:
            probe_results["overall"] = "unavailable"
            probe_results["degraded_reason"] = "所有 provider 不可用"
        elif not primary_healthy:
            probe_results["overall"] = "degraded"
            probe_results["degraded_reason"] = (
                f"主 provider {primary_provider} 不可用，已降级到 {fallback_provider}"
            )
        else:
            probe_results["overall"] = "healthy"

        return probe_results

    def _probe_provider(self, provider_id: str) -> Dict[str, Any]:
        """探测单个 provider"""
        # 简化探测：检查环境变量和基本连通性
        if not self._registry:
            return {
                "provider_id": provider_id,
                "healthy": False,
                "reason": "registry 未加载",
                "env_key_missing": True,
            }

        provider = self._registry.get_provider(provider_id)
        if not provider:
            return {
                "provider_id": provider_id,
                "healthy": False,
                "reason": "provider 未在 registry 中定义",
                "env_key_missing": True,
            }

        # 检查环境变量
        env_key = provider.auth_env_key
        env_missing = False
        if env_key:
            env_value = os.environ.get(env_key)
            if not env_value:
                env_missing = True

        # 简化健康检查：如果环境变量缺失，则认为不健康
        healthy = not env_missing

        return {
            "provider_id": provider_id,
            "healthy": healthy,
            "reason": "环境变量缺失" if env_missing else "基本可用",
            "env_key_missing": env_missing,
            "has_auth_key": bool(env_key),
            "base_url": provider.base_url,
        }

    def _update_state_from_probe(self, probe_result: Dict[str, Any]):
        """根据探测结果更新状态"""
        overall = probe_result.get("overall", "unknown")
        degraded_reason = probe_result.get("degraded_reason", "")

        # 更新 chat_state
        if overall == "healthy":
            self._status.chat_state = ChatState.OK.value
        elif overall == "degraded":
            self._status.chat_state = ChatState.FALLBACK_ONLY.value
        elif overall == "unavailable":
            self._status.chat_state = ChatState.DEGRADED.value
        else:
            self._status.chat_state = ChatState.UNKNOWN.value

        # 更新 chat_reason
        self._status.chat_reason = degraded_reason or f"状态: {overall}"

        # 如果主 provider 不健康，切换到备用
        primary_healthy = probe_result["primary"]["healthy"]
        if not primary_healthy and overall != "unavailable":
            fallback_provider = self._config.fallback["provider_id"]
            fallback_model = self._config.fallback["model_id"]
            self._update_selection(
                fallback_provider,
                fallback_model,
                "primary unhealthy, switched to fallback",
            )

    def _update_selection(self, provider_id: str, model_id: str, reason: str):
        """更新当前选择的 provider/model"""
        self._status.chat_backend = provider_id
        self._status.chat_selected_model = model_id
        self._status.chat_reason = reason
        logger.info(f"Chat selection updated: {provider_id}/{model_id}, reason: {reason}")

    def is_degraded(self) -> bool:
        """是否处于降级状态"""
        return self._status.chat_state == ChatState.DEGRADED.value

    def get_primary(self) -> Tuple[str, str]:
        """获取主 provider/model"""
        primary = self._config.primary
        return primary["provider_id"], primary["model_id"]


# 全局 runtime 实例
_runtime_instance: Optional[ChatRuntime] = None


def get_runtime() -> ChatRuntime:
    """获取全局 chat runtime 实例"""
    global _runtime_instance
    if _runtime_instance is None:
        _runtime_instance = ChatRuntime()
    return _runtime_instance


if __name__ == "__main__":
    # 测试代码
    print("=== Chat Runtime 测试 ===")

    runtime = ChatRuntime()
    config = runtime.get_config()

    print(f"\n1. 配置:")
    print(f"   版本: {config.version}")
    print(f"   主 provider: {config.primary}")
    print(f"   备用 provider: {config.fallback}")
    print(f"   超时: {config.timeout}ms")

    print("\n2. 当前状态:")
    state = runtime.get_chat_state()
    for key, value in state.items():
        if key != "timestamp":
            print(f"   {key}: {value}")

    print("\n3. 任务选择测试:")
    test_cases = [
        ("coding_plan", "engineering"),
        ("general", "engineering"),
        ("openhuman", "openhuman"),
        ("debug", "engineering"),
    ]

    for task_kind, domain in test_cases:
        provider, model = runtime.select_provider_for_task(task_kind, domain)
        print(f"   {task_kind}/{domain} -> {provider}/{model}")

    print("\n4. Fallback 测试:")
    fallback_provider, fallback_model = runtime.get_fallback()
    print(f"   fallback: {fallback_provider}/{fallback_model}")

    print("\n5. 状态探测测试:")
    probe_result = runtime.probe_status(force=True)
    print(f"   整体状态: {probe_result['overall']}")
    print(f"   主 provider 健康: {probe_result['primary']['healthy']}")
    print(f"   备用 provider 健康: {probe_result['fallback']['healthy']}")

    print("\n6. 更新后状态:")
    state = runtime.get_chat_state()
    for key, value in state.items():
        if key != "timestamp":
            print(f"   {key}: {value}")

    print("\n✅ Chat Runtime 测试完成")
