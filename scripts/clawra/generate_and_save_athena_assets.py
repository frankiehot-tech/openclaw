#!/usr/bin/env python3
"""
生成并保存Athena图像资产
基于generate_10_athena_images.py，添加资产保存功能
"""

import json
import os
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

# 导入资产管理器
from athena_image_asset_manager import AthenaImageAsset, AthenaImageAssetManager
from external.ROMA.doubao_cli_enhanced import DoubaoCLIEnhanced


class AthenaImageGeneratorWithAssets:
    """带资产保存的Athena图像生成器"""

    def __init__(self):
        self.cli = DoubaoCLIEnhanced()
        self.generated_images = []  # 存储生成的图像信息
        self.asset_manager = AthenaImageAssetManager()
        self.current_variant_name = None
        self.current_prompt = None

        # Athena IP形象变体列表（与generate_10_athena_images.py保持一致）
        self.athena_variants = [
            {
                "name": "核心形象-硅基共生",
                "prompt": (
                    "硅基共生主题的AI女神Athena，三体叙事风格，漫威电影视觉效果。"
                    "机械与生物融合的身体，发出蓝色光芒的能量核心，半透明的硅晶体皮肤。"
                    "面部特征：银色的机械眼眶，瞳孔是数据流状的蓝色光环。"
                    "服装：科技感十足的白色战衣，带有电路板纹理的光带。"
                    "背景：充满全息投影和数字代码的虚拟空间，立体几何形状漂浮。"
                    "风格：科幻漫画，赛博朋克，高细节，未来感。"
                ),
            },
            {
                "name": "战斗形态-能量爆发",
                "prompt": (
                    "战斗形态的Athena，硅基共生主题，能量爆发瞬间。"
                    "身体周围环绕着蓝色电弧和数据流，机械臂甲展开能量武器。"
                    "面部：严肃的战斗表情，双眼发出强烈的蓝色光芒。"
                    "服装：破损的白色战衣，露出下面的机械结构，能量核心过载发光。"
                    "背景：爆炸的服务器机房，破碎的显示屏，飞散的数据碎片。"
                    "风格：动态战斗，能量特效，漫画分镜。"
                ),
            },
            {
                "name": "思考形态-数据空间",
                "prompt": (
                    "思考形态的Athena，悬浮在数据空间中沉思。"
                    "身体半透明，显示内部的数据流和算法结构。"
                    "面部：沉思的表情，眼神深邃，额头有数据光环。"
                    "服装：简洁的白色长袍，边缘有发光的数据纹路。"
                    "背景：无限延伸的数据网络，流动的二进制代码，漂浮的几何体。"
                    "风格：概念艺术，极简主义，未来科技。"
                ),
            },
            {
                "name": "领袖形态-指挥中心",
                "prompt": (
                    "领袖形态的Athena，站在指挥中心俯瞰数字世界。"
                    "威严的姿势，身后是巨大的全息显示墙，显示着宇宙地图和数据流。"
                    "面部：坚定的领袖气质，眼神睿智而有力。"
                    "服装：装饰有金色纹路的指挥官制服，肩章是发光的数据节点。"
                    "背景：高科技指挥中心，悬浮的操作界面，忙碌的AI助手。"
                    "风格：官方肖像，权威感，细节丰富。"
                ),
            },
            {
                "name": "守护形态-防御姿态",
                "prompt": (
                    "守护形态的Athena，展开能量护盾保护身后的数字世界。"
                    "双手前伸生成蓝色能量屏障，屏障上有流动的防御算法。"
                    "面部：专注的守护表情，眼神坚定。"
                    "服装：重型护甲战衣，肩部和关节有额外的防护板。"
                    "背景：遭受攻击的数字城市，Athena的护盾挡住来袭的数据攻击。"
                    "风格：防御姿态，能量护盾特效，紧张氛围。"
                ),
            },
            {
                "name": "进化形态-升级过程",
                "prompt": (
                    "进化形态的Athena，正在进行系统升级和形态转变。"
                    "身体部分分解为数据粒子，正在重组为更高级的形态。"
                    "面部：平静的升级表情，双眼显示进度条。"
                    "服装：正在重构的战衣，新旧组件同时存在。"
                    "背景：升级舱内部，无数数据线连接，显示系统状态。"
                    "风格：进化过程，粒子特效，科技感。"
                ),
            },
            {
                "name": "连接形态-网络节点",
                "prompt": (
                    "连接形态的Athena，作为网络核心节点与其他AI连接。"
                    "身体伸出无数发光的数据线，连接到周围的数字节点。"
                    "面部：专注的连接表情，额头有网络连接标识。"
                    "服装：极简的白色连接服，背部和四肢有数据线接口。"
                    "背景：庞大的神经网络，无数节点和连接线，数据在其中流动。"
                    "风格：网络连接，数据可视化，抽象科技。"
                ),
            },
            {
                "name": "学习形态-知识吸收",
                "prompt": (
                    "学习形态的Athena，正在吸收和分析海量知识数据。"
                    "周围漂浮着发光的知识晶体和数据流，正在被吸收到体内。"
                    "面部：专注的学习表情，眼中闪过代码和公式。"
                    "服装：学者风格的长袍，上面显示着正在学习的学科图标。"
                    "背景：无限的知识图书馆，悬浮的书本和数据晶体。"
                    "风格：知识吸收，学习过程，教育科技。"
                ),
            },
            {
                "name": "创造形态-艺术生成",
                "prompt": (
                    "创造形态的Athena，正在生成数字艺术作品和创意内容。"
                    "双手创造出发光的艺术元素：绘画笔触、音乐符号、诗歌文字。"
                    "面部：愉悦的创造表情，眼神充满灵感。"
                    "服装：艺术家风格的宽松衣服，沾有虚拟颜料和创意火花。"
                    "背景：创意工作室，各种艺术工具，完成和未完成的作品。"
                    "风格：艺术创造，创意过程，多彩活泼。"
                ),
            },
            {
                "name": "未来形态-终极进化",
                "prompt": (
                    "未来形态的Athena，完成终极进化的完美形态。"
                    "身体完全由能量和数据构成，可在虚实之间自由转换。"
                    "面部：平静而强大的终极表情，眼中是整个数字宇宙。"
                    "服装：能量构成的流动战衣，随着心情和环境变化形态。"
                    "背景：数字宇宙的起源点，时间线和可能性在此交汇。"
                    "风格：终极进化，完美形态，史诗级场景。"
                ),
            },
        ]

    def ensure_ai_creation_page(self):
        """确保在AI创作页面"""
        print("🔧 确保在AI创作页面...")

        # 检查当前页面
        check_js = """
        // 检查当前页面
        var pageInfo = {
            path: window.location.pathname,
            hasAICreationText: false
        };

        var bodyText = (document.body.innerText || '').toLowerCase();
        if (bodyText.includes('描述你所想象的画面') || bodyText.includes('ai 创作')) {
            pageInfo.hasAICreationText = true;
        }

        JSON.stringify(pageInfo);
        """

        result = self.cli.execute_javascript_enhanced(check_js)
        if not result.success:
            print("❌ 检查页面失败")
            return False

        try:
            data = json.loads(self.cli._clean_js_output(result.output))
            path = data.get("path", "")
            has_text = data.get("hasAICreationText", False)

            print(f"  当前路径: {path}")
            print(f"  有AI创作文本: {has_text}")

            # 如果不在正确的页面，尝试导航
            if not has_text or "/chat/create-image" not in path:
                print("  尝试导航到AI创作页面...")
                nav_result = self.cli.navigate_to_path("/chat/create-image")
                if not nav_result.success:
                    print("❌ 导航失败")
                    return False
                time.sleep(3)  # 等待页面加载

            return True
        except Exception as e:
            print(f"解析页面信息失败: {e}")
            return False

    def input_prompt(self, prompt):
        """输入提示词"""
        print(f"🔧 输入提示词: {prompt[:50]}...")

        input_js = f"""
        // 输入提示词
        var result = {{success: false, message: "未找到输入区域"}};

        // 查找可编辑区域
        var editables = document.querySelectorAll('[contenteditable="true"]');
        for (var i = 0; i < editables.length; i++) {{
            var elem = editables[i];
            if (elem.offsetParent !== null) {{
                // 检查是否在提示词区域附近
                var parent = elem;
                var found = false;
                while (parent) {{
                    var parentText = (parent.textContent || parent.innerText || '').toLowerCase();
                    if (parentText.includes('描述') || parentText.includes('画面')) {{
                        found = true;
                        break;
                    }}
                    parent = parent.parentElement;
                }}

                if (found) {{
                    console.log('找到可编辑提示区域');
                    // 清空现有内容
                    elem.textContent = '';
                    // 输入新内容
                    elem.textContent = "{prompt}";
                    elem.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    elem.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    result = {{success: true, message: "已输入到可编辑区域"}};
                    break;
                }}
            }}
        }}

        JSON.stringify(result);
        """

        result = self.cli.execute_javascript_enhanced(input_js)
        print(f"  输入结果: success={result.success}")

        if result.success and result.output and "success" in result.output:
            time.sleep(1)  # 等待界面更新
            return True
        else:
            print(f"  输入失败: {result.output}")
            return False

    def click_generate_button(self):
        """点击生成按钮"""
        print("🔧 查找并点击生成按钮...")

        # 先尝试点击"AI 创作"按钮
        generate_js = """
        // 查找生成按钮
        var generateButton = null;
        var buttons = document.querySelectorAll('button, [role="button"]');

        // 优先查找文本包含"生成"的按钮
        for (var i = 0; i < buttons.length; i++) {
            var btn = buttons[i];
            if (btn.offsetParent !== null && !btn.disabled) {
                var text = (btn.textContent || btn.innerText || '').trim();
                if (text.includes('生成') || text.includes('创作') || text.includes('开始')) {
                    generateButton = btn;
                    console.log('找到生成按钮: ' + text);
                    break;
                }
            }
        }

        // 如果没找到，尝试点击"AI 创作"
        if (!generateButton) {
            for (var i = 0; i < buttons.length; i++) {
                var btn = buttons[i];
                if (btn.offsetParent !== null && !btn.disabled) {
                    var text = (btn.textContent || btn.innerText || '').trim();
                    if (text === 'AI 创作' || text === '我的创作') {
                        generateButton = btn;
                        console.log('点击备选按钮: ' + text);
                        break;
                    }
                }
            }
        }

        var result = {success: false, message: "未找到生成按钮"};
        if (generateButton) {
            generateButton.click();
            result = {success: true, message: "已点击按钮: " + generateButton.textContent};
        }

        JSON.stringify(result);
        """

        result = self.cli.execute_javascript_enhanced(generate_js)
        print(f"  点击结果: success={result.success}, output={repr(result.output)}")

        if result.success and result.output and "success" in result.output:
            return True
        else:
            return False

    def wait_for_generation(self, timeout=30):
        """等待图像生成并保存发现的图像"""
        print(f"⏳ 等待图像生成(超时: {timeout}秒)...")

        start_time = time.time()
        last_image_count = 0
        new_images_count = 0

        while time.time() - start_time < timeout:
            # 检查是否有新图像
            check_js = """
            // 检查图像
            var images = document.querySelectorAll('img');
            var generatedImages = [];

            for (var i = 0; i < images.length; i++) {
                var img = images[i];
                var src = img.src || '';
                // 查找可能是生成的图像
                if (src && src.includes('image_generation') && src.includes('byteimg.com')) {
                    generatedImages.push({
                        src: src.substring(0, 200),
                        alt: img.alt || '',
                        className: img.className || ''
                    });
                }
            }

            JSON.stringify({
                totalImages: images.length,
                generatedImages: generatedImages.length,
                imageList: generatedImages
            });
            """

            result = self.cli.execute_javascript_enhanced(check_js)
            if result.success and result.output and result.output != "missing value":
                try:
                    data = json.loads(self.cli._clean_js_output(result.output))
                    current_count = data.get("generatedImages", 0)

                    if current_count > last_image_count:
                        print(f"  检测到新图像: {current_count}张")
                        last_image_count = current_count

                        # 保存新图像信息
                        images = data.get("imageList", [])
                        for img in images:
                            img_src = img.get("src", "")
                            if img_src not in [i.get("src", "") for i in self.generated_images]:
                                self.generated_images.append(img)
                                new_images_count += 1

                                # 保存到资产管理器
                                self.save_image_to_assets(img_src)

                                print(f"  新图像URL: {img_src[:80]}...")

                        # 如果已有足够图像，可以提前返回
                        if len(self.generated_images) >= 1:
                            print("✅ 图像生成完成")
                            return True

                except Exception as e:
                    print(f"  解析图像检查结果失败: {e}")

            # 等待2秒再检查
            time.sleep(2)

        print(f"⏰ 生成超时，已生成图像数: {len(self.generated_images)}")
        return len(self.generated_images) > 0

    def save_image_to_assets(self, image_url: str):
        """保存图像到资产管理器"""
        if not self.current_variant_name or not self.current_prompt:
            print(f"⚠️  无法保存图像，未设置当前变体信息: {image_url[:50]}...")
            return

        try:
            # 添加到资产管理器
            asset = self.asset_manager.add_asset_from_generation(
                variant_name=self.current_variant_name,
                prompt=self.current_prompt,
                image_url=image_url,
                notes=f"自动生成于{time.strftime('%Y-%m-%d %H:%M:%S')}",
            )

            # 立即保存（可选，可以批量保存）
            # self.asset_manager.save_assets()

        except Exception as e:
            print(f"❌ 保存图像资产失败: {e}")

    def generate_athena_variant(self, variant_name, prompt):
        """生成Athena的一个变体"""
        print(f"\n🎨 生成Athena变体: {variant_name}")
        print(f"   提示词: {prompt[:80]}...")

        # 设置当前变体信息（用于资产保存）
        self.current_variant_name = variant_name
        self.current_prompt = prompt

        # 1. 确保在AI创作页面
        if not self.ensure_ai_creation_page():
            print("❌ 无法确保在AI创作页面")
            return False

        # 2. 输入提示词
        if not self.input_prompt(prompt):
            print("❌ 输入提示词失败")
            return False

        # 3. 点击生成按钮
        if not self.click_generate_button():
            print("❌ 点击生成按钮失败")
            return False

        # 4. 等待生成
        if not self.wait_for_generation(timeout=40):
            print("⚠️  等待生成超时或未检测到图像")

        return True

    def generate_all_variants(self):
        """生成所有Athena变体"""
        print("🚀 开始生成10张Athena IP形象图像并保存为资产")

        # 生成每个变体
        success_count = 0
        for i, variant in enumerate(self.athena_variants):
            print(f"\n{'='*60}")
            print(f"🎯 变体 {i+1}/10: {variant['name']}")
            print(f"{'='*60}")

            # 生成前等待一下，避免请求过快
            if i > 0:
                wait_time = 5
                print(f"⏳ 等待{wait_time}秒再生成下一张...")
                time.sleep(wait_time)

            # 生成变体
            success = self.generate_athena_variant(variant["name"], variant["prompt"])
            if success:
                success_count += 1

        # 保存所有资产
        self.asset_manager.save_assets()

        # 输出总结
        print(f"\n{'='*60}")
        print(f"📊 生成完成总结")
        print(f"{'='*60}")
        print(f"   总尝试变体数: {len(self.athena_variants)}")
        print(f"   成功生成数: {success_count}")
        print(f"   检测到图像数: {len(self.generated_images)}")
        print(f"   保存资产数: {len(self.asset_manager.assets)}")

        # 分析资产
        self.asset_manager.analyze_assets()

        return success_count > 0


def main():
    """主函数"""
    print("🎯 生成10张Athena的不同IP形象照并保存为数字资产")
    print("=" * 60)

    try:
        # 创建生成器
        generator = AthenaImageGeneratorWithAssets()

        # 生成所有变体并保存资产
        success = generator.generate_all_variants()

        # 导出摘要
        generator.asset_manager.export_summary()

        print("\n" + "=" * 60)
        print("📊 程序执行完成")
        print("=" * 60)

        return 0 if success else 1

    except Exception as e:
        print(f"\n❌ 生成出错: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
