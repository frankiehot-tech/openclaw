#!/usr/bin/env python3
"""
严格版提示词提取测试
专注于提取真正的AI生成提示词格式，排除README和描述性内容
"""

import json
import logging
import re
from typing import Any, Dict, List, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StrictPromptExtractor:
    """严格版提示词提取器"""

    def __init__(self):
        # 严格的关键词列表 - 必须是真正的提示词
        self.strict_prompt_patterns = [
            # 标准格式
            r'"([^"]{10,300})"',  # 引号内的文本
            r"prompt:\s*(.+)",  # prompt: 前缀
            r"text:\s*(.+)",  # text: 前缀
            r"description:\s*(.+)",  # description: 前缀
            r"input:\s*(.+)",  # input: 前缀
            # JSON格式
            r'"prompt"\s*:\s*"([^"]+)"',
            r'"text"\s*:\s*"([^"]+)"',
            r'"description"\s*:\s*"([^"]+)"',
            # 数组格式
            r'\d+\s*:\s*"([^"]+)"',  # 0: "提示词"
            r'-\s*"([^"]+)"',  # - "提示词" (YAML/列表格式)
            r'\*\s*"([^"]+)"',  # * "提示词" (Markdown列表)
        ]

        # 真正的提示词特征
        self.prompt_features = [
            "high quality",
            "detailed",
            "masterpiece",
            "professional",
            "intricate",
            "sharp focus",
            "cinematic",
            "epic",
            "beautiful",
            "stunning",
            "amazing",
            "gorgeous",
            "magnificent",
            "spectacular",
            "in the style of",
            "by artist",
            "trending on",
            "artstation",
            "unreal engine",
            "octane render",
            "vray",
            "cycles",
        ]

        # 排除的特征（非提示词）
        self.exclude_features = [
            "install",
            "usage",
            "example",
            "tutorial",
            "guide",
            "readme",
            "license",
            "changelog",
            "contributing",
            "configuration",
            "settings",
            "requirements",
            "setup",
            "function",
            "def ",
            "class ",
            "import ",
            "export ",
            "api",
            "endpoint",
            "route",
            "controller",
            "model",
        ]

        # 最小和最大长度
        self.min_length = 20
        self.max_length = 300

    def extract_strict_prompts(self, text: str) -> List[str]:
        """严格提取提示词"""
        prompts = []

        # 分割行
        lines = text.split("\n")

        for line_num, line in enumerate(lines):
            line = line.strip()
            line_lower = line.lower()

            # 长度检查
            if len(line) < self.min_length or len(line) > self.max_length:
                continue

            # 排除非提示词内容
            if any(exclude in line_lower for exclude in self.exclude_features):
                continue

            # 检查代码特征
            code_symbols = ["{", "}", ";", "=", "()", "=>", "def ", "function ", "class "]
            if any(symbol in line for symbol in code_symbols):
                continue

            # 尝试匹配各种提示词格式
            matched = False
            prompt_text = line

            # 模式匹配
            for pattern in self.strict_prompt_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    # 提取匹配的文本
                    if len(match.groups()) > 0:
                        prompt_text = match.group(1).strip()
                        if self.min_length <= len(prompt_text) <= self.max_length:
                            matched = True
                            break

            # 如果没有模式匹配，但看起来像描述性提示词
            if not matched:
                # 检查是否以描述性开头
                descriptive_starts = [
                    "a ",
                    "an ",
                    "the ",
                    "close-up of",
                    "portrait of",
                    "landscape of",
                    "image of",
                    "photo of",
                    "picture of",
                    "view of",
                    "scene of",
                ]
                starts_descriptive = any(
                    line_lower.startswith(start) for start in descriptive_starts
                )

                # 检查是否包含提示词特征
                has_prompt_features = any(feature in line_lower for feature in self.prompt_features)

                # 检查逗号数量（描述性提示词通常有多个修饰词）
                comma_count = line.count(",")

                # 单词数检查
                words = line.split()
                word_count = len(words)

                # 综合评分
                score = 0
                if starts_descriptive:
                    score += 2
                if has_prompt_features:
                    score += 2
                if comma_count >= 2:
                    score += 1
                if 10 <= word_count <= 30:
                    score += 1

                if score >= 4:  # 高阈值
                    matched = True

            if matched:
                # 清理提示词文本
                prompt_text = self._clean_prompt_text(prompt_text)
                if self._validate_prompt(prompt_text):
                    prompts.append(prompt_text)
                    logger.debug(f"提取提示词 (行{line_num}): {prompt_text[:60]}...")

        return prompts

    def _clean_prompt_text(self, text: str) -> str:
        """清理提示词文本"""
        # 去除多余空格
        text = " ".join(text.split())

        # 去除常见前缀/后缀
        prefixes = ["prompt:", "text:", "description:", "input:", "output:"]
        for prefix in prefixes:
            if text.lower().startswith(prefix):
                text = text[len(prefix) :].strip()

        # 去除开头/结尾的引号
        text = text.strip("\"'")

        return text

    def _validate_prompt(self, text: str) -> bool:
        """验证是否为真正的提示词"""
        text_lower = text.lower()

        # 长度验证
        if len(text) < self.min_length or len(text) > self.max_length:
            return False

        # 排除明显非提示词的内容
        non_prompt_indicators = [
            "http://",
            "https://",
            "www.",
            ".com",
            ".org",
            ".net",
            "browserslist",
            "not ie <=",
            "not op_mini",
            "def ",
            "function ",
            "class ",
            "import ",
            "export ",
            "install",
            "setup",
            "configuration",
            "license",
            "repository",
            "collection",
            "notebook",
            "technique",
            "transform",
            "create",
            "generate",
            "control",
            "movement",
        ]

        if any(indicator in text_lower for indicator in non_prompt_indicators):
            return False

        # 检查是否为句子（包含动词和完整句子结构）
        # 提示词通常是名词短语，不是完整句子
        sentence_indicators = [
            " is ",
            " are ",
            " was ",
            " were ",
            " has ",
            " have ",
            " do ",
            " does ",
            " can ",
            " could ",
            " will ",
            " would ",
            " should ",
            " must ",
            " may ",
            " might ",
        ]

        # 检查句子结构（主语+动词）
        if any(indicator in text_lower for indicator in sentence_indicators):
            # 可能是描述而非提示词
            return False

        # 检查是否以动词开头（通常不是提示词）
        verb_starts = [
            "create",
            "generate",
            "transform",
            "install",
            "use",
            "download",
            "configure",
            "setup",
            "run",
            "execute",
        ]
        first_word = text_lower.split()[0] if text_lower.split() else ""
        if first_word in verb_starts:
            return False

        # 单词数检查
        words = text.split()
        if len(words) < 3 or len(words) > 50:
            return False

        # 检查是否包含AI提示词常见特征
        prompt_features = [
            "quality",
            "detailed",
            "masterpiece",
            "professional",
            "intricate",
            "sharp",
            "cinematic",
            "epic",
            "beautiful",
            "stunning",
            "amazing",
            "gorgeous",
            "4k",
            "8k",
            "hd",
            "trending",
            "artstation",
            "unreal",
            "octane",
            "vray",
        ]

        if not any(feature in text_lower for feature in prompt_features):
            # 可能不是高质量的AI提示词
            # 但不要完全排除，因为简单提示词也可能有效
            pass

        # 检查是否包含描述性结构
        descriptive_structures = [
            " of ",
            " with ",
            " in ",
            " on ",
            " at ",
            " by ",
            " for ",
            " and ",
            " or ",
            " but ",
            ", ",
            " - ",
            " -- ",
        ]

        has_descriptive_structure = any(struct in text for struct in descriptive_structures)
        if not has_descriptive_structure and len(words) > 5:
            # 长文本但没有描述性结构，可能不是提示词
            return False

        return True

    def extract_from_json(self, json_content: str) -> List[str]:
        """从JSON中提取提示词"""
        try:
            data = json.loads(json_content)
            prompts = []

            def extract_from_obj(obj):
                if isinstance(obj, dict):
                    # 检查键值对
                    for key, value in obj.items():
                        key_lower = str(key).lower()
                        if (
                            "prompt" in key_lower
                            or "text" in key_lower
                            or "description" in key_lower
                        ):
                            if isinstance(value, str):
                                extracted = self.extract_strict_prompts(value)
                                prompts.extend(extracted)
                            elif isinstance(value, list):
                                for item in value:
                                    if isinstance(item, str):
                                        extracted = self.extract_strict_prompts(item)
                                        prompts.extend(extracted)
                        else:
                            extract_from_obj(value)
                elif isinstance(obj, list):
                    for item in obj:
                        extract_from_obj(item)

            extract_from_obj(data)
            return list(set(prompts))  # 去重

        except json.JSONDecodeError:
            return []


