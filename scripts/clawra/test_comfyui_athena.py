#!/usr/bin/env python3
"""
测试ComfyUI Athena生成器
优化存储版本测试
"""

import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

# 导入Athena生成器
from comfyui_athena_generator import ComfyUIAthenaGenerator


def test_server_connection():
    """测试服务器连接"""
    print("测试ComfyUI服务器连接...")
    generator = ComfyUIAthenaGenerator()

    if generator.check_server_status():
        print("OK: 服务器连接成功")
        return generator
    else:
        print("ERROR: 服务器连接失败")
        return None


def test_workflow_creation():
    """测试工作流创建"""
    print("测试工作流创建...")
    generator = ComfyUIAthenaGenerator()

    workflow = generator.create_athena_workflow(
        prompt="硅基共生主题的AI女神Athena,机械与生物融合的身体,发出蓝色光芒的能量核心",
        negative_prompt="低质量,模糊,变形,多余的手指",
        steps=30,
        cfg=7.0,
        width=1024,
        height=1024,
        seed=-1,
    )

    # 检查必要节点
    required_nodes = [
        "checkpoint",
        "positive",
        "negative",
        "empty_latent",
        "ksampler",
        "vae",
        "save",
    ]

    for node_key in required_nodes:
        # 查找节点ID
        found = False
        for node_id in workflow.keys():
            if node_key in node_id:
                found = True
                break

        if found:
            print(f"OK: 节点 {node_key} 存在")
        else:
            print(f"ERROR: 节点 {node_key} 缺失")
            return False

    print("OK: 工作流结构完整")
    return True


def test_image_generation():
    """测试图像生成"""
    print("测试图像生成...")

    generator = ComfyUIAthenaGenerator()

    if not generator.check_server_status():
        print("ERROR: 服务器未运行")
        return False

    # 创建简单工作流
    workflow = generator.create_athena_workflow(
        prompt="硅基共生主题的AI女神Athena,机械与生物融合的身体,简约测试",
        negative_prompt="低质量,模糊",
        steps=20,  # 减少步数以加快测试
        cfg=7.0,
        width=512,  # 小尺寸以加快测试
        height=512,
        seed=42,  # 固定种子
    )

    print("提交工作流到队列...")
    prompt_id = generator.queue_prompt(workflow)

    if not prompt_id:
        print("ERROR: 工作流提交失败")
        return False

    print(f"OK: 工作流已提交, Prompt ID: {prompt_id}")

    # 等待完成（增加超时以适应CPU推理）
    print("等待生成完成（超时: 300秒）...")
    if generator.wait_for_completion(prompt_id, timeout=300):
        print("OK: 生成完成")

        # 获取生成的图像
        images = generator.get_generated_images(prompt_id)
        if images:
            print(f"OK: 找到 {len(images)} 张图像")
            for img in images[:2]:  # 显示前两张
                print(f"  - {img.get('filename')} (节点: {img.get('node_id')})")
            return True
        else:
            print("ERROR: 未找到生成的图像")
            return False
    else:
        print("ERROR: 生成超时或失败")
        return False


def main():
    """主测试函数"""
    print("=" * 60)
    print("ComfyUI Athena生成器测试（优化存储版）")
    print("=" * 60)

    # 测试1: 服务器连接
    generator = test_server_connection()
    if not generator:
        return 1

    # 测试2: 工作流创建
    if not test_workflow_creation():
        return 1

    # 测试3: 图像生成（自动运行完整测试）
    print("\n运行图像生成测试（完整工作流验证）...")
    if test_image_generation():
        print("\n" + "=" * 60)
        print("所有测试通过！")
        print("=" * 60)
        return 0
    else:
        print("\n图像生成测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
