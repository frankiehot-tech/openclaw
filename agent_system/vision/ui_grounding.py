"""
UI Grounding - UI 元素定位

基于 OCR 结果定位目标 UI 元素
"""

import logging
import os
import sys
from dataclasses import dataclass

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from vision.ocr_engine import OCRResult

# 配置日志
logger = logging.getLogger(__name__)

# 日志文件
VISION_LOG = "os.path.join(os.path.dirname(os.path.abspath(__file__)), '../logs/vision.log')"

# 配置日志
file_handler = logging.FileHandler(VISION_LOG)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(file_handler)

# 安全配置
EDGE_MARGIN_RATIO = 0.05  # 边缘区域比例 5%


@dataclass
class TextTarget:
    """文本目标"""

    matched: bool
    text: str
    bbox: list[int]  # [x1, y1, x2, y2]
    center: tuple[int, int]  # (cx, cy)
    confidence: float
    match_type: str  # "exact" | "contains" | "fuzzy"

    def to_dict(self) -> dict:
        return {
            "matched": self.matched,
            "text": self.text,
            "bbox": self.bbox,
            "center": self.center,
            "confidence": self.confidence,
            "match_type": self.match_type,
        }


class UIGrounding:
    """UI Grounding 引擎"""

    def __init__(self, screen_size: tuple[int, int] | None = None):
        """
        初始化 UI Grounding

        Args:
            screen_size: 屏幕尺寸 (width, height)
        """
        self.screen_size = screen_size or (1080, 2640)  # 默认 Z Flip3 尺寸
        logger.info(f"UIGrounding 初始化: screen_size={self.screen_size}")

    def find_text_target(
        self, ocr_blocks: list[OCRResult], target_text: str, match_threshold: float = 0.75
    ) -> TextTarget | None:
        """
        在 OCR 结果中查找目标文本

        Args:
            ocr_blocks: OCR 结果列表
            target_text: 目标文本
            match_threshold: 匹配阈值

        Returns:
            匹配的 TextTarget 或 None
        """
        if not ocr_blocks or not target_text:
            return None

        target_lower = target_text.lower().strip()
        candidates = []

        for block in ocr_blocks:
            text_lower = block.text.lower().strip()

            # 精确匹配
            if text_lower == target_lower:
                candidates.append({"block": block, "match_type": "exact", "score": 1.0})
            # 包含匹配
            elif target_lower in text_lower or text_lower in target_lower:
                # 计算包含程度
                if target_lower in text_lower:
                    score = len(target_lower) / len(text_lower)
                else:
                    score = len(text_lower) / len(target_lower)

                if score >= match_threshold:
                    candidates.append({"block": block, "match_type": "contains", "score": score})
            else:
                # 简单模糊匹配 - 检查共同字符
                common_chars = set(text_lower) & set(target_lower)
                if common_chars:
                    score = len(common_chars) / max(len(set(text_lower)), len(set(target_lower)))
                    if score >= match_threshold:
                        candidates.append(
                            {
                                "block": block,
                                "match_type": "fuzzy",
                                "score": score * block.confidence,
                            }
                        )

        if not candidates:
            logger.info(f"未找到目标文本: {target_text}")
            return None

        # 按分数排序，选择最高分
        candidates.sort(key=lambda x: x["score"], reverse=True)
        best = candidates[0]
        block = best["block"]

        # 计算中心点
        center = self.bbox_to_tap_point(block.bbox)

        if center is None:
            logger.warning(f"目标文本 {block.text} 的中心点不安全")
            return None

        logger.info(
            f"找到目标文本: {block.text} (type={best['match_type']}, "
            f"score={best['score']:.2f}, center={center})"
        )

        return TextTarget(
            matched=True,
            text=block.text,
            bbox=block.bbox,
            center=center,
            confidence=block.confidence * best["score"],
            match_type=best["match_type"],
        )

    def bbox_to_tap_point(
        self, bbox: list[int], safe_margin: bool = True
    ) -> tuple[int, int] | None:
        """
        将文本框转换为可点击中心点

        Args:
            bbox: [x1, y1, x2, y2]
            safe_margin: 是否应用安全边距

        Returns:
            (x, y) 中心点坐标，或 None（如果中心点不安全）
        """
        x1, y1, x2, y2 = bbox

        # 计算中心点
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2

        if not safe_margin:
            return (cx, cy)

        # 安全校验 - 检查是否在边缘危险区域
        width, height = self.screen_size
        margin_x = int(width * EDGE_MARGIN_RATIO)
        margin_y = int(height * EDGE_MARGIN_RATIO)

        # 如果中心点在边缘区域，尝试偏移到安全区域
        if cx < margin_x:
            cx = margin_x + 10
        elif cx > width - margin_x:
            cx = width - margin_x - 10

        if cy < margin_y:
            cy = margin_y + 10
        elif cy > height - margin_y:
            cy = height - margin_y - 10

        return (cx, cy)

    def rank_candidates(
        self, candidates: list[TextTarget], prefer_center: bool = True
    ) -> list[TextTarget]:
        """
        对多个候选目标排序

        Args:
            candidates: 候选目标列表
            prefer_center: 是否优先选择靠近屏幕中心的候选

        Returns:
            排序后的候选列表
        """
        if not candidates:
            return []

        width, height = self.screen_size
        center_x, center_y = width // 2, height // 2

        def calc_score(target: TextTarget) -> float:
            score = target.confidence

            if prefer_center:
                # 计算到中心的距离
                cx, cy = target.center
                dist = ((cx - center_x) ** 2 + (cy - center_y) ** 2) ** 0.5
                max_dist = ((width**2 + height**2) ** 0.5) / 2

                # 距离越近分数越高
                dist_score = 1 - (dist / max_dist)
                score = score * 0.7 + dist_score * 0.3

            # 精确匹配优先
            if target.match_type == "exact":
                score *= 1.2

            return score

        ranked = sorted(candidates, key=calc_score, reverse=True)

        logger.info(f"候选目标排序完成: {len(ranked)} 个候选")
        for i, t in enumerate(ranked[:3]):
            logger.info(f"  {i+1}. {t.text} (score={calc_score(t):.2f})")

        return ranked

    def find_multiple_targets(
        self, ocr_blocks: list[OCRResult], target_texts: list[str], max_candidates: int = 5
    ) -> list[TextTarget]:
        """
        查找多个目标文本

        Args:
            ocr_blocks: OCR 结果列表
            target_texts: 目标文本列表
            max_candidates: 最大候选数量

        Returns:
            匹配的 TextTarget 列表
        """
        results = []

        for target_text in target_texts:
            target = self.find_text_target(ocr_blocks, target_text)
            if target:
                results.append(target)

            if len(results) >= max_candidates:
                break

        return results


