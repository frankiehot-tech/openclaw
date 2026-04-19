#!/usr/bin/env python3
"""合并所有提示词文件，去除重复项"""

import glob
import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Dict, List, Set


@dataclass
class PromptEntry:
    """提示词条目"""

    id: str
    category: str
    subcategory: str
    prompt_text: str
    parameters: Dict[str, str]
    model_compatibility: List[str]
    quality_score: float
    source: str
    examples: List[Dict]


def get_prompt_hash(prompt_text: str) -> str:
    """计算提示词文本的哈希值"""
    return hashlib.md5(prompt_text.strip().encode("utf-8")).hexdigest()


def load_prompts_from_file(file_path: str) -> List[PromptEntry]:
    """从文件加载提示词"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        prompts = []
        for item in data:
            # 适配不同的数据结构
            if isinstance(item, dict):
                try:
                    # 兼容不同字段名
                    prompt_text = item.get("prompt_text", "") or item.get("prompt", "")
                    category = item.get("category", "unknown") or item.get("type", "unknown")

                    if not prompt_text:
                        continue  # 跳过没有提示词文本的条目

                    prompt = PromptEntry(
                        id=item.get("id", ""),
                        category=category,
                        subcategory=item.get("subcategory", "general"),
                        prompt_text=prompt_text,
                        parameters=item.get("parameters", {}),
                        model_compatibility=item.get("model_compatibility", []),
                        quality_score=item.get("quality_score", 0.5),
                        source=item.get("source", file_path),
                        examples=item.get("examples", []),
                    )
                    prompts.append(prompt)
                except Exception as e:
                    print(f"解析提示词条目失败 (文件: {file_path}): {e}")
                    continue

        return prompts
    except Exception as e:
        print(f"读取文件 {file_path} 失败: {e}")
        return []


def merge_and_deduplicate_prompts(prompt_files: List[str]) -> List[Dict]:
    """合并并去重提示词"""
    all_prompts = []
    seen_hashes = set()

    print(f"处理 {len(prompt_files)} 个文件...")

    for file_path in prompt_files:
        prompts = load_prompts_from_file(file_path)
        print(f"  {file_path}: {len(prompts)} 个提示词")

        for prompt in prompts:
            # 计算哈希值检查重复
            prompt_hash = get_prompt_hash(prompt.prompt_text)

            if prompt_hash in seen_hashes:
                continue  # 跳过重复

            seen_hashes.add(prompt_hash)

            # 转换为字典格式
            prompt_dict = asdict(prompt)
            all_prompts.append(prompt_dict)

    print(f"\n去重后总计: {len(all_prompts)} 个唯一提示词")
    return all_prompts


def main():
    """主函数"""
    # 查找所有提示词文件
    prompt_files = glob.glob("*prompts.json")

    print("=== 发现提示词文件 ===")
    for file in prompt_files:
        print(f"  {file}")

    # 合并去重
    merged_prompts = merge_and_deduplicate_prompts(prompt_files)

    # 保存合并结果
    output_file = "merged_prompts.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(merged_prompts, f, indent=2, ensure_ascii=False)

    print(f"\n✅ 合并完成！保存到: {output_file}")

    # 类别统计
    categories = {}
    for prompt in merged_prompts:
        cat = prompt.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1

    print("\n=== 类别统计 ===")
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        print(f"  {cat}: {count} 个")

    return merged_prompts


if __name__ == "__main__":
    main()
