"""
API Key 错误处理器 — 替代 fix_gene_management_all_issues.py 等 3 个脚本

故障模式:
- DASHSCOPE_API_KEY 环境变量未设置
- API Key 过期或无效
- 控制面配置缺少 api_key 字段
"""

import json
import logging
import os
from typing import Any, Dict

from ops.fault_handler.registry import (
    BaseFaultHandler,
    FaultContext,
    FaultRegistry,
    FaultSeverity,
)

logger = logging.getLogger(__name__)

REQUIRED_KEYS = [
    "DASHSCOPE_API_KEY",
    "DEEPSEEK_API_KEY",
    "AUTOGLM_API_KEY",
]


class ApiKeyErrorHandler(BaseFaultHandler):
    fault_type = "api_key_error"
    severity = FaultSeverity.CRITICAL
    max_retries = 1

    def detect(self, ctx: FaultContext) -> bool:
        missing = []
        for key in REQUIRED_KEYS:
            if not os.environ.get(key):
                missing.append(key)

        if missing:
            ctx.metadata["missing_keys"] = missing
            logger.warning(f"缺少环境变量: {missing}")
            return True

        return False

    def diagnose(self, ctx: FaultContext) -> Dict[str, Any]:
        missing = ctx.metadata.get("missing_keys", [])
        all_env_keys = {k: bool(v) for k, v in os.environ.items() if "KEY" in k or "TOKEN" in k}
        return {
            "missing_keys": missing,
            "available_key_vars": list(all_env_keys.keys()),
            "env_setup_required": True if missing else False,
        }

    def repair(self, ctx: FaultContext) -> bool:
        missing = ctx.metadata.get("missing_keys", [])
        if not missing:
            return True

        env_file = os.path.expanduser("~/.zshrc")
        instructions = []
        for key in missing:
            instructions.append(f"export {key}=<your-{key.lower()}>")
            instructions.append(f"请在 DashScope/DeepSeek 控制台获取 {key}")
            instructions.append(f"然后执行: source ~/.zshrc")

        ctx.metadata["instructions"] = instructions
        logger.warning(f"API Key 缺失，需要手动设置: {missing}")
        return False

    def verify(self, ctx: FaultContext) -> bool:
        for key in REQUIRED_KEYS:
            if not os.environ.get(key):
                return False
        return True


FaultRegistry.register(ApiKeyErrorHandler)