# 全局单例
_ui_grounding: UIGrounding | None = None


def get_ui_grounding(screen_size: tuple[int, int] | None = None) -> UIGrounding:
    """获取全局 UI Grounding 引擎"""
    global _ui_grounding

    if _ui_grounding is None:
        _ui_grounding = UIGrounding(screen_size=screen_size)

    return _ui_grounding


def reset_ui_grounding():
    """重置 UI Grounding"""
    global _ui_grounding
    _ui_grounding = None


if __name__ == "__main__":
    # 测试代码
    print("=== UI Grounding 测试 ===")

    grounding = UIGrounding(screen_size=(1080, 2640))

    # 模拟 OCR 结果
    ocr_blocks = [
        OCRResult(text="设置", bbox=[450, 1200, 630, 1260], confidence=0.95),
        OCRResult(text="搜索", bbox=[200, 300, 400, 400], confidence=0.90),
        OCRResult(text="浏览器", bbox=[300, 800, 500, 900], confidence=0.88),
        OCRResult(text="返回", bbox=[50, 100, 150, 180], confidence=0.92),
    ]

    # 测试查找目标
    print("\n1. 查找 '设置':")
    target = grounding.find_text_target(ocr_blocks, "设置")
    if target:
        print(f"   找到: {target.text}, center={target.center}, type={target.match_type}")

    print("\n2. 查找 '浏览器':")
    target = grounding.find_text_target(ocr_blocks, "浏览器")
    if target:
        print(f"   找到: {target.text}, center={target.center}, type={target.match_type}")

    print("\n3. 查找不存在的目标:")
    target = grounding.find_text_target(ocr_blocks, "不存在的文本")
    print(f"   结果: {target}")

    # 测试多目标查找
    print("\n4. 多目标查找:")
    targets = grounding.find_multiple_targets(ocr_blocks, ["设置", "搜索", "浏览器", "返回"])
    for t in targets:
        print(f"   - {t.text}: {t.center}")
