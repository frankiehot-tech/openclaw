#!/usr/bin/env python3
"""
成本估算策略模块 - 基于审计报告第二阶段优化建议

实现多层级fallback策略和增强的token估算算法。

设计特点：
1. 多层级fallback策略：API响应 → 脚本解析 → 启发式估算 → 默认值
2. 增强token估算：支持不同语言、代码、结构化数据的特殊处理
3. 模型感知估算：针对不同模型优化估算算法
4. 置信度评分：为每个估算结果提供置信度分数

分层策略：
1. 第1层（准确数据）：从API响应中提取usage信息
2. 第2层（脚本解析）：解析provider替代脚本输出，提取tokens
3. 第3层（启发式估算）：基于文本内容的高级估算算法
4. 第4层（默认估算）：回退到基本字符计数估算
"""

import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class EstimationSource(Enum):
    """估算数据来源枚举"""

    API_USAGE = "api_usage"  # API返回的准确usage数据
    SCRIPT_PARSING = "script_parsing"  # 从脚本输出中解析
    HEURISTIC_ESTIMATION = "heuristic_estimation"  # 启发式估算
    BASIC_ESTIMATION = "basic_estimation"  # 基本字符估算
    DEFAULT_VALUES = "default_values"  # 默认值回退


@dataclass
class EstimationResult:
    """估算结果数据类"""

    input_tokens: int
    output_tokens: int
    source: EstimationSource
    confidence: float  # 置信度 0.0-1.0
    notes: str = ""
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TokenEstimate:
    """Token估算详细结果"""

    text: str
    estimated_tokens: int
    confidence: float
    method: str
    language_stats: Dict[str, float] = None
    character_count: int = 0
    line_count: int = 0
    has_code: bool = False
    has_json: bool = False
    has_xml: bool = False

    def __post_init__(self):
        if self.language_stats is None:
            self.language_stats = {}
        self.character_count = len(self.text)


