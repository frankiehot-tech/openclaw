#!/usr/bin/env python3
"""
Athena图像资产管理脚本
用于保存、管理和筛选生成的Athena IP形象图像
"""

import hashlib
import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.append(str(Path(__file__).parent))

# 尝试导入豆包CLI增强模块
try:
    from external.ROMA.doubao_cli_enhanced import DoubaoCLIEnhanced
    from generate_10_athena_images import AthenaImageGenerator

    HAS_DOUBAO = True
except ImportError:
    HAS_DOUBAO = False
    print("⚠️  无法导入豆包模块，仅支持本地数据管理")


@dataclass
class AthenaImageAsset:
    """Athena图像资产数据结构"""

    # 基础信息
    id: str  # 唯一标识符
    variant_name: str  # 变体名称（如"核心形象-硅基共生"）
    variant_index: int  # 变体索引（1-10）

    # 生成信息
    prompt: str  # 完整的提示词
    prompt_preview: str  # 提示词预览（前100字符）
    generation_time: str  # 生成时间戳

    # 图像信息
    image_url: str  # 图像URL
    image_url_hash: str  # URL哈希（用于去重）
    image_filename: Optional[str] = None  # 保存的文件名

    # 质量评估
    quality_score: float = 0.0  # 质量评分（0-10）
    relevance_score: float = 0.0  # 与变体描述的相关性评分（0-10）
    creativity_score: float = 0.0  # 创意评分（0-10）
    technical_score: float = 0.0  # 技术实现评分（0-10）

    # 元数据
    tags: List[str] = field(default_factory=list)  # 标签（如"硅基", "机械", "未来感"）
    selected_for_showcase: bool = False  # 是否被选为展示图像
    notes: str = ""  # 备注

    # 统计分析
    view_count: int = 0  # 查看次数
    selection_count: int = 0  # 被选中的次数


