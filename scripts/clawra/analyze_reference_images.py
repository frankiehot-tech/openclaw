#!/usr/bin/env python3
"""
分析Athena参考图像
分析Gemini生成的5张Athena参考图像
"""

import os
import sys
from pathlib import Path

from PIL import Image, ImageStat

# 图像目录
IMAGE_DIR = Path("/Volumes/1TB-M2/openclaw/comfyui_workspace/output")


def analyze_image_color(image_path):
    """分析图像颜色特征"""
    try:
        with Image.open(image_path) as img:
            # 转换为RGB（如果是RGBA）
            if img.mode != "RGB":
                img = img.convert("RGB")

            # 计算图像统计
            stat = ImageStat.Stat(img)

            # 平均颜色
            mean_color = tuple(int(c) for c in stat.mean)

            # 颜色标准差（颜色变化程度）
            std_color = tuple(int(c) for c in stat.stddev) if hasattr(stat, "stddev") else (0, 0, 0)

            # 提取颜色直方图（简化版）
            colors = img.getcolors(maxcolors=256 * 256)
            if colors:
                # 按频率排序
                colors_sorted = sorted(colors, key=lambda x: x[0], reverse=True)
                dominant_color = colors_sorted[0][1] if len(colors_sorted[0]) > 1 else (0, 0, 0)
            else:
                dominant_color = (0, 0, 0)

            # 亮度分析（转换为灰度）
            gray = img.convert("L")
            gray_stat = ImageStat.Stat(gray)
            brightness = gray_stat.mean[0]  # 0-255

            return {
                "mean_color": mean_color,
                "std_color": std_color,
                "dominant_color": dominant_color,
                "brightness": brightness,
                "brightness_level": (
                    "亮" if brightness > 180 else "中等" if brightness > 100 else "暗"
                ),
            }
    except Exception as e:
        return {"error": str(e)}


def analyze_image_composition(image_path):
    """分析图像构图"""
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            aspect_ratio = width / height if height > 0 else 0

            # 构图类型判断
            if abs(aspect_ratio - 1.0) < 0.1:
                composition = "方形"
            elif aspect_ratio > 1.2:
                composition = "横向"
            elif aspect_ratio < 0.8:
                composition = "纵向"
            else:
                composition = "近方形"

            # 检查是否可能包含人物（基于宽高比和尺寸的简单启发式）
            # 人物肖像通常是纵向或方形
            is_portrait_likely = composition in ["纵向", "方形", "近方形"] and height > width * 0.8

            return {
                "width": width,
                "height": height,
                "aspect_ratio": aspect_ratio,
                "composition": composition,
                "is_portrait_likely": is_portrait_likely,
            }
    except Exception as e:
        return {"error": str(e)}


def check_athena_theme_indicators(image_path):
    """检查Athena主题的视觉指示器"""
    try:
        with Image.open(image_path) as img:
            # 转换为RGB进行分析
            if img.mode != "RGB":
                img = img.convert("RGB")

            # 简单颜色特征检测
            # Athena主题：银色、蓝色、科技感、发光效果
            # 这里进行简单的颜色分布分析
            pixels = list(img.getdata())
            total_pixels = len(pixels)

            if total_pixels == 0:
                return {"error": "无像素数据"}

            # 分析蓝色和银色系像素
            blue_count = 0
            silver_gray_count = 0
            bright_count = 0

            for r, g, b in pixels[:10000]:  # 抽样分析前10000像素
                # 蓝色检测 (B值高，R和G值相对低)
                if b > r + 20 and b > g + 20:
                    blue_count += 1

                # 银色/灰色检测 (RGB值接近)
                if abs(r - g) < 20 and abs(g - b) < 20 and abs(r - b) < 20:
                    silver_gray_count += 1

                # 高亮度像素（可能代表发光效果）
                if r > 200 or g > 200 or b > 200:
                    bright_count += 1

            blue_ratio = blue_count / min(10000, total_pixels)
            silver_ratio = silver_gray_count / min(10000, total_pixels)
            bright_ratio = bright_count / min(10000, total_pixels)

            # Athena主题匹配度
            athena_score = 0
            athena_notes = []

            if blue_ratio > 0.1:
                athena_score += 2
                athena_notes.append("蓝色元素较多")
            if silver_ratio > 0.2:
                athena_score += 2
                athena_notes.append("银色/灰色调")
            if bright_ratio > 0.15:
                athena_score += 1
                athena_notes.append("高光/发光效果")

            return {
                "blue_ratio": blue_ratio,
                "silver_ratio": silver_ratio,
                "bright_ratio": bright_ratio,
                "athena_score": athena_score,
                "athena_notes": athena_notes,
                "athena_theme_likely": athena_score >= 3,
            }
    except Exception as e:
        return {"error": str(e)}