def test_extraction():
    """测试提取功能"""
    print("=== 严格版提示词提取测试 ===\n")

    extractor = StrictPromptExtractor()

    # 测试用例
    test_cases = [
        # 真正的提示词
        ('"a peaceful zen garden, detailed, 4k"', True, "引号内提示词"),
        ("prompt: A beautiful landscape with mountains and a river", True, "prompt:前缀"),
        ('0: "portrait of a warrior, intricate armor, cinematic lighting"', True, "数组格式"),
        ('{"prompt": "fantasy castle on a cliff, epic scale, dramatic clouds"}', True, "JSON格式"),
        (
            "A close-up of a beautiful flower, macro photography, detailed petals, bokeh background",
            True,
            "描述性提示词",
        ),
        # 非提示词
        ("Install the package using pip install stable-diffusion", False, "安装说明"),
        ("This repository contains examples of AI art generation", False, "仓库描述"),
        ("def generate_image(prompt):", False, "代码"),
        ("browserslist: not ie <= 11", False, "配置文件"),
        ("Readme.md - Documentation for the project", False, "文档标题"),
        # 边界案例
        ("Image of a cat", False, "太短"),
        (
            "A highly detailed masterpiece of epic fantasy landscape with intricate details, cinematic lighting, trending on artstation, by greg rutkowski",
            True,
            "详细提示词",
        ),
        ('Usage: python3 generate.py --prompt "your prompt here"', False, "使用说明"),
    ]

    print("测试用例结果:")
    print("-" * 80)

    passed = 0
    total = len(test_cases)

    for text, expected, description in test_cases:
        prompts = extractor.extract_strict_prompts(text)
        extracted = len(prompts) > 0
        status = "✅" if extracted == expected else "❌"

        if extracted:
            prompt_text = prompts[0][:50] + "..." if len(prompts[0]) > 50 else prompts[0]
            print(f"{status} {description}: '{text[:40]}...' -> 提取: {prompt_text}")
        else:
            print(
                f"{status} {description}: '{text[:40]}...' -> 提取: {extracted}, 预期: {expected}"
            )

        if extracted == expected:
            passed += 1

    print(f"\n测试通过率: {passed}/{total} ({passed/total*100:.1f}%)")

    # 测试从文件提取
    print("\n=== 测试从现有文件提取 ===")

    test_files = ["optimized_collected_prompts_v2.json", "collected_prompts_50.json"]

    for filename in test_files:
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)

            print(f"\n分析文件: {filename}")
            print(f"原始条目数: {len(data)}")

            # 提取真正的提示词
            true_prompts = []
            for item in data:
                if isinstance(item, dict) and "prompt_text" in item:
                    prompts = extractor.extract_strict_prompts(item["prompt_text"])
                    if prompts:
                        true_prompts.extend(prompts)

            print(f"真正的提示词数: {len(true_prompts)}")
            if true_prompts:
                print("前5个真正的提示词:")
                for i, prompt in enumerate(true_prompts[:5]):
                    print(f"  {i+1}. {prompt[:80]}...")
        except FileNotFoundError:
            print(f"文件不存在: {filename}")
        except Exception as e:
            print(f"处理文件 {filename} 出错: {e}")

    return passed == total


