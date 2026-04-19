#!/usr/bin/env python3
"""
演示版提示词收集器
用于测试MVP阶段的提示词收集功能，不依赖GitHub API
"""

import json
import os
import random
import sys
from datetime import datetime
from typing import Any, Dict, List

# 添加路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from prompt_knowledge_base import (
    PromptCategory,
    PromptEntry,
    PromptMetadata,
    PromptSource,
    PromptSubcategory,
    QualityLevel,
)


def generate_sample_prompts(count: int = 50) -> List[PromptEntry]:
    """生成示例提示词"""

    # 提示词模板
    prompt_templates = [
        # 风景类
        {
            "template": "A breathtaking {scene} at {time_of_day}, {lighting}, {style}, {detail}",
            "scenes": [
                "mountain landscape",
                "ocean view",
                "forest path",
                "desert sunset",
                "city skyline",
            ],
            "times": ["sunrise", "midday", "sunset", "night", "golden hour"],
            "lightings": [
                "soft lighting",
                "dramatic lighting",
                "cinematic lighting",
                "natural lighting",
            ],
            "styles": [
                "photorealistic",
                "impressionist",
                "anime style",
                "oil painting",
                "digital art",
            ],
            "details": [
                "8k resolution",
                "highly detailed",
                "intricate textures",
                "professional photography",
            ],
        },
        # 肖像类
        {
            "template": "{description} portrait of a {person} with {features}, {style}, {detail}",
            "descriptions": ["Professional", "Artistic", "Character", "Fantasy", "Historical"],
            "persons": ["young woman", "old man", "warrior", "scientist", "elf", "cyborg"],
            "features": [
                "intricate facial features",
                "expressive eyes",
                "detailed clothing",
                "unique hairstyle",
            ],
            "styles": [
                "photorealistic",
                "anime",
                "concept art",
                "Renaissance painting",
                "comic book style",
            ],
            "details": [
                "shallow depth of field",
                "studio lighting",
                "high contrast",
                "cinematic composition",
            ],
        },
        # 产品类
        {
            "template": "{product} product photography, {setting}, {lighting}, {style}, {detail}",
            "products": ["smartphone", "watch", "car", "furniture", "cosmetic", "food"],
            "settings": [
                "studio setting",
                "lifestyle context",
                "minimalist background",
                "natural environment",
            ],
            "lightings": [
                "professional lighting",
                "softbox lighting",
                "natural light",
                "dramatic shadows",
            ],
            "styles": ["commercial photography", "advertisement style", "editorial", "minimalist"],
            "details": [
                "high-end product shot",
                "clean composition",
                "focus on details",
                "brand aesthetic",
            ],
        },
    ]

    # 模型兼容性
    models = ["stable-diffusion", "midjourney", "dall-e-3", "leonardo.ai", "playground-ai"]

    prompts = []

    for i in range(count):
        # 选择模板
        template_data = random.choice(prompt_templates)

        # 生成提示词文本（使用get方法避免KeyError）
        prompt_text = template_data["template"].format(
            scene=random.choice(template_data.get("scenes", [""])),
            time_of_day=random.choice(template_data.get("times", [""])),
            lighting=random.choice(template_data.get("lightings", [""])),
            style=random.choice(template_data.get("styles", [""])),
            detail=random.choice(template_data.get("details", [""])),
            description=random.choice(template_data.get("descriptions", [""])),
            person=random.choice(template_data.get("persons", [""])),
            features=random.choice(template_data.get("features", [""])),
            product=random.choice(template_data.get("products", [""])),
            setting=random.choice(template_data.get("settings", [""])),
        )

        # 确定类别
        if (
            "landscape" in prompt_text.lower()
            or "mountain" in prompt_text.lower()
            or "forest" in prompt_text.lower()
        ):
            category = PromptCategory.TEXT_TO_IMAGE
            subcategory = PromptSubcategory.LANDSCAPE
            tags = ["landscape", "nature", "scenery"]
        elif "portrait" in prompt_text.lower() or "person" in prompt_text.lower():
            category = PromptCategory.TEXT_TO_IMAGE
            subcategory = PromptSubcategory.PORTRAIT
            tags = ["portrait", "person", "character"]
        elif "product" in prompt_text.lower():
            category = PromptCategory.TEXT_TO_IMAGE
            subcategory = PromptSubcategory.PRODUCT
            tags = ["product", "commercial", "photography"]
        else:
            category = PromptCategory.TEXT_TO_IMAGE
            subcategory = PromptSubcategory.GENERAL
            tags = ["general", "art"]

        # 生成质量评分（基于提示词长度和细节）
        base_score = 0.5
        length_bonus = min(len(prompt_text.split()) / 50, 0.3)  # 最多0.3分，基于单词数
        detail_bonus = (
            0.2
            if any(
                word in prompt_text.lower()
                for word in ["detailed", "intricate", "high resolution", "professional"]
            )
            else 0
        )
        quality_score = min(
            base_score + length_bonus + detail_bonus + random.uniform(-0.1, 0.1), 1.0
        )

        # 创建提示词条目
        prompt = PromptEntry(
            id=f"demo-{i:03d}",
            category=category,
            subcategory=subcategory,
            prompt_text=prompt_text,
            parameters={
                "model": random.choice(models),
                "steps": random.randint(20, 50),
                "cfg_scale": round(random.uniform(5.0, 9.0), 1),
                "size": random.choice(["512x512", "768x768", "1024x1024", "1024x768"]),
            },
            model_compatibility=random.sample(models, random.randint(1, 3)),
            base_quality_score=round(quality_score, 2),
            quality_level=QualityLevel.UNRATED,
            source=PromptSource.GENERATED,
            source_url="",
            examples=[
                {
                    "description": f"Sample output {i}",
                    "quality_rating": round(random.uniform(3.5, 5.0), 1),
                }
            ],
            references=[],
            metadata=PromptMetadata(
                tags=set(
                    tags + [random.choice(["photorealistic", "artistic", "detailed", "cinematic"])]
                ),
                usage_count=random.randint(0, 20),
                success_count=random.randint(0, 15),
                avg_quality_score=round(random.uniform(0.6, 0.95), 2),
                last_used=datetime.now() if random.random() > 0.5 else None,
            ),
        )

        prompts.append(prompt)

    return prompts