class EnhancedTokenEstimator:
    """增强Token估算器"""

    # 语言特定的token估算系数（字符/token）
    LANGUAGE_COEFFICIENTS = {
        "chinese": 1.5,  # 中文：约1.5字符/token
        "english": 4.0,  # 英文：约4.0字符/token
        "japanese": 2.0,  # 日文：约2.0字符/token
        "korean": 2.5,  # 韩文：约2.5字符/token
        "code": 3.0,  # 代码：约3.0字符/token（混合字符）
        "whitespace": 1.0,  # 空白字符：1字符/token
        "numbers": 3.0,  # 数字：约3.0字符/token
        "punctuation": 1.0,  # 标点符号：1字符/token
    }

    # 模型特定调整系数
    MODEL_ADJUSTMENTS = {
        # OpenAI GPT系列
        "gpt-4": {"chinese": 1.3, "english": 3.8, "code": 2.8},
        "gpt-3.5-turbo": {"chinese": 1.4, "english": 3.9, "code": 2.9},
        # DeepSeek系列
        "deepseek-chat": {"chinese": 1.4, "english": 3.9, "code": 2.8},
        "deepseek-coder": {"chinese": 1.5, "english": 4.0, "code": 2.5},
        # Qwen系列
        "qwen3.5-plus": {"chinese": 1.3, "english": 3.8, "code": 2.7},
        "qwen3-max": {"chinese": 1.3, "english": 3.8, "code": 2.7},
        # Claude系列
        "claude-3-opus": {"chinese": 1.4, "english": 3.9, "code": 2.9},
        "claude-3-sonnet": {"chinese": 1.4, "english": 3.9, "code": 2.9},
    }

    @staticmethod
    def analyze_text_language(text: str) -> Dict[str, float]:
        """分析文本的语言组成"""
        if not text:
            return {"unknown": 1.0}

        stats = {
            "chinese": 0.0,
            "english": 0.0,
            "code": 0.0,
            "numbers": 0.0,
            "whitespace": 0.0,
            "punctuation": 0.0,
            "other": 0.0,
        }

        total_chars = len(text)
        if total_chars == 0:
            return stats

        # 按字符分类
        for char in text:
            # 中文字符 (U+4E00-U+9FFF)
            if "\u4e00" <= char <= "\u9fff":
                stats["chinese"] += 1

            # 英文字符（字母和基本符号）
            elif "A" <= char <= "Z" or "a" <= char <= "z":
                stats["english"] += 1

            # 数字
            elif "0" <= char <= "9":
                stats["numbers"] += 1

            # 空白字符
            elif char in " \t\n\r":
                stats["whitespace"] += 1

            # 代码相关字符
            elif char in "{}[]()<>;:,.?!'\"`~@#$%^&*_-+=|\\/":
                stats["punctuation"] += 1

            else:
                stats["other"] += 1

        # 转换为比例
        for key in stats:
            stats[key] = stats[key] / total_chars

        # 检测代码模式
        code_patterns = [
            r"def\s+\w+\s*\(",  # Python函数定义
            r"function\s+\w+\s*\(",  # JavaScript函数定义
            r"class\s+\w+",  # 类定义
            r"import\s+",  # 导入语句
            r"console\.log",  # 控制台日志
            r"print\s*\(",  # 打印语句
            r"if\s*\(",  # 条件语句
            r"for\s*\(",  # 循环语句
            r"return\s+",  # 返回语句
            r"public\s+class",  # Java类定义
        ]

        has_code = False
        for pattern in code_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                has_code = True
                break

        # 检测JSON
        has_json = False
        text_stripped = text.strip()
        if (text_stripped.startswith("{") and text_stripped.endswith("}")) or (
            text_stripped.startswith("[") and text_stripped.endswith("]")
        ):
            try:
                json.loads(text_stripped)
                has_json = True
            except (json.JSONDecodeError, ValueError):
                pass

        # 检测XML/HTML
        has_xml = re.search(r"<\w+[^>]*>.*</\w+>", text) is not None

        # 如果检测到代码或结构化数据，调整统计
        if has_code or has_json or has_xml:
            # 代码和结构化文本通常有更多特殊字符
            stats["code"] = max(0.3, stats["code"] + 0.2)  # 增加代码比例
            stats["punctuation"] = max(0.1, stats["punctuation"] + 0.1)  # 增加标点比例

        return stats

    @classmethod
    def estimate_tokens_enhanced(cls, text: str, model_id: str = "") -> TokenEstimate:
        """
        增强的token估算算法

        Args:
            text: 输入文本
            model_id: 模型ID（用于特定模型优化）

        Returns:
            TokenEstimate对象包含详细估算信息
        """
        if not text:
            return TokenEstimate(text="", estimated_tokens=0, confidence=1.0, method="empty")

        # 分析文本
        language_stats = cls.analyze_text_language(text)

        # 应用模型特定调整
        coefficients = cls.LANGUAGE_COEFFICIENTS.copy()
        if model_id and model_id in cls.MODEL_ADJUSTMENTS:
            for lang, adjustment in cls.MODEL_ADJUSTMENTS[model_id].items():
                if lang in coefficients:
                    coefficients[lang] = adjustment

        # 计算每种语言的字符数
        total_chars = len(text)
        language_chars = {}
        for lang, proportion in language_stats.items():
            language_chars[lang] = total_chars * proportion

        # 估算tokens（加权平均）
        total_tokens = 0.0
        for lang, chars in language_chars.items():
            if chars > 0:
                # 获取该语言的系数，如果没有则使用最接近的
                if lang in coefficients:
                    coeff = coefficients[lang]
                elif lang in ["chinese", "japanese", "korean"]:
                    coeff = coefficients["chinese"]  # 使用中文系数
                elif lang in ["english", "other"]:
                    coeff = coefficients["english"]  # 使用英文系数
                else:
                    coeff = 3.0  # 默认系数

                tokens_for_lang = chars / coeff if coeff > 0 else 0
                total_tokens += tokens_for_lang

        # 确保至少1个token
        estimated_tokens = max(1, int(total_tokens + 0.5))

        # 计算置信度
        # 置信度基于：文本长度、语言多样性、模型匹配度
        confidence_factors = []

        # 1. 文本长度因子：越长越准确
        if total_chars > 1000:
            confidence_factors.append(0.9)
        elif total_chars > 100:
            confidence_factors.append(0.8)
        elif total_chars > 10:
            confidence_factors.append(0.7)
        else:
            confidence_factors.append(0.5)

        # 2. 语言识别因子：主导语言越明显越准确
        dominant_lang_prop = max(language_stats.values())
        if dominant_lang_prop > 0.8:
            confidence_factors.append(0.9)
        elif dominant_lang_prop > 0.6:
            confidence_factors.append(0.8)
        elif dominant_lang_prop > 0.4:
            confidence_factors.append(0.7)
        else:
            confidence_factors.append(0.6)

        # 3. 模型匹配因子：如果模型有特定调整，置信度更高
        if model_id and model_id in cls.MODEL_ADJUSTMENTS:
            confidence_factors.append(0.9)
        else:
            confidence_factors.append(0.7)

        # 平均置信度
        confidence = sum(confidence_factors) / len(confidence_factors)

        # 检测特殊内容
        has_code = any(
            re.search(pattern, text, re.IGNORECASE)
            for pattern in [
                r"def\s+\w+\s*\(",
                r"function\s+\w+\s*\(",
                r"class\s+\w+",
                r"import\s+",
                r"console\.log",
                r"print\s*\(",
                r"if\s*\(",
                r"for\s*\(",
                r"return\s+",
                r"public\s+class",
            ]
        )

        has_json = False
        text_stripped = text.strip()
        if (text_stripped.startswith("{") and text_stripped.endswith("}")) or (
            text_stripped.startswith("[") and text_stripped.endswith("]")
        ):
            try:
                json.loads(text_stripped)
                has_json = True
            except (json.JSONDecodeError, ValueError):
                pass

        has_xml = re.search(r"<\w+[^>]*>.*</\w+>", text) is not None

        return TokenEstimate(
            text=text,
            estimated_tokens=estimated_tokens,
            confidence=confidence,
            method="enhanced_estimation",
            language_stats=language_stats,
            character_count=total_chars,
            line_count=text.count("\n") + 1,
            has_code=has_code,
            has_json=has_json,
            has_xml=has_xml,
        )

    @classmethod
    def estimate_tokens_simple(cls, text: str) -> int:
        """
        简单token估算（向后兼容）

        Args:
            text: 输入文本

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


class ScriptOutputParser:
    """脚本输出解析器（解析provider替代脚本的输出）"""

    @staticmethod
    def extract_tokens_from_curl_response(output: str) -> Optional[Dict[str, int]]:
        """
        从curl响应中提取tokens信息

        Args:
            output: curl命令的输出

        Returns:
            包含input_tokens和output_tokens的字典，或None
        """
        try:
            # 查找JSON响应部分（通常curl输出会有HTTP状态和JSON响应）
            lines = output.split("\n")
            json_start = -1
            json_end = -1

            for i, line in enumerate(lines):
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    # 单行JSON
                    json_str = line
                    break
                elif line.startswith("{"):
                    # 多行JSON开始
                    json_start = i
                    break
            else:
                # 没有找到JSON开始
                return None

            # 如果是多行JSON
            if json_start >= 0:
                for i in range(json_start, len(lines)):
                    if lines[i].strip().endswith("}"):
                        json_end = i
                        break

                if json_end >= json_start:
                    json_str = "\n".join(lines[json_start : json_end + 1])
                else:
                    return None

            # 解析JSON
            response_data = json.loads(json_str)

            # 尝试提取usage信息
            usage = response_data.get("usage", {})
            if usage and isinstance(usage, dict):
                input_tokens = usage.get("prompt_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", 0)

                # 如果没有prompt/completion tokens，但有total_tokens
                if input_tokens == 0 and output_tokens == 0 and total_tokens > 0:
                    # 简单分配：输入30%，输出70%
                    input_tokens = int(total_tokens * 0.3)
                    output_tokens = total_tokens - input_tokens

                return {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "source": "api_response",
                }

            # 尝试从其他字段提取
            # 有些API可能返回不同的格式
            for key in ["usage_stats", "token_usage", "tokens"]:
                if key in response_data:
                    token_data = response_data[key]
                    if isinstance(token_data, dict):
                        input_tokens = token_data.get("input", token_data.get("prompt", 0))
                        output_tokens = token_data.get("output", token_data.get("completion", 0))
                        if input_tokens > 0 or output_tokens > 0:
                            return {
                                "input_tokens": input_tokens,
                                "output_tokens": output_tokens,
                                "source": key,
                            }

        except (json.JSONDecodeError, KeyError, ValueError, IndexError) as e:
            logger.debug(f"解析curl响应失败: {e}")

        return None

    @staticmethod
    def extract_tokens_from_bash_output(output: str) -> Optional[Dict[str, int]]:
        """
        从bash脚本输出中提取tokens信息

        支持格式：
        1. Provider替代脚本输出（claude-qwen-alt.sh, claude-deepseek-alt.sh等）
        2. JSON响应（如上）
        3. 自定义格式：TOKENS: input=100, output=50
        4. 统计行：Total tokens: 150 (input: 100, output: 50)

        Args:
            output: bash脚本输出

        Returns:
            包含input_tokens和output_tokens的字典，或None
        """
        # 首先尝试provider脚本解析（专门针对Claude Code替代脚本）
        provider_result = ScriptOutputParser.extract_tokens_from_provider_script(output)
        if provider_result:
            return provider_result

        # 然后尝试标准的JSON解析
        json_result = ScriptOutputParser.extract_tokens_from_curl_response(output)
        if json_result:
            return json_result

        # 尝试自定义格式
        patterns = [
            # TOKENS: input=100, output=50
            r"TOKENS:\s*input\s*=\s*(\d+),\s*output\s*=\s*(\d+)",
            r"tokens:\s*input\s*=\s*(\d+),\s*output\s*=\s*(\d+)",
            r"input[_:]?\s*(\d+)[,\s]+output[_:]?\s*(\d+)",
            # Total tokens: 150 (input: 100, output: 50)
            r"Total\s+tokens:\s*(\d+)\s*\(input:\s*(\d+),\s*output:\s*(\d+)\)",
            r"total[_:]?\s*(\d+)[,\s]*input[_:]?\s*(\d+)[,\s]*output[_:]?\s*(\d+)",
            # 简单统计
            r"prompt[_:]?\s*(\d+)[,\s]+completion[_:]?\s*(\d+)",
            r"prompt_tokens[_:]?\s*(\d+)[,\s]+completion_tokens[_:]?\s*(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) >= 2:
                    try:
                        input_tokens = int(groups[0])
                        output_tokens = int(groups[1])
                        return {
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                            "source": "pattern_match",
                        }
                    except (ValueError, IndexError):
                        continue

        return None

    @staticmethod
    def extract_tokens_from_provider_script(output: str) -> Optional[Dict[str, int]]:
        """
        从provider替代脚本输出中提取tokens信息

        支持格式：
        1. Claude Code替代脚本（claude-qwen-alt.sh, claude-deepseek-alt.sh）
        2. 清理ANSI颜色代码（转义序列）
        3. 从JSON响应中提取usage信息
        4. 从调试输出中估算tokens

        Args:
            output: provider脚本的输出

        Returns:
            包含input_tokens和output_tokens的字典，或None
        """
        if not output:
            return None

        # 清理ANSI颜色代码（转义序列）
        # ANSI转义序列模式：\x1b[...m
        import re

        cleaned_output = re.sub(r"\x1b\[[0-9;]*m", "", output)

        # 首先尝试标准的JSON解析（父类方法）
        json_result = ScriptOutputParser.extract_tokens_from_curl_response(cleaned_output)
        if json_result:
            json_result["source"] = "provider_script_json"
            return json_result

        # 尝试从调试信息中提取tokens
        # provider脚本可能在stderr中输出调试信息
        debug_patterns = [
            # 格式1: "DEBUG: Input tokens: 100, Output tokens: 50"
            r"(?:DEBUG|INFO|LOG):?\s*Input\s*tokens?:?\s*(\d+)[,\s]+Output\s*tokens?:?\s*(\d+)",
            # 格式2: "Tokens used: prompt=100, completion=50"
            r"(?:Tokens|tokens)\s*(?:used|count):?\s*prompt[=_]\s*(\d+)[,\s]+completion[=_]\s*(\d+)",
            # 格式3: "Prompt: 100 tokens, Completion: 50 tokens"
            r"Prompt:?\s*(\d+)\s*tokens[,\s]+Completion:?\s*(\d+)\s*tokens",
            # 格式4: "Input text length: 500 chars (est. 125 tokens)"
            r"Input\s*text\s*length:?\s*(\d+)\s*chars\s*\(est\.?\s*(\d+)\s*tokens\)",
            r"Output\s*text\s*length:?\s*(\d+)\s*chars\s*\(est\.?\s*(\d+)\s*tokens\)",
        ]

        for pattern in debug_patterns:
            match = re.search(pattern, cleaned_output, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) >= 2:
                    try:
                        input_tokens = int(groups[0])
                        output_tokens = int(groups[1])
                        return {
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                            "source": "provider_script_debug",
                        }
                    except (ValueError, IndexError):
                        continue

        # 尝试从脚本执行的curl响应中提取
        # provider脚本通常使用curl发送请求
        # 查找curl响应部分（通常包含HTTP状态码和JSON）
        curl_sections = re.findall(
            r"(?:HTTP/\d\.\d\s+\d+\s+\w+|curl:.*?)\s*\n(.*?)(?:\n\n|\nHTTP|$)",
            cleaned_output,
            re.DOTALL | re.IGNORECASE,
        )

        for section in curl_sections:
            # 尝试解析JSON
            json_match = re.search(r"\{.*\}", section, re.DOTALL)
            if json_match:
                try:
                    json_str = json_match.group(0)
                    data = json.loads(json_str)
                    if "usage" in data:
                        usage = data["usage"]
                        input_tokens = usage.get("prompt_tokens", 0)
                        output_tokens = usage.get("completion_tokens", 0)
                        if input_tokens > 0 or output_tokens > 0:
                            return {
                                "input_tokens": input_tokens,
                                "output_tokens": output_tokens,
                                "source": "provider_script_curl_json",
                            }
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue

        # 如果以上都失败，尝试基于文本长度估算
        # provider脚本可能在输出中包含输入/输出文本
        # 估算规则：
        # 1. 查找明显的输入和输出部分
        # 2. 使用简单token估算

        # 标记输入输出部分（常见模式）
        input_markers = ["INPUT:", "PROMPT:", "Request:", ">>>"]
        output_markers = ["OUTPUT:", "RESPONSE:", "Answer:", "<<<"]

        input_text = ""
        output_text = ""

        lines = cleaned_output.split("\n")
        current_section = None

        for line in lines:
            line_lower = line.lower()
            # 检查是否开始新部分
            if any(marker.lower() in line_lower for marker in input_markers):
                current_section = "input"
                # 移除标记
                for marker in input_markers:
                    if marker.lower() in line_lower:
                        line = line[line_lower.index(marker.lower()) + len(marker) :].strip()
                        break
            elif any(marker.lower() in line_lower for marker in output_markers):
                current_section = "output"
                for marker in output_markers:
                    if marker.lower() in line_lower:
                        line = line[line_lower.index(marker.lower()) + len(marker) :].strip()
                        break

            # 添加到相应部分
            if current_section == "input":
                input_text += line + "\n"
            elif current_section == "output":
                output_text += line + "\n"

        # 如果有足够的文本，进行估算
        if len(input_text.strip()) > 10 or len(output_text.strip()) > 10:
            from .cost_tracker_integration import TokenEstimator

            try:
                estimator = TokenEstimator()
                input_tokens = estimator.estimate_tokens(input_text) if input_text.strip() else 100
                output_tokens = (
                    estimator.estimate_tokens(output_text) if output_text.strip() else 50
                )

                return {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "source": "provider_script_text_estimation",
                    "confidence": 0.6,
                }
            except ImportError:
                # 如果无法导入TokenEstimator，使用简单估算
                chinese_chars_input = sum(1 for c in input_text if "\u4e00" <= c <= "\u9fff")
                total_chars_input = len(input_text)
                non_chinese_input = total_chars_input - chinese_chars_input
                input_tokens = max(1, int((chinese_chars_input / 1.5) + (non_chinese_input / 4.0)))

                chinese_chars_output = sum(1 for c in output_text if "\u4e00" <= c <= "\u9fff")
                total_chars_output = len(output_text)
                non_chinese_output = total_chars_output - chinese_chars_output
                output_tokens = max(
                    1, int((chinese_chars_output / 1.5) + (non_chinese_output / 4.0))
                )

                return {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "source": "provider_script_simple_estimation",
                    "confidence": 0.5,
                }

        return None


class MultiLevelEstimationStrategy:
    """多层级fallback估算策略"""

    def __init__(self):
        """初始化策略"""
        self.token_estimator = EnhancedTokenEstimator()
        self.script_parser = ScriptOutputParser()

    def estimate_from_api_response(
        self, api_response: Dict[str, Any], input_text: str = ""
    ) -> EstimationResult:
        """
        第1层：从API响应中提取准确usage信息

        Args:
            api_response: API响应字典
            input_text: 输入文本（用于fallback）

        Returns:
            EstimationResult对象
        """
        try:
            # 尝试从API响应中提取usage信息
            usage = api_response.get("usage", {})

            if usage and isinstance(usage, dict):
                input_tokens = usage.get("prompt_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", 0)

                # 如果没有prompt_tokens/completion_tokens，使用total_tokens估算
                if input_tokens == 0 and output_tokens == 0 and total_tokens > 0:
                    # 简单估算：输入占30%，输出占70%
                    input_tokens = int(total_tokens * 0.3)
                    output_tokens = total_tokens - input_tokens
                    confidence = 0.8
                    notes = "从total_tokens估算输入输出分布"
                else:
                    confidence = 0.95
                    notes = "API返回准确usage数据"

                return EstimationResult(
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    source=EstimationSource.API_USAGE,
                    confidence=confidence,
                    notes=notes,
                    metadata={"api_response_keys": list(api_response.keys())},
                )

            # 检查其他可能的字段
            for key in ["usage_stats", "token_usage", "tokens"]:
                if key in api_response:
                    token_data = api_response[key]
                    if isinstance(token_data, dict):
                        input_tokens = token_data.get("input", token_data.get("prompt", 0))
                        output_tokens = token_data.get("output", token_data.get("completion", 0))
                        if input_tokens > 0 or output_tokens > 0:
                            return EstimationResult(
                                input_tokens=input_tokens,
                                output_tokens=output_tokens,
                                source=EstimationSource.API_USAGE,
                                confidence=0.9,
                                notes=f"从{key}字段提取tokens",
                                metadata={"source_key": key},
                            )

        except Exception as e:
            logger.warning(f"从API响应提取tokens失败: {e}")

        # 如果API响应中没有usage信息，回退到脚本解析
        return self.estimate_from_script_output(str(api_response), input_text)

    def estimate_from_script_output(
        self, script_output: str, input_text: str = "", model_id: str = ""
    ) -> EstimationResult:
        """
        第2层：解析脚本输出

        Args:
            script_output: 脚本输出文本
            input_text: 输入文本（用于fallback）
            model_id: 模型ID（用于fallback）

        Returns:
            EstimationResult对象
        """
        try:
            # 尝试从脚本输出中提取tokens
            token_data = self.script_parser.extract_tokens_from_bash_output(script_output)

            if token_data:
                return EstimationResult(
                    input_tokens=token_data["input_tokens"],
                    output_tokens=token_data["output_tokens"],
                    source=EstimationSource.SCRIPT_PARSING,
                    confidence=0.85,
                    notes=f"从脚本输出解析tokens (来源: {token_data.get('source', 'unknown')})",
                    metadata=token_data,
                )

        except Exception as e:
            logger.warning(f"解析脚本输出失败: {e}")

        # 如果无法解析脚本输出，回退到启发式估算
        return self.estimate_heuristic(input_text, script_output, model_id)

    def estimate_heuristic(
        self, input_text: str, output_text: str = "", model_id: str = ""
    ) -> EstimationResult:
        """
        第3层：启发式估算

        Args:
            input_text: 输入文本
            output_text: 输出文本
            model_id: 模型ID

        Returns:
            EstimationResult对象
        """
        try:
            # 使用增强估算算法
            input_estimate = self.token_estimator.estimate_tokens_enhanced(input_text, model_id)
            output_estimate = self.token_estimator.estimate_tokens_enhanced(output_text, model_id)

            # 合并置信度
            combined_confidence = (input_estimate.confidence + output_estimate.confidence) / 2

            # 为启发式估算设置稍低的置信度
            final_confidence = combined_confidence * 0.9

            notes = f"启发式估算: 输入置信度{input_estimate.confidence:.2f}, 输出置信度{output_estimate.confidence:.2f}"

            if input_estimate.has_code or output_estimate.has_code:
                notes += " (检测到代码)"
            if input_estimate.has_json or output_estimate.has_json:
                notes += " (检测到JSON)"
            if input_estimate.has_xml or output_estimate.has_xml:
                notes += " (检测到XML/HTML)"

            return EstimationResult(
                input_tokens=input_estimate.estimated_tokens,
                output_tokens=output_estimate.estimated_tokens,
                source=EstimationSource.HEURISTIC_ESTIMATION,
                confidence=final_confidence,
                notes=notes,
                metadata={
                    "input_estimate": input_estimate.__dict__,
                    "output_estimate": output_estimate.__dict__,
                    "model_id": model_id,
                },
            )

        except Exception as e:
            logger.warning(f"启发式估算失败: {e}")

        # 如果启发式估算失败，回退到基本估算
        return self.estimate_basic(input_text, output_text)

    def estimate_basic(self, input_text: str, output_text: str = "") -> EstimationResult:
        """
        第4层：基本字符计数估算

        Args:
            input_text: 输入文本
            output_text: 输出文本

        Returns:
            EstimationResult对象
        """
        try:
            # 使用简单算法（向后兼容）
            input_tokens = EnhancedTokenEstimator.estimate_tokens_simple(input_text)
            output_tokens = EnhancedTokenEstimator.estimate_tokens_simple(output_text)

            return EstimationResult(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                source=EstimationSource.BASIC_ESTIMATION,
                confidence=0.7,
                notes="基本字符计数估算（中英文混合）",
                metadata={"input_length": len(input_text), "output_length": len(output_text)},
            )

        except Exception as e:
            logger.warning(f"基本估算失败: {e}")

        # 如果所有方法都失败，使用默认值
        return self.estimate_default()

    def estimate_default(self) -> EstimationResult:
        """
        第5层：默认值回退

        Returns:
            EstimationResult对象
        """
        return EstimationResult(
            input_tokens=100,  # 默认值
            output_tokens=50,  # 默认值
            source=EstimationSource.DEFAULT_VALUES,
            confidence=0.5,
            notes="所有估算方法失败，使用默认值",
            metadata={"warning": "fallback_to_defaults"},
        )

    def estimate(
        self,
        api_response: Optional[Dict[str, Any]] = None,
        script_output: Optional[str] = None,
        input_text: str = "",
        output_text: str = "",
        model_id: str = "",
    ) -> EstimationResult:
        """
        多层级fallback估算主函数

        按优先级尝试：
        1. API响应
        2. 脚本输出
        3. 启发式估算
        4. 基本估算
        5. 默认值

        Args:
            api_response: API响应字典
            script_output: 脚本输出文本
            input_text: 输入文本
            output_text: 输出文本
            model_id: 模型ID

        Returns:
            EstimationResult对象
        """
        # 第1层：API响应
        if api_response is not None:
            result = self.estimate_from_api_response(api_response, input_text)
            if result.source == EstimationSource.API_USAGE:
                return result

        # 第2层：脚本输出
        if script_output is not None:
            result = self.estimate_from_script_output(script_output, input_text, model_id)
            if result.source == EstimationSource.SCRIPT_PARSING:
                return result

        # 第3层：启发式估算（需要输入文本）
        if input_text:
            result = self.estimate_heuristic(input_text, output_text, model_id)
            if result.source == EstimationSource.HEURISTIC_ESTIMATION:
                return result

        # 第4层：基本估算
        if input_text or output_text:
            result = self.estimate_basic(input_text, output_text)
            if result.source == EstimationSource.BASIC_ESTIMATION:
                return result

        # 第5层：默认值
        return self.estimate_default()


# 全局实例
_multi_level_estimator_instance = None


def get_multi_level_estimator() -> MultiLevelEstimationStrategy:
    """获取全局多层级估算策略实例"""
    global _multi_level_estimator_instance
    if _multi_level_estimator_instance is None:
        _multi_level_estimator_instance = MultiLevelEstimationStrategy()
    return _multi_level_estimator_instance


class CostEstimationStrategy:
    """成本估算策略类（测试兼容性适配器）

    提供与测试文件兼容的接口，内部使用多层级估算策略。
    这个类是为了保持测试文件兼容性而创建的适配器。
    """

    def __init__(self):
        """初始化策略"""
        self.multi_level_estimator = get_multi_level_estimator()
        self.script_parser = ScriptOutputParser()
        self.token_estimator = EnhancedTokenEstimator()

    def estimate_tokens(self, text: str) -> int:
        """估算文本的token数量（简单算法）

        Args:
            text: 输入文本

        Returns:
            估算的token数量
        """
        # 使用简单算法（与测试期望兼容）
        return EnhancedTokenEstimator.estimate_tokens_simple(text)

    def extract_tokens_from_provider_script(self, output: str) -> dict:
        """从provider脚本输出中提取tokens信息

        Args:
            output: provider脚本的输出

        Returns:
            包含input_tokens和output_tokens的字典
        """
        result = self.script_parser.extract_tokens_from_provider_script(output)
        if result is None:
            # 如果解析失败，返回默认值
            return {"input_tokens": 0, "output_tokens": 0, "source": "unknown"}
        return result

    def estimate_cost_tokens(
        self,
        provider_id: str,
        model_id: str,
        api_response: dict = None,
        provider_script_output: str = None,
        fallback_text: str = "",
    ) -> dict:
        """估算成本tokens（多层级fallback）

        Args:
            provider_id: provider ID
            model_id: 模型ID
            api_response: API响应字典
            provider_script_output: provider脚本输出
            fallback_text: fallback文本（用于估算）

        Returns:
            包含input_tokens、output_tokens和source的字典
        """
        # 使用多层级估算策略
        result = self.multi_level_estimator.estimate(
            api_response=api_response,
            script_output=provider_script_output,
            input_text=fallback_text,
            output_text="",  # 只有输入文本，无输出
            model_id=model_id,
        )

        # 转换结果为测试期望的格式
        source_mapping = {
            EstimationSource.API_USAGE: "api_response",
            EstimationSource.SCRIPT_PARSING: "provider_script",
            EstimationSource.HEURISTIC_ESTIMATION: "estimation",
            EstimationSource.BASIC_ESTIMATION: "estimation",
            EstimationSource.DEFAULT_VALUES: "estimation",
        }

        return {
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "source": source_mapping.get(result.source, "unknown"),
        }


# 测试函数
def test_cost_estimation_strategy():
    """测试成本估算策略"""
    print("=== 测试成本估算策略 ===\n")

    estimator = get_multi_level_estimator()

    # 测试1：增强token估算
    print("1. 测试增强token估算:")
    test_texts = [
        ("这是一个中文测试文本。", "qwen3.5-plus"),
        ("This is an English test text.", "deepseek-chat"),
        ("这是一个混合文本。This is mixed text.", "gpt-4"),
        ("def hello():\n    print('Hello, world!')", "deepseek-coder"),
        ('{"name": "test", "value": 123}', "qwen3.5-plus"),
    ]

    for text, model in test_texts:
        estimate = EnhancedTokenEstimator.estimate_tokens_enhanced(text, model)
        print(f"   文本: '{text[:30]}...'")
        print(f"   模型: {model}, 估算tokens: {estimate.estimated_tokens}")
        print(f"   置信度: {estimate.confidence:.2f}, 字符数: {estimate.character_count}")
        print(f"   语言统计: {estimate.language_stats}")
        print()

    # 测试2：多层级估算
    print("\n2. 测试多层级估算:")

    # 模拟API响应（有usage）
    api_response_with_usage = {
        "id": "test_001",
        "choices": [{"text": "测试输出"}],
        "usage": {"prompt_tokens": 120, "completion_tokens": 45, "total_tokens": 165},
    }

    result1 = estimator.estimate(
        api_response=api_response_with_usage,
        input_text="测试输入",
        output_text="测试输出",
        model_id="qwen3.5-plus",
    )

    print(f"   API响应估算:")
    print(f"     输入tokens: {result1.input_tokens}, 输出tokens: {result1.output_tokens}")
    print(f"     来源: {result1.source.value}, 置信度: {result1.confidence:.2f}")
    print(f"     说明: {result1.notes}")
    print()

    # 模拟脚本输出（无usage，但可以解析）
    script_output = '{"text": "Hello world", "total_tokens": 50}'

    result2 = estimator.estimate(
        script_output=script_output,
        input_text="Hello",
        output_text="world",
        model_id="deepseek-chat",
    )

    print(f"   脚本输出估算:")
    print(f"     输入tokens: {result2.input_tokens}, 输出tokens: {result2.output_tokens}")
    print(f"     来源: {result2.source.value}, 置信度: {result2.confidence:.2f}")
    print(f"     说明: {result2.notes}")
    print()

    # 测试3：仅文本估算
    print("\n3. 测试仅文本估算:")

    result3 = estimator.estimate(
        input_text="这是一个较长的测试文本，用于测试启发式估算算法。",
        output_text="这是模型的输出响应。",
        model_id="gpt-4",
    )

    print(f"   仅文本估算:")
    print(f"     输入tokens: {result3.input_tokens}, 输出tokens: {result3.output_tokens}")
    print(f"     来源: {result3.source.value}, 置信度: {result3.confidence:.2f}")
    print(f"     说明: {result3.notes}")
    print()

    # 测试4：脚本解析器
    print("\n4. 测试脚本解析器:")

    test_outputs = [
        "TOKENS: input=150, output=75",
        "Total tokens: 225 (input: 150, output: 75)",
        "prompt_tokens: 150, completion_tokens: 75",
        '{"usage": {"prompt_tokens": 150, "completion_tokens": 75}}',
    ]

    for i, output in enumerate(test_outputs, 1):
        tokens = ScriptOutputParser.extract_tokens_from_bash_output(output)
        if tokens:
            print(f"   测试{i}: '{output[:30]}...'")
            print(f"     解析结果: 输入{tokens['input_tokens']}, 输出{tokens['output_tokens']}")
        else:
            print(f"   测试{i}: 无法解析")

    # 测试5：Provider脚本输出解析（新增）
    print("\n5. 测试Provider脚本输出解析:")

    provider_test_outputs = [
        # 模拟claude-qwen-alt.sh输出（包含ANSI颜色代码和JSON响应）
        '\x1b[32mINFO: Sending request to Qwen API...\x1b[0m\n{"id": "chatcmpl-123", "choices": [{"text": "Hello"}], "usage": {"prompt_tokens": 120, "completion_tokens": 45, "total_tokens": 165}}',
        # 模拟claude-deepseek-alt.sh输出（调试信息）
        "DEBUG: Input tokens: 200, Output tokens: 80\nRequest completed successfully.",
        # 模拟脚本curl响应（包含HTTP头）
        'HTTP/1.1 200 OK\nContent-Type: application/json\n\n{"usage": {"prompt_tokens": 180, "completion_tokens": 60}}',
        # 模拟包含输入输出标记的脚本输出
        "INPUT: 请解释一下量子计算。\nPROCESSING...\nOUTPUT: 量子计算是一种利用量子力学原理进行计算的新型计算模式。",
        # 模拟带颜色代码和错误信息的混合输出
        '\x1b[31mERROR: API rate limit exceeded\x1b[0m\nRetrying...\n\x1b[33mWARNING: Using fallback provider\x1b[0m\n{"text": "Response", "total_tokens": 100}',
    ]

    for i, output in enumerate(provider_test_outputs, 1):
        tokens = ScriptOutputParser.extract_tokens_from_bash_output(output)
        if tokens:
            print(f"   Provider测试{i}: 成功解析")
            print(
                f"     输入tokens: {tokens['input_tokens']}, 输出tokens: {tokens['output_tokens']}"
            )
            print(f"     来源: {tokens.get('source', 'unknown')}")
        else:
            print(f"   Provider测试{i}: 无法解析")

    print("\n✅ 成本估算策略测试完成")


if __name__ == "__main__":
    test_cost_estimation_strategy()
