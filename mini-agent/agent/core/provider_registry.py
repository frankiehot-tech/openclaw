#!/usr/bin/env python3
"""
Provider Registry - Athena Provider/Model 单一事实源
"""

import logging
import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import yaml

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CostMode(Enum):
    ACTUAL = "actual"
    ESTIMATED = "estimated"
    UNAVAILABLE = "unavailable"
    FREE = "free"


class ApprovalState(Enum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class ModelDefinition:
    """模型定义"""

    id: str
    label: str
    context_length: int
    supports_function_calling: bool
    max_tokens: int
    cost_per_1k_input: float
    cost_per_1k_output: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "context_length": self.context_length,
            "supports_function_calling": self.supports_function_calling,
            "max_tokens": self.max_tokens,
            "cost_per_1k_input": self.cost_per_1k_input,
            "cost_per_1k_output": self.cost_per_1k_output,
        }


@dataclass
class ProviderDefinition:
    """Provider 定义"""

    id: str
    label: str
    base_url: str
    auth_env_key: str
    api_mode: str
    default_model: str
    fallback_model: str
    cost_mode: str
    allowed_task_kinds: List[str]
    risk_notes: str
    models: Dict[str, ModelDefinition] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "base_url": self.base_url,
            "auth_env_key": self.auth_env_key,
            "api_mode": self.api_mode,
            "default_model": self.default_model,
            "fallback_model": self.fallback_model,
            "cost_mode": self.cost_mode,
            "allowed_task_kinds": self.allowed_task_kinds,
            "risk_notes": self.risk_notes,
            "models": {model_id: model.to_dict() for model_id, model in self.models.items()},
        }


@dataclass
class ProviderRegistryConfig:
    """Registry 配置"""

    version: str
    providers: Dict[str, ProviderDefinition]
    defaults: Dict[str, Any]
    task_kind_provider_map: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "providers": {pid: p.to_dict() for pid, p in self.providers.items()},
            "defaults": self.defaults,
            "task_kind_provider_map": self.task_kind_provider_map,
        }