def save_to_json(prompts: List[PromptEntry], output_path: str):
    """保存提示词到JSON文件"""
    # 转换为字典列表
    data = []
    for prompt in prompts:
        prompt_dict = prompt.to_dict()
        # 确保datetime对象被序列化
        for key, value in prompt_dict.items():
            if isinstance(value, datetime):
                prompt_dict[key] = value.isoformat()
            elif isinstance(value, dict):
                for subkey, subvalue in value.items():
                    if isinstance(subvalue, datetime):
                        prompt_dict[key][subkey] = subvalue.isoformat()
        data.append(prompt_dict)

    # 保存到文件
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ 已保存 {len(prompts)} 个示例提示词到: {output_path}")

    # 输出统计信息
    print(f"\n=== 统计信息 ===")
    print(f"总提示词数: {len(prompts)}")

    # 按类别统计
    categories = {}
    for prompt in prompts:
        cat_name = prompt.category.value
        categories[cat_name] = categories.get(cat_name, 0) + 1

    print("\n按类别统计:")
    for category, count in categories.items():
        print(f"  {category}: {count}")

    # 按子类别统计
    subcategories = {}
    for prompt in prompts:
        subcat_name = prompt.subcategory.value
        subcategories[subcat_name] = subcategories.get(subcat_name, 0) + 1

    print("\n按子类别统计:")
    for subcategory, count in subcategories.items():
        print(f"  {subcategory}: {count}")

    # 质量分布
    quality_dist = {"优秀 (>0.8)": 0, "良好 (0.6-0.8)": 0, "一般 (<0.6)": 0}
    for prompt in prompts:
        if prompt.base_quality_score > 0.8:
            quality_dist["优秀 (>0.8)"] += 1
        elif prompt.base_quality_score > 0.6:
            quality_dist["良好 (0.6-0.8)"] += 1
        else:
            quality_dist["一般 (<0.6)"] += 1

    print("\n质量分布:")
    for level, count in quality_dist.items():
        print(f"  {level}: {count}")


def test_knowledge_base_integration():
    """测试与知识库的集成"""
    print("\n=== 知识库集成测试 ===")

    import tempfile

    from prompt_knowledge_base import PromptKnowledgeBase

    # 使用临时数据库
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # 初始化知识库
        kb = PromptKnowledgeBase(db_path=db_path)
        print("✅ 知识库初始化成功")

        # 生成示例提示词
        sample_prompts = generate_sample_prompts(20)
        print(f"✅ 生成 {len(sample_prompts)} 个示例提示词")

        # 添加到知识库
        added_count = 0
        for prompt in sample_prompts:
            if kb.add_prompt(prompt):
                added_count += 1

        print(f"✅ 成功添加 {added_count} 个提示词到知识库")

        # 测试检索
        landscape_prompts = kb.search_prompts(
            category=PromptCategory.TEXT_TO_IMAGE, subcategory=PromptSubcategory.LANDSCAPE
        )
        print(f"✅ 检索到 {len(landscape_prompts)} 个风景类提示词")

        # 测试推荐
        recommendations = kb.get_recommended_prompts(category=PromptCategory.TEXT_TO_IMAGE, count=5)
        print(f"✅ 生成 {len(recommendations)} 个推荐提示词")

        # 显示推荐示例
        print("\n推荐示例:")
        for i, prompt in enumerate(recommendations[:3], 1):
            print(f"{i}. {prompt.prompt_text[:80]}... (质量: {prompt.base_quality_score})")

        return True

    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # 清理
        if os.path.exists(db_path):
            os.unlink(db_path)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="演示版提示词收集器")
    parser.add_argument("--count", type=int, default=50, help="生成的提示词数量")
    parser.add_argument("--output", default="demo_prompts.json", help="输出文件路径")
    parser.add_argument("--test-integration", action="store_true", help="测试知识库集成")

    args = parser.parse_args()

    print("=== 演示版提示词收集器 ===")

    # 生成示例提示词
    print(f"生成 {args.count} 个示例提示词...")
    prompts = generate_sample_prompts(args.count)

    # 保存到JSON
    save_to_json(prompts, args.output)

    # 测试集成
    if args.test_integration:
        test_knowledge_base_integration()

    print(f"\n🎉 演示完成！")
    print(f"提示词文件: {args.output}")
    print(
        f"使用命令测试知识库: python3 -c \"from prompt_knowledge_base import PromptKnowledgeBase; kb = PromptKnowledgeBase('demo.db'); kb.import_from_json('{args.output}')\""
    )


if __name__ == "__main__":
    main()