class AthenaImageAssetManager:
    """Athena图像资产管理器"""

    def __init__(self, data_dir: str = None):
        """初始化管理器"""
        if data_dir is None:
            data_dir = str(Path(__file__).parent / "data" / "athena_assets")

        self.data_dir = Path(data_dir)
        self.assets_file = self.data_dir / "athena_assets.json"
        self.assets: List[AthenaImageAsset] = []
        self.variants_metadata: Dict[str, Dict] = {}

        # 创建数据目录
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 加载现有资产
        self.load_assets()

        # 初始化变体元数据（基于generate_10_athena_images.py）
        self.init_variants_metadata()

    def init_variants_metadata(self):
        """初始化变体元数据"""
        # 10个Athena变体的元数据
        self.variants_metadata = {
            "核心形象-硅基共生": {
                "index": 1,
                "category": "核心",
                "description": "硅基共生主题的AI女神Athena，机械与生物融合的身体",
                "key_elements": ["硅晶体皮肤", "蓝色能量核心", "机械眼眶", "电路板纹理"],
            },
            "战斗形态-能量爆发": {
                "index": 2,
                "category": "战斗",
                "description": "战斗形态的Athena，能量爆发瞬间，蓝色电弧和数据流环绕",
                "key_elements": ["能量武器", "蓝色电弧", "破损战衣", "战斗表情"],
            },
            "思考形态-数据空间": {
                "index": 3,
                "category": "思考",
                "description": "思考形态的Athena，悬浮在数据空间中沉思",
                "key_elements": ["数据流", "算法结构", "数据光环", "半透明身体"],
            },
            "领袖形态-指挥中心": {
                "index": 4,
                "category": "领袖",
                "description": "领袖形态的Athena，站在指挥中心俯瞰数字世界",
                "key_elements": ["全息显示墙", "指挥官制服", "金色纹路", "权威姿态"],
            },
            "守护形态-防御姿态": {
                "index": 5,
                "category": "守护",
                "description": "守护形态的Athena，展开能量护盾保护数字世界",
                "key_elements": ["能量护盾", "重型护甲", "防御算法", "专注表情"],
            },
            "进化形态-升级过程": {
                "index": 6,
                "category": "进化",
                "description": "进化形态的Athena，正在进行系统升级和形态转变",
                "key_elements": ["数据粒子", "系统升级", "形态转变", "进度条"],
            },
            "连接形态-网络节点": {
                "index": 7,
                "category": "连接",
                "description": "连接形态的Athena，作为网络核心节点与其他AI连接",
                "key_elements": ["数据线", "网络连接", "节点接口", "连接标识"],
            },
            "学习形态-知识吸收": {
                "index": 8,
                "category": "学习",
                "description": "学习形态的Athena，正在吸收和分析海量知识数据",
                "key_elements": ["知识晶体", "学习表情", "代码公式", "学者长袍"],
            },
            "创造形态-艺术生成": {
                "index": 9,
                "category": "创造",
                "description": "创造形态的Athena，正在生成数字艺术作品和创意内容",
                "key_elements": ["艺术元素", "创意火花", "艺术家风格", "灵感表情"],
            },
            "未来形态-终极进化": {
                "index": 10,
                "category": "未来",
                "description": "未来形态的Athena，完成终极进化的完美形态",
                "key_elements": ["能量构成", "虚实转换", "终极表情", "流动战衣"],
            },
        }

    def create_asset_id(self, variant_name: str, image_url: str) -> str:
        """创建资产ID（变体名称 + URL哈希）"""
        url_hash = hashlib.md5(image_url.encode()).hexdigest()[:8]
        variant_key = variant_name.replace(" ", "_").replace("-", "_")
        return f"athena_{variant_key}_{url_hash}"

    def add_asset_from_generation(
        self, variant_name: str, prompt: str, image_url: str, notes: str = ""
    ) -> AthenaImageAsset:
        """从生成结果添加资产"""
        # 检查是否已存在
        url_hash = hashlib.md5(image_url.encode()).hexdigest()
        existing = self.find_asset_by_url_hash(url_hash)
        if existing:
            print(f"⚠️  图像已存在: {existing.id}")
            return existing

        # 获取变体索引
        variant_meta = self.variants_metadata.get(variant_name, {"index": 0})
        variant_index = variant_meta["index"]

        # 创建新资产
        asset_id = self.create_asset_id(variant_name, image_url)

        asset = AthenaImageAsset(
            id=asset_id,
            variant_name=variant_name,
            variant_index=variant_index,
            prompt=prompt,
            prompt_preview=prompt[:100] + "..." if len(prompt) > 100 else prompt,
            generation_time=datetime.now().isoformat(),
            image_url=image_url,
            image_url_hash=url_hash,
            tags=self.extract_tags_from_prompt(prompt),
            notes=notes,
        )

        # 自动质量评估（基础版本）
        self.auto_assess_quality(asset)

        self.assets.append(asset)
        print(f"✅ 添加资产: {asset_id}")

        return asset

    def find_asset_by_url_hash(self, url_hash: str) -> Optional[AthenaImageAsset]:
        """通过URL哈希查找资产"""
        for asset in self.assets:
            if asset.image_url_hash == url_hash:
                return asset
        return None

    def extract_tags_from_prompt(self, prompt: str) -> List[str]:
        """从提示词中提取标签"""
        tags = []
        prompt_lower = prompt.lower()

        # 关键词映射
        keyword_tags = {
            "硅基": ["硅基", "硅晶体", "机械"],
            "能量": ["能量", "发光", "光芒", "电弧"],
            "数据": ["数据", "代码", "算法", "网络"],
            "未来": ["未来", "科幻", "赛博朋克"],
            "机械": ["机械", "机器人", "机械结构"],
            "艺术": ["艺术", "创意", "绘画", "音乐"],
            "战斗": ["战斗", "武器", "护甲", "防御"],
            "思考": ["思考", "沉思", "分析", "学习"],
            "领袖": ["领袖", "指挥", "权威", "中心"],
            "进化": ["进化", "升级", "转变", "重构"],
        }

        for tag_category, keywords in keyword_tags.items():
            for keyword in keywords:
                if keyword in prompt_lower:
                    tags.append(tag_category)
                    break

        # 去重
        return list(set(tags))

    def auto_assess_quality(self, asset: AthenaImageAsset):
        """自动质量评估（基础版本）"""
        # 基础评分：基于URL特征（豆包生成的URL通常有特定模式）
        base_score = 5.0

        # URL质量检查
        if "image_generation" in asset.image_url and "byteimg.com" in asset.image_url:
            base_score += 2.0  # 有效的豆包生成URL

        # 提示词质量检查
        prompt_length = len(asset.prompt)
        if prompt_length > 100:
            base_score += 1.0  # 详细提示词

        # 变体完整性检查
        variant_meta = self.variants_metadata.get(asset.variant_name, {})
        if variant_meta.get("index", 0) > 0:
            base_score += 1.0  # 有效的变体

        # 设置分数（0-10范围）
        asset.quality_score = min(10.0, base_score)
        asset.relevance_score = min(10.0, base_score - 1.0)  # 相关性略低于质量
        asset.creativity_score = min(10.0, base_score + 0.5)  # 创意分稍高
        asset.technical_score = min(10.0, base_score - 0.5)  # 技术分稍低

    def save_assets(self):
        """保存资产到JSON文件"""
        assets_data = []
        for asset in self.assets:
            asset_dict = asdict(asset)
            assets_data.append(asset_dict)

        with open(self.assets_file, "w", encoding="utf-8") as f:
            json.dump(assets_data, f, ensure_ascii=False, indent=2)

        print(f"💾 保存资产到: {self.assets_file} (共{len(assets_data)}个)")

    def load_assets(self):
        """从JSON文件加载资产"""
        if not self.assets_file.exists():
            print(f"📁 资产文件不存在，创建新文件: {self.assets_file}")
            self.assets = []
            return

        try:
            with open(self.assets_file, "r", encoding="utf-8") as f:
                assets_data = json.load(f)

            self.assets = []
            for asset_dict in assets_data:
                # 转换tags确保是列表
                if isinstance(asset_dict.get("tags"), str):
                    asset_dict["tags"] = [asset_dict["tags"]]

                # 创建资产对象
                asset = AthenaImageAsset(**asset_dict)
                self.assets.append(asset)

            print(f"📂 加载资产: {self.assets_file} (共{len(self.assets)}个)")
        except Exception as e:
            print(f"❌ 加载资产失败: {e}")
            self.assets = []

    def get_assets_by_variant(self, variant_name: str = None) -> List[AthenaImageAsset]:
        """按变体名称获取资产"""
        if variant_name is None:
            return self.assets

        return [asset for asset in self.assets if asset.variant_name == variant_name]

    def get_best_assets_per_variant(self, top_n: int = 3) -> Dict[str, List[AthenaImageAsset]]:
        """获取每个变体的最佳资产（按质量评分排序）"""
        best_assets = {}

        for variant_name in self.variants_metadata.keys():
            variant_assets = self.get_assets_by_variant(variant_name)

            # 按质量评分排序
            sorted_assets = sorted(variant_assets, key=lambda x: x.quality_score, reverse=True)

            best_assets[variant_name] = sorted_assets[:top_n]

        return best_assets

    def select_showcase_assets(self, per_variant: int = 1) -> List[AthenaImageAsset]:
        """选择展示用的资产（每个变体选择最佳的一个）"""
        # 重置所有资产的展示标记
        for asset in self.assets:
            asset.selected_for_showcase = False

        showcase_assets = []

        for variant_name in self.variants_metadata.keys():
            variant_assets = self.get_assets_by_variant(variant_name)
            if not variant_assets:
                continue

            # 选择质量最高的资产
            best_asset = max(variant_assets, key=lambda x: x.quality_score)
            best_asset.selected_for_showcase = True
            showcase_assets.append(best_asset)
            print(f"🏆 选择展示资产: {best_asset.id} (评分: {best_asset.quality_score:.1f})")

        return showcase_assets

    def analyze_assets(self):
        """分析资产数据"""
        print(f"\n📊 Athena图像资产分析")
        print(f"=" * 60)

        # 基础统计
        total_assets = len(self.assets)
        print(f"总资产数: {total_assets}")

        if total_assets == 0:
            print("⚠️  无资产数据")
            return

        # 按变体统计
        print(f"\n📋 按变体统计:")
        for variant_name in self.variants_metadata.keys():
            variant_assets = self.get_assets_by_variant(variant_name)
            if variant_assets:
                avg_score = sum(a.quality_score for a in variant_assets) / len(variant_assets)
                print(
                    f"  {variant_name}: {len(variant_assets)}个资产, 平均质量: {avg_score:.1f}/10"
                )

        # 质量分布
        print(f"\n📊 质量评分分布:")
        score_ranges = [(0, 3), (3, 5), (5, 7), (7, 9), (9, 11)]
        for low, high in score_ranges:
            count = len([a for a in self.assets if low <= a.quality_score < high])
            percentage = (count / total_assets) * 100 if total_assets > 0 else 0
            print(f"  {low}-{high-1}分: {count}个 ({percentage:.1f}%)")

        # 标签统计
        print(f"\n🏷️  热门标签:")
        tag_counts = {}
        for asset in self.assets:
            for tag in asset.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {tag}: {count}次")

    def export_summary(self, output_file: str = None):
        """导出资产摘要报告"""
        if output_file is None:
            output_file = self.data_dir / "athena_assets_summary.md"

        # 选择展示资产
        showcase_assets = self.select_showcase_assets()

        with open(output_file, "w", encoding="utf-8") as f:
            f.write("# Athena IP形象图像资产摘要\n\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"总资产数: {len(self.assets)}\n")
            f.write(f"展示资产数: {len(showcase_assets)}\n\n")

            f.write("## 按变体分类\n\n")
            for variant_name in self.variants_metadata.keys():
                variant_assets = self.get_assets_by_variant(variant_name)
                if not variant_assets:
                    continue

                f.write(f"### {variant_name}\n\n")
                f.write(f"- **资产数**: {len(variant_assets)}\n")

                # 最佳资产
                best_asset = max(variant_assets, key=lambda x: x.quality_score)
                f.write(
                    f"- **最佳资产**: {best_asset.id} (质量: {best_asset.quality_score:.1f}/10)\n"
                )

                # 展示资产
                showcase = [a for a in showcase_assets if a.variant_name == variant_name]
                if showcase:
                    asset = showcase[0]
                    f.write(f"- **展示资产**: {asset.id}\n")
                    f.write(f"  - URL: {asset.image_url[:100]}...\n")
                    f.write(f"  - 提示词: {asset.prompt_preview}\n")
                    f.write(f"  - 标签: {', '.join(asset.tags)}\n")

                f.write("\n")

            f.write("## 资产详情\n\n")
            f.write("| ID | 变体 | 质量评分 | URL预览 | 生成时间 |\n")
            f.write("|----|------|----------|---------|----------|\n")

            for asset in sorted(self.assets, key=lambda x: (x.variant_index, -x.quality_score)):
                url_preview = (
                    asset.image_url[:50] + "..." if len(asset.image_url) > 50 else asset.image_url
                )
                f.write(
                    f"| {asset.id} | {asset.variant_name} | {asset.quality_score:.1f} | {url_preview} | {asset.generation_time[:10]} |\n"
                )

        print(f"📄 导出摘要到: {output_file}")


def main():
    """主函数"""
    print("🎯 Athena图像资产管理")
    print("=" * 60)

    try:
        # 创建管理器
        manager = AthenaImageAssetManager()

        # 分析现有资产
        manager.analyze_assets()

        # 导出摘要
        manager.export_summary()

        # 如果用户提供了生成数据，可以添加到这里
        # 示例：手动添加资产
        # manager.add_asset_from_generation(
        #     variant_name="核心形象-硅基共生",
        #     prompt="硅基共生主题的AI女神Athena...",
        #     image_url="https://p3-flow-imagex-sign.byteimg.com/...",
        #     notes="测试添加"
        # )

        print("\n" + "=" * 60)
        print("📊 资产管理完成")
        print(f"   总资产数: {len(manager.assets)}")
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"\n❌ 管理出错: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
