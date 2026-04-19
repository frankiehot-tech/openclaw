#!/usr/bin/env python3
"""
从豆包页面提取已生成的Athena图像并保存为资产
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from athena_image_asset_manager import AthenaImageAssetManager
from external.ROMA.doubao_cli_enhanced import DoubaoCLIEnhanced


class AthenaImageExtractor:
    """Athena图像提取器"""

    def __init__(self):
        self.cli = DoubaoCLIEnhanced()
        self.asset_manager = AthenaImageAssetManager()
        self.extracted_images = []

    def check_current_page(self):
        """检查当前页面"""
        print("🔧 检查当前页面...")

        check_js = """
        // 检查当前页面信息
        var pageInfo = {
            path: window.location.pathname,
            title: document.title,
            hasAICreation: false,
            hasGeneratedImages: false
        };

        var bodyText = (document.body.innerText || '').toLowerCase();
        if (bodyText.includes('描述你所想象的画面') || bodyText.includes('ai 创作')) {
            pageInfo.hasAICreation = true;
        }

        // 检查是否有生成的图像
        var images = document.querySelectorAll('img');
        for (var i = 0; i < images.length; i++) {
            var src = images[i].src || '';
            if (src.includes('image_generation') && src.includes('byteimg.com')) {
                pageInfo.hasGeneratedImages = true;
                break;
            }
        }

        JSON.stringify(pageInfo);
        """

        result = self.cli.execute_javascript_enhanced(check_js)
        if not result.success:
            print("❌ 检查页面失败")
            return None

        try:
            data = json.loads(self.cli._clean_js_output(result.output))
            print(f"  当前路径: {data.get('path')}")
            print(f"  页面标题: {data.get('title')}")
            print(f"  是否AI创作页面: {data.get('hasAICreation')}")
            print(f"  是否有生成图像: {data.get('hasGeneratedImages')}")
            return data
        except Exception as e:
            print(f"解析页面信息失败: {e}")
            return None

    def extract_all_images(self):
        """提取所有生成的图像"""
        print("\n🔧 提取所有生成的图像...")

        extract_js = """
        // 提取所有生成的图像
        var allImages = [];
        var images = document.querySelectorAll('img');

        for (var i = 0; i < images.length; i++) {
            var img = images[i];
            var src = img.src || '';

            // 只提取生成的图像（豆包特定的URL模式）
            if (src && src.includes('image_generation') && src.includes('byteimg.com')) {
                // 尝试获取更多上下文信息
                var parent = img.parentElement;
                var contextInfo = '';
                var altText = img.alt || '';

                // 检查父元素是否有相关文本
                while (parent && parent !== document.body) {
                    var parentText = (parent.textContent || parent.innerText || '').trim();
                    if (parentText && parentText.length > 0 && parentText.length < 200) {
                        contextInfo = parentText;
                        break;
                    }
                    parent = parent.parentElement;
                }

                allImages.push({
                    index: i,
                    src: src,
                    alt: altText,
                    className: img.className || '',
                    contextInfo: contextInfo,
                    // 获取位置信息（用于排序）
                    rect: (function() {
                        try {
                            var rect = img.getBoundingClientRect();
                            return rect.top + ',' + rect.left;
                        } catch(e) {
                            return '0,0';
                        }
                    })()
                });
            }
        }

        // 按位置排序（从上到下，从左到右）
        allImages.sort(function(a, b) {
            var aRect = a.rect.split(',').map(Number);
            var bRect = b.rect.split(',').map(Number);

            if (aRect[0] !== bRect[0]) return aRect[0] - bRect[0];
            return aRect[1] - bRect[1];
        });

        JSON.stringify({
            totalImages: images.length,
            generatedImages: allImages.length,
            images: allImages
        });
        """

        result = self.cli.execute_javascript_enhanced(extract_js)
        if not result.success or not result.output or result.output == "missing value":
            print("❌ 提取图像失败")
            return []

        try:
            data = json.loads(self.cli._clean_js_output(result.output))
            image_count = data.get("generatedImages", 0)
            images = data.get("images", [])

            print(f"✅ 找到 {image_count} 张生成的图像")

            # 显示部分图像信息
            for i, img in enumerate(images[:5]):  # 显示前5个
                src_preview = (
                    img.get("src", "")[:80] + "..."
                    if len(img.get("src", "")) > 80
                    else img.get("src", "")
                )
                print(f"  {i+1}. {src_preview}")
                if img.get("contextInfo"):
                    print(f"     上下文: {img.get('contextInfo')[:50]}...")

            if image_count > 5:
                print(f"  ... 还有 {image_count - 5} 张图像未显示")

            return images
        except Exception as e:
            print(f"解析图像数据失败: {e}")
            return []

    def map_variants_to_images(self, images):
        """将图像映射到Athena变体（智能猜测）"""
        print("\n🔧 智能映射图像到Athena变体...")

        # Athena变体列表（基于generate_10_athena_images.py）
        athena_variants = [
            {
                "name": "核心形象-硅基共生",
                "keywords": ["硅基", "机械", "生物融合", "硅晶体", "电路板", "能量核心"],
                "prompt": "硅基共生主题的AI女神Athena，三体叙事风格，漫威电影视觉效果...",
            },
            {
                "name": "战斗形态-能量爆发",
                "keywords": ["战斗", "能量爆发", "电弧", "数据流", "能量武器", "破损战衣"],
                "prompt": "战斗形态的Athena，硅基共生主题，能量爆发瞬间...",
            },
            {
                "name": "思考形态-数据空间",
                "keywords": ["思考", "数据空间", "数据流", "算法", "半透明", "数据光环"],
                "prompt": "思考形态的Athena，悬浮在数据空间中沉思...",
            },
            {
                "name": "领袖形态-指挥中心",
                "keywords": ["领袖", "指挥中心", "全息显示", "指挥官", "金色纹路", "权威"],
                "prompt": "领袖形态的Athena，站在指挥中心俯瞰数字世界...",
            },
            {
                "name": "守护形态-防御姿态",
                "keywords": ["守护", "防御", "能量护盾", "护甲", "防御算法", "保护"],
                "prompt": "守护形态的Athena，展开能量护盾保护身后的数字世界...",
            },
            {
                "name": "进化形态-升级过程",
                "keywords": ["进化", "升级", "数据粒子", "形态转变", "进度条", "重构"],
                "prompt": "进化形态的Athena，正在进行系统升级和形态转变...",
            },
            {
                "name": "连接形态-网络节点",
                "keywords": ["连接", "网络", "数据线", "节点", "接口", "网络连接"],
                "prompt": "连接形态的Athena，作为网络核心节点与其他AI连接...",
            },
            {
                "name": "学习形态-知识吸收",
                "keywords": ["学习", "知识", "晶体", "代码", "公式", "学者", "图书馆"],
                "prompt": "学习形态的Athena，正在吸收和分析海量知识数据...",
            },
            {
                "name": "创造形态-艺术生成",
                "keywords": ["创造", "艺术", "绘画", "音乐", "诗歌", "创意", "灵感"],
                "prompt": "创造形态的Athena，正在生成数字艺术作品和创意内容...",
            },
            {
                "name": "未来形态-终极进化",
                "keywords": ["未来", "终极", "进化", "能量", "数据", "虚实转换", "完美"],
                "prompt": "未来形态的Athena，完成终极进化的完美形态...",
            },
        ]

        mapping_results = []

        # 如果图像数量足够多，尝试按顺序分配
        # 假设：图像是按生成顺序排列的，每个变体生成约30张图像
        images_per_variant = 30  # 豆包每次生成约30张
        total_variants = len(athena_variants)

        print(f"  假设每个变体生成约 {images_per_variant} 张图像")
        print(
            f"  共有 {len(images)} 张图像，预计对应 {min(total_variants, len(images) // images_per_variant)} 个变体"
        )

        # 按顺序分配变体
        for i, img in enumerate(images):
            variant_index = i // images_per_variant
            if variant_index < total_variants:
                variant = athena_variants[variant_index]
                variant_name = variant["name"]
                prompt = variant["prompt"]

                # 检查上下文信息是否匹配关键词
                context_info = img.get("contextInfo", "").lower()
                alt_text = img.get("alt", "").lower()
                match_score = 0

                for keyword in variant["keywords"]:
                    if keyword in context_info or keyword in alt_text:
                        match_score += 1

                mapping_results.append(
                    {
                        "image": img,
                        "variant_name": variant_name,
                        "variant_index": variant_index,
                        "prompt": prompt,
                        "match_score": match_score,
                        "method": "sequential" if match_score == 0 else "keyword_match",
                    }
                )
            else:
                # 超过变体数量，分配到最后一个变体
                mapping_results.append(
                    {
                        "image": img,
                        "variant_name": athena_variants[-1]["name"],
                        "variant_index": total_variants - 1,
                        "prompt": athena_variants[-1]["prompt"],
                        "match_score": 0,
                        "method": "fallback",
                    }
                )

        # 统计映射结果
        variant_counts = {}
        for result in mapping_results:
            variant_name = result["variant_name"]
            variant_counts[variant_name] = variant_counts.get(variant_name, 0) + 1

        print(f"\n📋 映射结果统计:")
        for variant_name, count in variant_counts.items():
            print(f"  {variant_name}: {count}张图像")

        return mapping_results

    def save_to_asset_manager(self, mapping_results):
        """保存映射结果到资产管理器"""
        print("\n💾 保存图像资产...")

        saved_count = 0
        duplicate_count = 0

        for i, result in enumerate(mapping_results):
            img = result["image"]
            variant_name = result["variant_name"]
            prompt = result["prompt"]
            image_url = img.get("src", "")

            if not image_url:
                continue

            # 添加到资产管理器
            try:
                asset = self.asset_manager.add_asset_from_generation(
                    variant_name=variant_name,
                    prompt=prompt,
                    image_url=image_url,
                    notes=f"从页面提取，映射方法: {result['method']}，匹配分数: {result['match_score']}",
                )
                saved_count += 1

                if i < 5:  # 显示前5个保存的资产
                    print(f"  ✅ 保存: {asset.id} ({variant_name})")

            except Exception as e:
                # 可能是重复资产
                duplicate_count += 1

        # 保存所有资产到文件
        self.asset_manager.save_assets()

        print(f"\n📊 保存完成:")
        print(f"   成功保存: {saved_count} 个资产")
        print(f"   重复跳过: {duplicate_count} 个")

        return saved_count

    def extract_and_save(self):
        """主要提取流程"""
        print("🎯 从豆包页面提取Athena图像资产")
        print("=" * 60)

        # 1. 检查当前页面
        page_info = self.check_current_page()
        if not page_info:
            print("❌ 无法获取页面信息")
            return False

        if not page_info.get("hasAICreation"):
            print("⚠️  当前页面可能不是AI创作页面")
            # 仍然尝试提取

        # 2. 提取所有图像
        images = self.extract_all_images()
        if not images:
            print("❌ 未找到生成的图像")
            return False

        # 3. 映射到Athena变体
        mapping_results = self.map_variants_to_images(images)

        # 4. 保存到资产管理器
        saved_count = self.save_to_asset_manager(mapping_results)

        # 5. 分析资产
        if saved_count > 0:
            self.asset_manager.analyze_assets()
            self.asset_manager.export_summary()

        print("\n" + "=" * 60)
        print(f"📊 提取完成")
        print(f"   发现图像: {len(images)} 张")
        print(f"   保存资产: {saved_count} 个")
        print("=" * 60)

        return saved_count > 0


def main():
    """主函数"""
    print("🎯 从豆包页面提取已生成的Athena图像")
    print("=" * 60)

    try:
        # 创建提取器
        extractor = AthenaImageExtractor()

        # 执行提取
        success = extractor.extract_and_save()

        return 0 if success else 1

    except Exception as e:
        print(f"\n❌ 提取出错: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