def main():
    print("🔍 Athena参考图像分析")
    print("=" * 70)

    if not IMAGE_DIR.exists():
        print(f"错误: 图像目录不存在: {IMAGE_DIR}")
        return

    # 查找Gemini生成的参考图像
    gemini_patterns = [
        "Gemini_Generated_Image_*.png",
        "gemini_*.png",
        "*reference*.png",
        "*athena_ref*.png",
    ]
    gemini_images = []

    for pattern in gemini_patterns:
        gemini_images.extend(IMAGE_DIR.glob(pattern))

    # 去重
    gemini_images = list(set(gemini_images))

    if not gemini_images:
        print("未找到Gemini参考图像，检查所有PNG文件...")
        all_images = list(IMAGE_DIR.glob("*.png"))
        print(f"目录中所有PNG文件: {[p.name for p in all_images[:10]]}")

        # 假设用户指的是最近添加的5个文件
        # 按修改时间排序
        all_images.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        gemini_images = all_images[:5]

    print(f"分析 {len(gemini_images)} 张参考图像:")
    for img_path in gemini_images:
        print(f"  - {img_path.name}")

    print("\n" + "=" * 70)

    # 分析每张图像
    all_results = []
    for i, img_path in enumerate(gemini_images):
        print(f"\n{i+1}. {img_path.name}")
        print("-" * 40)

        # 文件信息
        file_size_mb = os.path.getsize(img_path) / 1024 / 1024
        print(f"   文件大小: {file_size_mb:.2f} MB")

        # 构图分析
        comp_result = analyze_image_composition(img_path)
        if "error" in comp_result:
            print(f"   构图分析错误: {comp_result['error']}")
            continue

        print(f"   尺寸: {comp_result['width']}x{comp_result['height']}")
        print(f"   宽高比: {comp_result['aspect_ratio']:.2f} ({comp_result['composition']})")
        print(f"   可能包含人物: {'是' if comp_result['is_portrait_likely'] else '否'}")

        # 颜色分析
        color_result = analyze_image_color(img_path)
        if "error" in color_result:
            print(f"   颜色分析错误: {color_result['error']}")
        else:
            print(f"   平均颜色: RGB{color_result['mean_color']}")
            print(f"   主色调: RGB{color_result['dominant_color']}")
            print(f"   亮度: {color_result['brightness']:.0f} ({color_result['brightness_level']})")

        # Athena主题分析
        theme_result = check_athena_theme_indicators(img_path)
        if "error" in theme_result:
            print(f"   主题分析错误: {theme_result['error']}")
        else:
            print(f"   蓝色比例: {theme_result['blue_ratio']:.2%}")
            print(f"   银色比例: {theme_result['silver_ratio']:.2%}")
            print(f"   高光比例: {theme_result['bright_ratio']:.2%}")
            print(f"   Athena主题分数: {theme_result['athena_score']}/5")

            if theme_result["athena_notes"]:
                print(f"   主题特征: {', '.join(theme_result['athena_notes'])}")

            if theme_result["athena_theme_likely"]:
                print("   ✅ 可能符合Athena主题")
            else:
                print("   ⚠️  Athena主题特征不明显")

        # 保存结果
        all_results.append(
            {
                "file": img_path.name,
                "comp_result": comp_result,
                "color_result": color_result,
                "theme_result": theme_result,
                "file_size_mb": file_size_mb,
            }
        )

    # 汇总报告
    print("\n" + "=" * 70)
    print("📊 参考图像汇总报告")
    print("=" * 70)

    if not all_results:
        print("无有效分析结果")
        return

    # 统计Athena主题匹配
    athena_matches = sum(
        1
        for r in all_results
        if "theme_result" in r
        and not isinstance(r["theme_result"], dict)
        and r["theme_result"].get("athena_theme_likely", False)
    )

    print(f"Athena主题匹配: {athena_matches}/{len(all_results)} 张")

    # 平均文件大小
    avg_size = sum(r["file_size_mb"] for r in all_results) / len(all_results)
    print(f"平均文件大小: {avg_size:.2f} MB")

    # 尺寸分布
    sizes = set(
        f"{r['comp_result']['width']}x{r['comp_result']['height']}"
        for r in all_results
        if "comp_result" in r
    )
    print(f"尺寸分布: {', '.join(sizes)}")

    # 构图类型统计
    comp_types = {}
    for r in all_results:
        if "comp_result" in r:
            comp_type = r["comp_result"]["composition"]
            comp_types[comp_type] = comp_types.get(comp_type, 0) + 1

    print(f"构图类型: {', '.join(f'{k}:{v}' for k, v in comp_types.items())}")

    # IP形象建设建议
    print("\n" + "=" * 70)
    print("💡 Athena IP形象建设建议")
    print("=" * 70)

    # 基于分析结果给出建议
    high_res_images = [
        r
        for r in all_results
        if r["comp_result"]["width"] >= 1024 or r["comp_result"]["height"] >= 1024
    ]

    if len(high_res_images) >= 3:
        print("✅ 高分辨率图像充足，适合印刷和展示")
    else:
        print("⚠️  高分辨率图像不足，建议补充1024x1024以上图像")

    if athena_matches >= 3:
        print("✅ Athena主题一致性较好")
    else:
        print("⚠️  Athena主题特征不明显，需强化蓝色、银色、科技感元素")

    # 检查是否有明显的人物肖像
    portrait_images = [r for r in all_results if r["comp_result"].get("is_portrait_likely", False)]

    if len(portrait_images) >= 3:
        print("✅ 人物肖像图像充足")
    else:
        print("⚠️  人物肖像图像不足，需要更多正面/半身像")

    # 技术建议
    print("\n技术建议:")
    print("1. 使用ComfyUI生成时，参考这些图像的色彩和构图")
    print("2. 建立Athena色彩规范: 蓝色系为主，银色/灰色为辅")
    print("3. 确保生成图像包含科技感元素（发光电路、机械细节）")
    print("4. 保持方形或纵向构图，便于多种应用场景")
    print("5. 文件大小建议: 1-2MB (1024x1024 PNG)")

    # 后续步骤
    print("\n后续步骤:")
    print("1. 选择2-3张最佳参考图作为ComfyUI生成的标准")
    print("2. 创建Athena风格LoRA或Embedding进行风格迁移")
    print("3. 建立质量评估标准（颜色、构图、主题匹配度）")
    print("4. 集成到Clawra生产系统进行批量生成")


if __name__ == "__main__":
    main()
