#!/usr/bin/env python3
"""
成本跟踪集成模块 - 用于OpenCode包装器集成

为OpenCode包装器提供成本跟踪功能，包括：
1. 估算tokens使用量（当无法获取准确usage时）
2. 调用CostTracker记录成本
3. 解析provider替代脚本的输出
"""

import json
import logging
import os
import re
import sys
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 导入现有组件
from .cost_tracker import CostTracker, get_cost_tracker
from .provider_registry import get_registry

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TokenEstimator:
    """Token估算器"""

    @staticmethod
    def estimate_tokens(text: str, model_id: str = "") -> int:
        """
        估算文本的token数量

        使用启发式方法：
        1. 对于英文：~4个字符/1个token
        2. 对于中文：~2个字符/1个token
        3. 混合文本：根据中英文比例加权

        Args:
            text: 输入文本
            model_id: 模型ID（可选，用于特定模型优化）

        Returns:
            估算的token数量
        """
        if not text:
            return 0

        # 统计中文字符
        chinese_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        total_chars = len(text)
        non_chinese_chars = total_chars - chinese_chars

        # 中文token估算：约1.5个字符/1个token
        # 英文token估算：约4个字符/1个token
        estimated_tokens = (chinese_chars / 1.5) + (non_chinese_chars / 4.0)

        # 向上取整，确保至少1个token
        return max(1, int(estimated_tokens + 0.5))

    @staticmethod
    def estimate_tokens_for_prompt(prompt: str) -> Tuple[int, int]:
        """
        估算OpenCode提示的tokens

        OpenCode提示通常包含：
        1. 系统提示
        2. 用户消息
        3. 可能的格式标记

        Args:
            prompt: OpenCode提示

        Returns:
            (system_tokens, user_tokens) 元组
        """
        if not prompt:
            return 0, 0

        # 简化：假设提示的25%是系统提示，75%是用户消息
        # 在实际中，OpenCode提示有复杂结构，但这是合理的估算
        total_tokens = TokenEstimator.estimate_tokens(prompt)

        system_tokens = int(total_tokens * 0.25)
        user_tokens = total_tokens - system_tokens

        return system_tokens, user_tokens


