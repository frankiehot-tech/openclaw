#!/usr/bin/env python3
"""
查看和验证生成的Athena图像
从资产数据库读取图像URL，尝试下载和显示图像
"""

import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

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


def test_url_access(url):
    """测试URL是否可访问"""
    try:
        # 添加浏览器头部，模拟正常访问
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://www.doubao.com/",
        }

        print(f"🔗 测试URL: {url[:80]}...")
        response = requests.get(url, headers=headers, timeout=10, stream=True)

        if response.status_code == 200:
            content_type = response.headers.get("content-type", "")
            content_length = response.headers.get("content-length", "unknown")

            print(f"✅ URL可访问:")
            print(f"   状态码: {response.status_code}")
            print(f"   内容类型: {content_type}")
            print(f"   内容长度: {content_length}")

            # 检查是否是有效的图像
            if content_type.startswith("image/"):
                print(f"   ✅ 是有效的图像文件")
                return True, response
            else:
                print(f"   ⚠️  不是图像文件: {content_type}")
                return False, response
        else:
            print(f"❌ URL访问失败:")
            print(f"   状态码: {response.status_code}")
            print(f"   响应头: {dict(response.headers)}")
            return False, response

    except Exception as e:
        print(f"❌ URL测试出错: {e}")
        return False, None


def download_image(url, save_dir="data/athena_assets/images"):
    """下载图像到本地"""
    try:
        save_path = Path(save_dir)
        save_path.mkdir(parents=True, exist_ok=True)

        # 生成文件名
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"athena_{timestamp}_{url_hash}.jpg"
        filepath = save_path / filename

        # 下载图像
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.doubao.com/",
        }

        print(f"⬇️  下载图像: {url[:60]}...")
        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code == 200:
            with open(filepath, "wb") as f:
                f.write(response.content)

            file_size = os.path.getsize(filepath) / 1024  # KB
            print(f"✅ 下载成功:")
            print(f"   保存位置: {filepath}")
            print(f"   文件大小: {file_size:.1f} KB")

            return str(filepath)
        else:
            print(f"❌ 下载失败，状态码: {response.status_code}")
            return None

    except Exception as e:
        print(f"❌ 下载出错: {e}")
        return None


def analyze_assets(assets):
    """分析资产数据"""
    print(f"\n📊 Athena图像资产分析")
    print(f"=" * 60)

    if not assets:
        print("⚠️  无资产数据")
        return

    # 基础统计
    total_assets = len(assets)
    print(f"总资产数: {total_assets}")

    # 按变体统计
    variant_counts = {}
    for asset in assets:
        variant = asset.get("variant_name", "未知")
        variant_counts[variant] = variant_counts.get(variant, 0) + 1

    print(f"\n📋 按变体统计:")
    for variant, count in variant_counts.items():
        print(f"  {variant}: {count}个资产")

    # 质量评分统计
    quality_scores = [asset.get("quality_score", 0) for asset in assets]
    if quality_scores:
        avg_score = sum(quality_scores) / len(quality_scores)
        min_score = min(quality_scores)
        max_score = max(quality_scores)

        print(f"\n📊 质量评分统计:")
        print(f"   平均分: {avg_score:.1f}/10")
        print(f"   最低分: {min_score:.1f}")
        print(f"   最高分: {max_score:.1f}")

    # URL分析
    print(f"\n🔗 URL模式分析:")
    unique_domains = set()
    for asset in assets[:5]:  # 检查前5个
        url = asset.get("image_url", "")
        if "byteimg.com" in url:
            unique_domains.add("byteimg.com")
        if "image_generation" in url:
            print(f"  ✅ 包含'image_generation'标识")

    if unique_domains:
        print(f"  发现域名: {', '.join(unique_domains)}")


def main():
    """主函数"""
    print("🎯 查看和验证生成的Athena图像")
    print("=" * 60)

    # 1. 加载资产数据
    assets = load_assets()
    if not assets:
        print("❌ 无资产数据，请先生成图像")
        return 1

    # 2. 分析资产
    analyze_assets(assets)

    # 3. 测试前3个URL的可访问性
    print(f"\n🔍 测试图像URL可访问性 (前3个):")
    test_count = min(3, len(assets))

    accessible_urls = []
    for i in range(test_count):
        asset = assets[i]
        asset_id = asset.get("id", "未知")
        url = asset.get("image_url", "")

        print(f"\n{'='*40}")
        print(f"图像 {i+1}/{test_count}: {asset_id}")
        print(f"{'='*40}")

        if not url:
            print(f"❌ 无URL信息")
            continue

        # 测试URL
        is_accessible, response = test_url_access(url)

        if is_accessible and response:
            # 尝试下载
            saved_path = download_image(url)
            if saved_path:
                accessible_urls.append({"id": asset_id, "url": url, "path": saved_path})

    # 4. 总结
    print(f"\n{'='*60}")
    print(f"📊 验证结果总结")
    print(f"{'='*60}")
    print(f"   总资产数: {len(assets)}")
    print(f"   测试URL数: {test_count}")
    print(f"   可访问URL数: {len(accessible_urls)}")

    if accessible_urls:
        print(f"\n✅ 可访问的图像:")
        for item in accessible_urls:
            print(f"  - {item['id']}:")
            print(f"    下载位置: {item['path']}")
    else:
        print(f"\n⚠️  未成功下载任何图像")
        print(f"可能原因:")
        print(f"  1. URL已过期（豆包图像URL通常有时效性）")
        print(f"  2. 需要特定Referer或Cookie")
        print(f"  3. 网络访问限制")

    # 5. 建议
    print(f"\n💡 建议:")
    if len(accessible_urls) > 0:
        print(f"  1. 图像已保存到 data/athena_assets/images/ 目录")
        print(f"  2. 可以手动查看下载的图像文件")
        print(f"  3. 建议在生成后立即下载图像，避免URL过期")
    else:
        print(f"  1. 尝试重新生成图像")
        print(f"  2. 生成后立即下载图像")
        print(f"  3. 检查豆包图像URL的有效期")

    print(f"\n🎯 完成图像验证")
    return 0 if len(accessible_urls) > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