class ProviderRegistry:
    """Provider Registry 单例"""

    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """加载配置文件"""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "config",
            "athena_providers.yaml",
        )

        if not os.path.exists(config_path):
            logger.warning(f"配置文件不存在: {config_path}，使用内存默认配置")
            self._config = self._create_default_config()
            return

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                raw_config = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}，使用内存默认配置")
            self._config = self._create_default_config()
            return

        # 解析 providers
        providers = {}
        for provider_id, provider_data in raw_config.get("providers", {}).items():
            models = {}
            for model_data in provider_data.get("models", []):
                model_id = model_data["id"]
                models[model_id] = ModelDefinition(
                    id=model_id,
                    label=model_data.get("label", model_id),
                    context_length=model_data.get("context_length", 32768),
                    supports_function_calling=model_data.get("supports_function_calling", False),
                    max_tokens=model_data.get("max_tokens", 4096),
                    cost_per_1k_input=model_data.get("cost_per_1k_input", 0.0),
                    cost_per_1k_output=model_data.get("cost_per_1k_output", 0.0),
                )

            provider = ProviderDefinition(
                id=provider_id,
                label=provider_data.get("label", provider_id),
                base_url=provider_data.get("base_url", ""),
                auth_env_key=provider_data.get("auth_env_key", ""),
                api_mode=provider_data.get("api_mode", "openai-compatible"),
                default_model=provider_data.get("default_model", ""),
                fallback_model=provider_data.get("fallback_model", ""),
                cost_mode=provider_data.get("cost_mode", "unknown"),
                allowed_task_kinds=provider_data.get("allowed_task_kinds", []),
                risk_notes=provider_data.get("risk_notes", ""),
                models=models,
            )
            providers[provider_id] = provider

        self._config = ProviderRegistryConfig(
            version=raw_config.get("version", "1.0"),
            providers=providers,
            defaults=raw_config.get("defaults", {}),
            task_kind_provider_map=raw_config.get("task_kind_provider_map", {}),
        )

        logger.info(f"Provider Registry 加载完成，共 {len(providers)} 个 provider")

    def _create_default_config(self) -> ProviderRegistryConfig:
        """创建内存默认配置（用于 fallback）"""
        providers = {}

        # 简单默认配置
        providers["dashscope"] = ProviderDefinition(
            id="dashscope",
            label="阿里云百炼",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            auth_env_key="DASHSCOPE_API_KEY",
            api_mode="openai-compatible",
            default_model="qwen3.5-plus",
            fallback_model="qwen3-max-2026-01-23",
            cost_mode="pay_per_token",
            allowed_task_kinds=["coding_plan", "general", "openhuman"],
            risk_notes="商用API，需监控成本",
            models={
                "qwen3.5-plus": ModelDefinition(
                    id="qwen3.5-plus",
                    label="Qwen3.5 Plus",
                    context_length=128000,
                    supports_function_calling=True,
                    max_tokens=4096,
                    cost_per_1k_input=0.008,
                    cost_per_1k_output=0.008,
                )
            },
        )

        return ProviderRegistryConfig(
            version="1.0",
            providers=providers,
            defaults={
                "primary_provider": "deepseek",  # 更新默认主provider为DeepSeek
                "primary_model": "deepseek-coder",  # 使用deepseek-coder模型
                "fallback_provider": "dashscope",  # dashscope作为fallback
                "fallback_model": "qwen3.5-plus",
                "cost_aware": True,
            },
            task_kind_provider_map={
                "coding_plan": "deepseek",  # 代码规划任务使用DeepSeek
                "general": "deepseek",  # 通用任务使用DeepSeek
            },
        )

    def get_config(self) -> ProviderRegistryConfig:
        """获取配置"""
        if self._config is None:
            logger.warning("配置未初始化，使用默认配置")
            self._config = self._create_default_config()
        return self._config

    def get_provider(self, provider_id: str) -> Optional[ProviderDefinition]:
        """获取 provider 定义"""
        return self.get_config().providers.get(provider_id)

    def get_model(self, provider_id: str, model_id: str) -> Optional[ModelDefinition]:
        """获取 model 定义"""
        provider = self.get_provider(provider_id)
        if not provider:
            return None
        return provider.models.get(model_id)

    def get_default_provider(self) -> ProviderDefinition:
        """获取默认 provider"""
        config = self.get_config()
        default_id = config.defaults.get("primary_provider", "dashscope")
        provider = self.get_provider(default_id)
        if provider:
            return provider

        # 返回第一个可用的 provider
        for pid in config.providers:
            return config.providers[pid]

        # 如果没有任何 provider（不应该发生），创建一个紧急默认 provider
        logger.error("没有可用的 provider，创建紧急默认 provider")
        emergency_provider = ProviderDefinition(
            id="emergency",
            label="紧急默认",
            base_url="",
            auth_env_key="",
            api_mode="openai-compatible",
            default_model="none",
            fallback_model="none",
            cost_mode="free",
            allowed_task_kinds=[],
            risk_notes="紧急回退",
            models={},
        )
        return emergency_provider

    def get_default_model(self, provider_id: Optional[str] = None) -> Tuple[str, str]:
        """获取默认 provider 和 model"""
        if provider_id is None:
            provider = self.get_default_provider()
            provider_id = provider.id
        else:
            provider = self.get_provider(provider_id)

        if not provider:
            # fallback
            provider = self.get_default_provider()
            provider_id = provider.id

        model_id = self.get_config().defaults.get("primary_model", provider.default_model)
        if model_id not in provider.models:
            model_id = provider.default_model

        return provider_id, model_id

    def resolve_provider_for_task(
        self, task_kind: str, request_id: Optional[str] = None
    ) -> Tuple[str, str]:
        """根据任务类型解析 provider 和 model

        Args:
            task_kind: 任务类型 (debug/testing/general等)
            request_id: 可选请求ID，用于实验分配

        Returns:
            (provider_id, model_id) 元组
        """
        # 首先检查实验分配（如果request_id提供且实验框架可用）
        if request_id:
            try:
                from .experiment_router import get_experiment_router

                router = get_experiment_router()

                # 获取默认provider/model作为fallback
                default_provider, default_model = self.get_default_model()

                # 尝试实验分配
                provider_id, model_id = router.get_provider_for_experiment(
                    task_kind, request_id, default_provider, default_model
                )

                # 如果实验分配返回了不同于默认的provider，使用实验分配
                if provider_id != default_provider or model_id != default_model:
                    logger.info(
                        f"实验分配: {task_kind} -> {provider_id}/{model_id} (请求: {request_id})"
                    )
                    return provider_id, model_id

            except ImportError:
                logger.debug("实验路由器模块未找到，跳过实验分配")
            except Exception as e:
                logger.warning(f"实验分配失败: {e}，使用默认逻辑")

        # 其次检查映射
        provider_id = self.get_config().task_kind_provider_map.get(task_kind)
        if provider_id:
            provider = self.get_provider(provider_id)
            if provider:
                return provider_id, provider.default_model

        # 默认逻辑
        return self.get_default_model()

    def get_provider_base_url(self, provider_id: str) -> str:
        """获取 provider 的 base URL"""
        provider = self.get_provider(provider_id)
        if provider:
            return provider.base_url
        return ""

    def get_auth_key(self, provider_id: str) -> str:
        """获取 provider 的认证环境变量值"""
        provider = self.get_provider(provider_id)
        if not provider or not provider.auth_env_key:
            return ""

        return os.environ.get(provider.auth_env_key, "")

    def estimate_cost(
        self, provider_id: str, model_id: str, input_tokens: int, output_tokens: int
    ) -> Dict[str, Any]:
        """估算成本"""
        model = self.get_model(provider_id, model_id)
        if not model:
            return {
                "estimated_cost": 0.0,
                "estimated_tokens": input_tokens + output_tokens,
                "cost_mode": CostMode.UNAVAILABLE.value,
                "notes": "模型未在 registry 中定义",
            }

        provider = self.get_provider(provider_id)
        cost_mode = provider.cost_mode if provider else "unknown"

        if cost_mode == "free":
            actual_cost = 0.0
            cost_mode_enum = CostMode.FREE
        else:
            input_cost = (input_tokens / 1000.0) * model.cost_per_1k_input
            output_cost = (output_tokens / 1000.0) * model.cost_per_1k_output
            actual_cost = input_cost + output_cost
            cost_mode_enum = CostMode.ESTIMATED

        return {
            "estimated_cost": round(actual_cost, 6),
            "estimated_tokens": input_tokens + output_tokens,
            "cost_mode": cost_mode_enum.value,
            "provider_id": provider_id,
            "model_id": model_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_per_1k_input": model.cost_per_1k_input,
            "cost_per_1k_output": model.cost_per_1k_output,
        }

    def check_approval_required(self, task_description: str, stage: str) -> Dict[str, Any]:
        """检查是否需要审批"""
        defaults = self.get_config().defaults
        approval_policy = defaults.get("approval_policy", {})

        # 检查高风险关键词
        high_risk_keywords = approval_policy.get("high_risk_keywords", [])
        keyword_hits = []
        for keyword in high_risk_keywords:
            if keyword in task_description:
                keyword_hits.append(keyword)

        # 检查阶段策略
        require_hitl_tasks = approval_policy.get("require_hitl_tasks", [])
        auto_approve_tasks = approval_policy.get("auto_approve_tasks", [])

        hitl_required = False
        reason = ""

        if keyword_hits:
            hitl_required = True
            reason = f"包含高风险关键词: {', '.join(keyword_hits)}"
        elif stage in require_hitl_tasks:
            hitl_required = True
            reason = f"阶段 {stage} 默认需要人工审批"
        elif stage in auto_approve_tasks:
            hitl_required = False
            reason = f"阶段 {stage} 自动批准"
        else:
            # 默认策略：低风险任务自动批准
            hitl_required = False
            reason = "低风险任务，自动批准"

        return {
            "hitl_required": hitl_required,
            "reason": reason,
            "keyword_hits": keyword_hits,
            "stage": stage,
            "approval_state": (
                ApprovalState.PENDING.value if hitl_required else ApprovalState.NOT_REQUIRED.value
            ),
        }


