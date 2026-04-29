#!/usr/bin/env python3
"""
检查ComfyUI生成的Athena图像质量
"""

import os
from pathlib import Path

from PIL import Image

# 图像目录
IMAGE_DIR = Path("/Volumes/1TB-M2/openclaw/comfyui_workspace/output")


def check_image_quality(image_path):
    """检查单张图像质量"""
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            mode = img.mode
            format = img.format

            # 基本质量指标
            file_size = os.path.getsize(image_path)
            resolution = width * height

            return {
                "path": str(image_path),
                "width": width,
                "height": height,
                "resolution": resolution,
                "mode": mode,
                "format": format,
                "file_size": file_size,
                "file_size_mb": file_size / 1024 / 1024,
                "aspect_ratio": width / height if height > 0 else 0,
            }
    except Exception as e:
        return {"path": str(image_path), "error": str(e)}


def check_all_images():
    """检查所有图像"""
    print("🔍 ComfyUI Athena图像质量检查")
    print("=" * 60)

    if not IMAGE_DIR.exists():
        print(f"错误: 图像目录不存在: {IMAGE_DIR}")
        return

    image_files = list(IMAGE_DIR.glob("*.png"))
    if not image_files:
        print("未找到PNG图像文件")
        return

    print(f"找到 {len(image_files)} 张图像:")

    results = []
    for img_path in image_files:
        result = check_image_quality(img_path)
        results.append(result)

    # 打印结果
    for i, result in enumerate(results):
        print(f"\n{i+1}. {Path(result['path']).name}")
        print("-" * 40)

        if "error" in result:
            print(f"   错误: {result['error']}")
            continue

        print(f"   尺寸: {result['width']}x{result['height']} ({result['resolution']:,} 像素)")
        print(f"   宽高比: {result['aspect_ratio']:.2f}")
        print(f"   格式: {result['format']} ({result['mode']})")
        print(f"   文件大小: {result['file_size_mb']:.2f} MB")

        # 质量评估
        if result["resolution"] >= 1024 * 1024:
            print("   分辨率: ✅ 高 (≥1MP)")
        elif result["resolution"] >= 512 * 512:
            print("   分辨率: ⚠️  中 (≥0.25MP)")
        else:
            print("   分辨率: ❌ 低")

        if result["file_size_mb"] > 0.5:
            print("   文件大小: ✅ 充足")
        else:
            print("   文件大小: ⚠️  较小")

    # 汇总统计
    print("\n" + "=" * 60)
    print("📊 汇总统计:")
    valid_results = [r for r in results if "error" not in r]
    if valid_results:
        avg_width = sum(r["width"] for r in valid_results) / len(valid_results)
        avg_height = sum(r["height"] for r in valid_results) / len(valid_results)
        avg_size = sum(r["file_size_mb"] for r in valid_results) / len(valid_results)

        print(f"平均尺寸: {avg_width:.0f}x{avg_height:.0f}")
        print(f"平均文件大小: {avg_size:.2f} MB")
        print(f"总文件大小: {sum(r['file_size_mb'] for r in valid_results):.2f} MB")

    # Athena IP形象要求检查
    print("\n" + "=" * 60)
    print("🎯 Athena IP形象要求检查:")
    print("期望: 硅基共生主题的AI女神Athena,机械与生物融合的身体")
    print("      科幻漫画风格,赛博朋克,高细节")
    print("      图像应为人物肖像,非抽象图案")

    # 基于文件名简单分类
    for result in results:
        if "error" in result:
            continue

        filename = Path(result["path"]).name.lower()
        if "athena" in filename:
            print(f"\n{Path(result['path']).name}:")
            if result["width"] == result["height"]:
                print("  ✅ 方形构图 (适合头像)")
            else:
                print("  ⚠️  非方形构图")

            if result["resolution"] >= 1024 * 1024:
                print("  ✅ 高分辨率 (适合印刷/展示)")
            else:
                print("  ⚠️  分辨率较低")

            # 检查图像内容无法通过程序完成
            print("  ℹ️  内容需人工验证")


if __name__ == "__main__":
    check_all_images()