class CostTrackingIntegration:
    """成本跟踪集成"""

    def __init__(self):
        """初始化成本跟踪集成"""
        self.cost_tracker = get_cost_tracker()
        self.registry = get_registry()

    def record_provider_request(
        self,
        provider_id: str,
        model_id: str,
        task_kind: Optional[str],
        input_text: str,
        output_text: str,
        request_id: Optional[str] = None,
        estimated_tokens: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        记录provider请求成本

        Args:
            provider_id: provider ID
            model_id: 模型ID
            task_kind: 任务类型
            input_text: 输入文本
            output_text: 输出文本
            request_id: 请求ID（可选）
            estimated_tokens: tokens是否为估算值
            metadata: 额外元数据

        Returns:
            记录ID，如果失败返回空字符串
        """
        try:
            # 估算tokens
            input_tokens = TokenEstimator.estimate_tokens(input_text, model_id)
            output_tokens = TokenEstimator.estimate_tokens(output_text, model_id)

            logger.info(
                f"估算tokens: {input_tokens}输入 + {output_tokens}输出 "
                f"(输入长度: {len(input_text)}, 输出长度: {len(output_text)})"
            )

            # 记录成本
            record_id = self.cost_tracker.record_request(
                request_id=request_id,
                provider_id=provider_id,
                model_id=model_id,
                task_kind=task_kind,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                estimated_tokens=estimated_tokens,
                metadata=metadata,
            )

            if record_id:
                logger.info(
                    f"成本记录成功: {provider_id}/{model_id} - "
                    f"{input_tokens}+{output_tokens} tokens"
                )
            else:
                logger.warning(f"成本记录失败")

            return record_id

        except Exception as e:
            logger.error(f"记录provider请求成本失败: {e}")
            return ""

    def record_from_api_response(
        self,
        provider_id: str,
        model_id: str,
        task_kind: Optional[str],
        input_text: str,
        api_response: Dict[str, Any],
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        从API响应记录成本（当响应包含usage字段时）

        Args:
            provider_id: provider ID
            model_id: 模型ID
            task_kind: 任务类型
            input_text: 输入文本
            api_response: API响应（JSON格式）
            request_id: 请求ID（可选）
            metadata: 额外元数据

        Returns:
            记录ID，如果失败返回空字符串
        """
        try:
            # 尝试从API响应中提取usage信息
            usage = api_response.get("usage", {})

            if usage and isinstance(usage, dict):
                # 有准确的usage信息
                input_tokens = usage.get("prompt_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", 0)

                # 如果没有prompt_tokens/completion_tokens，使用total_tokens估算
                if input_tokens == 0 and output_tokens == 0 and total_tokens > 0:
                    # 简单估算：假设输入占30%，输出占70%
                    input_tokens = int(total_tokens * 0.3)
                    output_tokens = total_tokens - input_tokens

                estimated_tokens = False  # 这是准确数据

                logger.info(f"API返回准确tokens: {input_tokens}输入 + {output_tokens}输出")

            else:
                # 没有usage信息，使用估算
                # 从响应中提取输出文本
                output_text = ""
                if "choices" in api_response and api_response["choices"]:
                    choice = api_response["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        output_text = choice["message"]["content"]
                    elif "text" in choice:
                        output_text = choice["text"]

                return self.record_provider_request(
                    provider_id=provider_id,
                    model_id=model_id,
                    task_kind=task_kind,
                    input_text=input_text,
                    output_text=output_text,
                    request_id=request_id,
                    estimated_tokens=True,
                    metadata=metadata,
                )

            # 记录成本
            record_id = self.cost_tracker.record_request(
                request_id=request_id,
                provider_id=provider_id,
                model_id=model_id,
                task_kind=task_kind,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                estimated_tokens=estimated_tokens,
                metadata=metadata,
            )

            if record_id:
                logger.info(
                    f"成本记录成功（API准确数据）: {provider_id}/{model_id} - "
                    f"{input_tokens}+{output_tokens} tokens"
                )
            else:
                logger.warning(f"成本记录失败")

            return record_id

        except Exception as e:
            logger.error(f"从API响应记录成本失败: {e}")
            return ""

    def record_opencode_execution(
        self,
        provider_id: str,
        model_id: str,
        task_kind: Optional[str],
        opencode_args: list,
        stdout: str,
        stderr: str,
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        记录OpenCode执行成本

        Args:
            provider_id: provider ID
            model_id: 模型ID
            task_kind: 任务类型
            opencode_args: OpenCode参数列表
            stdout: 标准输出
            stderr: 标准错误
            request_id: 请求ID（可选）
            metadata: 额外元数据

        Returns:
            记录ID，如果失败返回空字符串
        """
        try:
            # 从参数中提取输入文本
            input_text = self._extract_input_from_opencode_args(opencode_args)

            # 输出文本是stdout
            output_text = stdout

            # 估算tokens
            input_tokens = TokenEstimator.estimate_tokens(input_text, model_id)
            output_tokens = TokenEstimator.estimate_tokens(output_text, model_id)

            logger.info(
                f"OpenCode执行估算tokens: {input_tokens}输入 + {output_tokens}输出 "
                f"(输入长度: {len(input_text)}, 输出长度: {len(output_text)})"
            )

            # 添加OpenCode特定元数据
            if metadata is None:
                metadata = {}

            metadata.update(
                {
                    "opencode_args": opencode_args,
                    "stderr_length": len(stderr),
                    "recorded_at": datetime.now().isoformat(),
                }
            )

            # 记录成本
            record_id = self.cost_tracker.record_request(
                request_id=request_id,
                provider_id=provider_id,
                model_id=model_id,
                task_kind=task_kind,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                estimated_tokens=True,
                metadata=metadata,
            )

            if record_id:
                logger.info(
                    f"OpenCode成本记录成功: {provider_id}/{model_id} - "
                    f"{input_tokens}+{output_tokens} tokens"
                )
            else:
                logger.warning(f"OpenCode成本记录失败")

            return record_id

        except Exception as e:
            logger.error(f"记录OpenCode执行成本失败: {e}")
            return ""

    def _extract_input_from_opencode_args(self, args: list) -> str:
        """从OpenCode参数中提取输入文本"""
        if not args:
            return ""

        # OpenCode参数格式通常为：["run", "--model", "model_name", "prompt_text"]
        # 或者使用provider替代脚本时：["script_path", "-m", "model_name", "prompt_text"]

        # 查找非选项参数（不以-开头的参数）
        non_option_args = []
        i = 0
        while i < len(args):
            arg = args[i]
            if arg.startswith("-"):
                # 跳过选项和它的值
                i += 2 if i + 1 < len(args) else 1
            else:
                non_option_args.append(arg)
                i += 1

        # 最后一个非选项参数通常是提示文本
        if non_option_args:
            # 排除脚本路径（第一个参数）
            if len(non_option_args) > 1:
                return non_option_args[-1]
            elif len(non_option_args) == 1:
                # 检查第一个参数是否是脚本路径
                if args and args[0] == non_option_args[0] and os.path.exists(non_option_args[0]):
                    return ""  # 这是脚本路径，不是提示
                else:
                    return non_option_args[0]

        return ""

    def generate_request_id(self) -> str:
        """生成请求ID"""
        import uuid

        return f"req_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


# 全局实例
_cost_tracking_integration_instance = None


def get_cost_tracking_integration() -> CostTrackingIntegration:
    """获取全局成本跟踪集成实例"""
    global _cost_tracking_integration_instance
    if _cost_tracking_integration_instance is None:
        _cost_tracking_integration_instance = CostTrackingIntegration()
    return _cost_tracking_integration_instance


# 简化接口函数
def record_request_simple(
    provider_id: str, model_id: str, task_kind: Optional[str], input_text: str, output_text: str
) -> bool:
    """
    简化接口：记录请求成本

    Args:
        provider_id: provider ID
        model_id: 模型ID
        task_kind: 任务类型
        input_text: 输入文本
        output_text: 输出文本

    Returns:
        是否成功
    """
    integration = get_cost_tracking_integration()
    record_id = integration.record_provider_request(
        provider_id=provider_id,
        model_id=model_id,
        task_kind=task_kind,
        input_text=input_text,
        output_text=output_text,
    )
    return bool(record_id)


if __name__ == "__main__":
    # 测试代码
    integration = get_cost_tracking_integration()

    # 测试token估算
    test_text = "这是一个测试文本。This is a test text."
    tokens = TokenEstimator.estimate_tokens(test_text)
    print(f"测试文本: '{test_text}'")
    print(f"估算tokens: {tokens}")

    # 测试成本记录
    record_id = integration.record_provider_request(
        provider_id="dashscope",
        model_id="qwen3.5-plus",
        task_kind="testing",
        input_text="测试输入",
        output_text="测试输出",
    )

    print(f"记录ID: {record_id}")
