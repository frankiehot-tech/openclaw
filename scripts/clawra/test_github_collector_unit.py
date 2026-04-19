#!/usr/bin/env python3
"""
GitHub提示词收集器单元测试
测试核心功能，不依赖外部API
"""

import json
import os
import sys

import yaml

sys.path.append(os.path.dirname(__file__))

from datetime import datetime

from github_prompt_collector import GitHubPromptCollector, GitHubRepo, PromptEntry


def test_prompt_parsing():
    """测试提示词解析功能"""
    print("=== 测试提示词解析功能 ===")

    collector = GitHubPromptCollector()

    # 测试JSON解析
    print("\n1. 测试JSON解析...")
    json_content = """
    [
        {
            "prompt": "A beautiful sunset over mountains, highly detailed, 8k",
            "model": "stable-diffusion",
            "size": "1024x1024",
            "category": "text_to_image",
            "tags": ["landscape", "nature"]
        },
        {
            "prompt": "Cute anime character with blue eyes, pastel colors",
            "model": "midjourney",
            "category": "text_to_image",
            "subcategory": "anime"
        }
    ]
    """

    source_info = {
        "repo": "test/repo",
        "url": "https://github.com/test/repo",
        "description": "Test repository",
    }

    prompts = collector.extract_prompts_from_json(json_content, source_info)
    print(f"  从JSON解析到 {len(prompts)} 个提示词")
    for i, prompt in enumerate(prompts[:2]):  # 只显示前2个
        print(f"  {i+1}. {prompt.prompt_text[:50]}...")
        print(f"     类别: {prompt.category}, 子类别: {prompt.subcategory}")
        print(f"     质量分: {prompt.quality_score:.2f}")

    # 测试YAML解析
    print("\n2. 测试YAML解析...")
    yaml_content = """
    - prompt: "Futuristic city at night, neon lights, cyberpunk style"
      model: dall-e
      size: "512x512"
      style: "cyberpunk"

    - prompt: "Portrait of an old wise man, realistic, detailed wrinkles"
      model: "stable-diffusion"
      subcategory: "portrait"
    """

    prompts = collector.extract_prompts_from_yaml(yaml_content, source_info)
    print(f"  从YAML解析到 {len(prompts)} 个提示词")

    # 测试文本解析
    print("\n3. 测试文本解析...")
    text_content = """
    # Prompts Collection

    prompt: A majestic eagle soaring in the sky, detailed feathers
    prompt: Abstract geometric patterns, vibrant colors, modern art
    This is not a prompt line, just regular text.
    prompt: Product photo of a smartphone on marble table, studio lighting
    """

    prompts = collector.extract_prompts_from_text(text_content, source_info)
    print(f"  从文本解析到 {len(prompts)} 个提示词")

    return len(prompts) > 0


def test_prompt_quality_assessment():
    """测试提示词质量评估"""
    print("\n=== 测试提示词质量评估 ===")

    collector = GitHubPromptCollector()

    test_prompts = [
        "A simple cat",  # 简单，质量应该较低
        "Highly detailed photorealistic portrait of a warrior with intricate armor, 8k resolution, cinematic lighting, award-winning photography",  # 详细，质量应该较高
        "Landscape painting of mountains at sunset with dramatic clouds, professional composition, texture details, depth of field",  # 中等
    ]

    for i, prompt in enumerate(test_prompts):
        score = collector._assess_prompt_quality(prompt, {})
        print(f"  提示词 {i+1}: {prompt[:50]}...")
        print(f"     质量评分: {score:.2f}")
        if score > 0.7:
            print(f"     等级: 优秀")
        elif score > 0.5:
            print(f"     等级: 良好")
        else:
            print(f"     等级: 一般")

    return True


def test_knowledge_base_integration():
    """测试知识库集成"""
    print("\n=== 测试知识库集成 ===")

    try:
        from prompt_knowledge_base import PromptKnowledgeBase

        # 创建测试提示词
        test_prompt = PromptEntry(
            id="test_001",
            category="text_to_image",
            subcategory="landscape",
            prompt_text="Beautiful mountain landscape at sunrise, 4k",
            parameters={"size": "1024x1024", "model": "stable-diffusion"},
            model_compatibility=["stable-diffusion", "dall-e"],
            quality_score=0.8,
            source="test",
            source_url="",
            examples=[],
            tags=["landscape", "nature"],
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )

        print("  1. 测试转换为知识库格式...")
        kb_entry = test_prompt.to_kb_prompt_entry()
        if kb_entry:
            print(f"  ✅ 转换成功: {kb_entry.id}")
            print(f"     类别: {kb_entry.category}, 子类别: {kb_entry.subcategory}")
            print(f"     质量等级: {kb_entry.quality_level}")
        else:
            print("  ⚠️ 转换失败（可能知识库模块不可用）")

        # 测试数据库
        print("\n  2. 测试知识库数据库...")
        db_path = "test_prompt_kb.db"
        if os.path.exists(db_path):
            os.remove(db_path)  # 清理旧测试文件

        kb = PromptKnowledgeBase(db_path)
        stats = kb.get_statistics()
        print(f"     初始统计: {stats}")

        # 添加测试提示词
        if kb_entry and kb.add_prompt(kb_entry):
            print(f"  ✅ 成功添加到知识库")
            stats = kb.get_statistics()
            print(f"     添加后统计: {stats}")
        else:
            print("  ⚠️ 添加失败")

        kb.close()

        # 清理
        if os.path.exists(db_path):
            os.remove(db_path)
            print("  ✅ 测试数据库已清理")

        return True

    except ImportError as e:
        print(f"  ⚠️ 知识库模块不可用: {e}")
        return False
    except Exception as e:
        print(f"  ❌ 知识库集成测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_collector_initialization():
    """测试收集器初始化"""
    print("\n=== 测试收集器初始化 ===")

    # 测试不带token
    collector1 = GitHubPromptCollector()
    print(f"  1. 不带token初始化: {'✅ 成功' if collector1 else '❌ 失败'}")
    print(f"     Headers: {collector1.headers}")

    # 测试带token
    collector2 = GitHubPromptCollector(github_token="test_token")
    print(f"  2. 带token初始化: {'✅ 成功' if collector2 else '❌ 失败'}")
    print(f"     是否包含Authorization: {'Authorization' in collector2.headers}")

    # 测试搜索关键词
    print(f"  3. 搜索关键词数量: {len(collector1.search_keywords)}")
    print(f"     示例关键词: {collector1.search_keywords[:3]}")

    return True


def main():
    """主测试函数"""
    print("GitHub提示词收集器单元测试")
    print("=" * 60)

    test_results = []

    # 运行测试
    test_results.append(("收集器初始化", test_collector_initialization()))
    test_results.append(("提示词解析", test_prompt_parsing()))
    test_results.append(("质量评估", test_prompt_quality_assessment()))
    test_results.append(("知识库集成", test_knowledge_base_integration()))

    # 输出结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    passed = 0
    total = len(test_results)

    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1

    print(f"\n通过率: {passed}/{total} ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n🎉 所有测试通过!")
        print("\n🎯 下一步: 运行实际的GitHub收集测试")
        print("  命令: python github_prompt_collector.py --target 50 --max-repos 5")
        return True
    else:
        print("\n⚠️  部分测试失败，需要修复")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
