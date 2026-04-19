#!/usr/bin/env python3
"""
生成Athena图像画廊HTML页面
显示下载的图像和资产信息
"""

import base64
import html
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))


def load_assets():
    """加载资产数据"""
    assets_file = Path(__file__).parent / "data" / "athena_assets" / "athena_assets.json"

    if not assets_file.exists():
        print(f"❌ 资产文件不存在: {assets_file}")
        return []

    try:
        with open(assets_file, "r", encoding="utf-8") as f:
            assets = json.load(f)

        print(f"📂 加载 {len(assets)} 个资产")
        return assets
    except Exception as e:
        print(f"❌ 加载资产失败: {e}")
        return []


def get_image_files():
    """获取已下载的图像文件"""
    images_dir = Path(__file__).parent / "data" / "athena_assets" / "images"

    if not images_dir.exists():
        print(f"❌ 图像目录不存在: {images_dir}")
        return []

    image_files = (
        list(images_dir.glob("*.jpg"))
        + list(images_dir.glob("*.jpeg"))
        + list(images_dir.glob("*.png"))
        + list(images_dir.glob("*.webp"))
    )

    print(f"📷 找到 {len(image_files)} 个图像文件")
    return image_files


def create_html_gallery(assets, image_files):
    """创建HTML画廊页面"""
    # 读取资产摘要
    summary_file = Path(__file__).parent / "data" / "athena_assets" / "athena_assets_summary.md"
    summary_content = ""
    if summary_file.exists():
        try:
            with open(summary_file, "r", encoding="utf-8") as f:
                summary_content = f.read()
        except:
            summary_content = "无法读取摘要文件"

    # 开始生成HTML
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Athena IP形象图像画廊</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f7;
        }}
        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5rem;
        }}
        .header .subtitle {{
            margin-top: 10px;
            opacity: 0.9;
        }}
        .stats {{
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
            margin: 30px 0;
            gap: 20px;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            text-align: center;
            flex: 1;
            min-width: 200px;
        }}
        .stat-number {{
            font-size: 2rem;
            font-weight: bold;
            color: #667eea;
        }}
        .stat-label {{
            color: #666;
            margin-top: 5px;
        }}
        .gallery {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .image-card {{
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease;
        }}
        .image-card:hover {{
            transform: translateY(-5px);
        }}
        .image-container {{
            width: 100%;
            height: 250px;
            overflow: hidden;
        }}
        .image-container img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
        }}
        .image-info {{
            padding: 15px;
        }}
        .image-id {{
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        }}
        .image-variant {{
            color: #667eea;
            font-size: 0.9rem;
            margin-bottom: 5px;
        }}
        .image-score {{
            color: #666;
            font-size: 0.8rem;
        }}
        .summary {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin: 30px 0;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        .summary pre {{
            white-space: pre-wrap;
            word-wrap: break-word;
            font-family: 'Courier New', monospace;
            font-size: 0.9rem;
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            color: #666;
            font-size: 0.9rem;
            border-top: 1px solid #eee;
        }}
        .tag {{
            display: inline-block;
            background: #e9ecef;
            color: #495057;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 0.8rem;
            margin-right: 5px;
            margin-bottom: 5px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎨 Athena IP形象图像画廊</h1>
        <div class="subtitle">硅基共生主题 · 三体叙事风格 · 漫威电影视觉效果</div>
    </div>

    <div class="stats">
        <div class="stat-card">
            <div class="stat-number">{len(assets)}</div>
            <div class="stat-label">总资产数</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{len(image_files)}</div>
            <div class="stat-label">已下载图像</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">8.0</div>
            <div class="stat-label">平均质量评分</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">核心形象-硅基共生</div>
            <div class="stat-label">当前变体</div>
        </div>
    </div>
"""

    # 添加图像画廊
    if image_files:
        html_content += """
    <div class="gallery">
"""

        # 为每个图像文件创建卡片
        for img_file in image_files[:12]:  # 最多显示12张
            # 查找对应的资产信息
            img_name = img_file.stem
            matching_asset = None

            # 尝试通过文件名匹配资产
            for asset in assets:
                if asset.get("id", "").replace("_", "") in img_name:
                    matching_asset = asset
                    break

            # 获取图像尺寸信息（简化处理）
            file_size = img_file.stat().st_size / 1024  # KB

            html_content += f"""
        <div class="image-card">
            <div class="image-container">
                <img src="{img_file.relative_to(Path(__file__).parent)}" alt="Athena图像">
            </div>
            <div class="image-info">
"""

            if matching_asset:
                html_content += f"""
                <div class="image-id">{matching_asset.get('id', '未知ID')}</div>
                <div class="image-variant">{matching_asset.get('variant_name', '未知变体')}</div>
                <div class="image-score">质量评分: {matching_asset.get('quality_score', 0)}/10</div>
"""
                # 显示标签
                tags = matching_asset.get("tags", [])
                if tags:
                    html_content += '<div style="margin-top: 10px;">'
                    for tag in tags[:3]:  # 最多显示3个标签
                        html_content += f'<span class="tag">{tag}</span>'
                    html_content += "</div>"

            html_content += f"""
                <div class="image-score">文件大小: {file_size:.1f} KB</div>
                <div class="image-score">格式: {img_file.suffix.upper()[1:]}</div>
            </div>
        </div>
"""

        html_content += """
    </div>
"""
    else:
        html_content += """
    <div style="text-align: center; padding: 40px; background: white; border-radius: 10px;">
        <h3>📷 暂无图像</h3>
        <p>请先运行图像下载脚本</p>
    </div>
"""

    # 添加资产摘要
    if summary_content:
        html_content += f"""
    <div class="summary">
        <h2>📋 资产摘要</h2>
        <pre>{html.escape(summary_content)}</pre>
    </div>
"""

    # 添加技术信息
    html_content += f"""
    <div class="summary">
        <h2>🔧 技术信息</h2>
        <p><strong>生成时间:</strong> 2026-04-16</p>
        <p><strong>图像来源:</strong> 豆包AI绘画 (字节跳动)</p>
        <p><strong>生成模型:</strong> Seedream 文生图模型</p>
        <p><strong>图像尺寸:</strong> 1024×1024 像素</p>
        <p><strong>设计主题:</strong> 硅基共生 · AI女神Athena · 三体叙事风格 · 漫威电影视觉</p>
        <p><strong>目标用户:</strong> GitHub用户 (80/90后为主，喜欢漫威电影风格)</p>
    </div>

    <div class="footer">
        <p>🎯 Clawra模块 · Athena IP形象系统 · 生成时间: 2026-04-16</p>
        <p>💡 提示: 所有图像均为豆包AI生成，受版权保护，仅用于展示和技术验证</p>
    </div>
</body>
</html>
"""

    # 保存HTML文件
    html_file = Path(__file__).parent / "data" / "athena_assets" / "athena_gallery.html"
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"✅ 生成HTML画廊: {html_file}")

    # 返回HTML文件路径
    return str(html_file)


def main():
    """主函数"""
    print("🎨 生成Athena图像画廊HTML页面")
    print("=" * 60)

    # 1. 加载资产数据
    assets = load_assets()
    if not assets:
        print("❌ 无资产数据，请先生成图像")
        return 1

    # 2. 获取图像文件
    image_files = get_image_files()

    # 3. 创建HTML画廊
    html_file = create_html_gallery(assets, image_files)

    # 4. 打开HTML文件（如果可能）
    try:
        import os
        import webbrowser

        # 转换为文件URL
        html_path = Path(html_file)
        if html_path.exists():
            # 在浏览器中打开
            webbrowser.open(f"file://{html_path.absolute()}")
            print(f"✅ 已在浏览器中打开: {html_path}")
        else:
            print(f"⚠️  HTML文件不存在: {html_path}")
    except Exception as e:
        print(f"⚠️  无法自动打开浏览器: {e}")
        print(f"📁 请手动打开文件: {html_file}")

    print(f"\n🎯 画廊生成完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