if __name__ == "__main__":
    success = test_extraction()
    if success:
        print("\n✅ 所有测试通过！")
    else:
        print("\n⚠️  部分测试失败，需要调整提取逻辑")

    # 保存提取的提示词
    extractor = StrictPromptExtractor()
    final_prompts = []

    # 从两个文件中提取
    for filename in ["optimized_collected_prompts_v2.json", "collected_prompts_50.json"]:
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)

            for item in data:
                if isinstance(item, dict) and "prompt_text" in item:
                    prompts = extractor.extract_strict_prompts(item["prompt_text"])
                    for prompt in prompts:
                        # 创建清理后的条目
                        clean_item = {
                            "prompt_text": prompt,
                            "source": item.get("source", "unknown"),
                            "quality_score": item.get("quality_score", 0.5),
                            "category": item.get("category", "text_to_image"),
                            "subcategory": item.get("subcategory", "general"),
                        }
                        final_prompts.append(clean_item)
        except Exception as e:
            print(f"处理 {filename} 时出错: {e}")

    # 保存最终结果
    if final_prompts:
        output_file = "strict_extracted_prompts.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(final_prompts, f, indent=2, ensure_ascii=False)
        print(f"\n🎯 保存 {len(final_prompts)} 个严格提取的提示词到: {output_file}")

        print("\n最终提示词示例:")
        for i, item in enumerate(final_prompts[:10]):
            print(f"  {i+1}. {item['prompt_text'][:80]}...")
            print(f"     来源: {item['source']}, 质量: {item['quality_score']:.2f}")
