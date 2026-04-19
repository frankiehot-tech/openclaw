#!/usr/bin/env python3
"""
生成完整版Athena图像测试
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from comfyui_athena_generator import ComfyUIAthenaGenerator


def main():
    print("🎨 生成完整版Athena图像测试")
    print("=" * 60)

    generator = ComfyUIAthenaGenerator()

    if not generator.check_server_status():
        print("[ERROR] ComfyUI服务器未运行")
        return 1

    # Athena IP形象完整提示词
    athena_prompt = (
        "硅基共生主题的AI女神Athena,机械与生物融合的身体,"
        "发出蓝色光芒的能量核心,半透明的硅晶体皮肤,"
        "未来科技感,赛博朋克风格,精致的机械细节,"
        "发光电路纹理,生物机械共生体,"
        "美丽而强大的女性形象,银色和蓝色配色,"
        "动态光效,科幻漫画风格,高细节,大师级作品"
    )

    print(f"提示词: {athena_prompt[:100]}...")

    # 生成"未来"变体
    result = generator.generate_athena_image(
        variant_name="未来-硅基共生",
        prompt=athena_prompt,
        output_dir="/Volumes/1TB-M2/openclaw/comfyui_workspace/output",
    )

    if result:
        print("\n[OK] Athena图像生成成功!")
        print(f"   图像路径: {result.image_path}")
        print(f"   Prompt ID: {result.prompt_id}")
        print(f"   变体名称: {result.metadata['variant_name']}")
        print(f"   生成时间: {result.metadata['generated_at']}")
        return 0
    else:
        print("\n[ERROR] 图像生成失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