# 全局 registry 实例
_registry_instance: Optional[ProviderRegistry] = None


def get_registry() -> ProviderRegistry:
    """获取全局 registry 实例"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ProviderRegistry()
    return _registry_instance


if __name__ == "__main__":
    # 测试代码
    print("=== Provider Registry 测试 ===")

    registry = ProviderRegistry()
    config = registry.get_config()

    print(f"\n1. 版本: {config.version}")
    print(f"   默认 provider: {config.defaults.get('primary_provider')}")
    print(f"   默认 model: {config.defaults.get('primary_model')}")

    print("\n2. Provider 列表:")
    for provider_id, provider in config.providers.items():
        print(f"   {provider.label} ({provider_id})")
        print(f"     基础URL: {provider.base_url}")
        print(f"     默认模型: {provider.default_model}")
        print(f"     模型数: {len(provider.models)}")

    print("\n3. 默认 provider/model:")
    provider_id, model_id = registry.get_default_model()
    print(f"   Provider: {provider_id}, Model: {model_id}")

    print("\n4. 成本估算测试:")
    cost_est = registry.estimate_cost("dashscope", "qwen3.5-plus", 1000, 500)
    print(f"   1000输入 + 500输出 tokens: {cost_est}")

    print("\n5. 审批检查测试:")
    approval_check = registry.check_approval_required("测试任务", "plan")
    print(f"   低风险任务: {approval_check}")

    approval_check2 = registry.check_approval_required("删除所有数据", "build")
    print(f"   高风险任务: {approval_check2}")

    print("\n✅ Provider Registry 测试完成")
