"""
Screen Analyzer - 屏幕分析器

整合 OCR、Layout Detection、Icon Heuristics 和 UI Grounding，提供完整的屏幕分析能力
支持混合模式：OCR + Layout + Icon Heuristic → Hybrid Grounding
"""

import hashlib
import logging
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from vision.icon_heuristics import detect_all_icon_elements
from vision.layout_detector import detect_all_layout_elements
from vision.ocr_engine import OCRResult, get_ocr_engine
from vision.ui_elements import (
    ElementSource,
    TargetSpec,
    UIElement,
    UIElementType,
    merge_elements,
    sort_elements_by_priority,
)
from vision.ui_grounding import TextTarget, get_ui_grounding

# MiniCPM 路由（阶段 13 新增）
try:
    from vision.vision_router import is_minicpm_available, route_vision_analysis

    MINICPM_IMPORTED = True
except ImportError:
    MINICPM_IMPORTED = False

    def route_vision_analysis(*args, **kwargs):
        raise NotImplementedError("vision_router 未安装")

    def is_minicpm_available():
        return False


# 配置日志
logger = logging.getLogger(__name__)

# 日志文件
VISION_LOG = "os.path.join(os.path.dirname(os.path.abspath(__file__)), '../logs/vision.log')"

# 配置日志
file_handler = logging.FileHandler(VISION_LOG)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(file_handler)


# 配置项
USE_LAYOUT = os.getenv("VISION_USE_LAYOUT", "true").lower() == "true"
USE_ICON_HEURISTICS = os.getenv("VISION_USE_ICON_HEURISTICS", "true").lower() == "true"
LAYOUT_CONFIDENCE_THRESHOLD = float(os.getenv("VISION_LAYOUT_CONFIDENCE_THRESHOLD", "0.70"))
ICON_CONFIDENCE_THRESHOLD = float(os.getenv("VISION_ICON_CONFIDENCE_THRESHOLD", "0.65"))
HYBRID_PRIORITY = os.getenv(
    "VISION_HYBRID_PRIORITY", "hybrid,layout,ocr,icon_heuristic,model"
).split(",")

# MiniCPM 配置（阶段 13 新增）
USE_MINICPM = os.getenv("VISION_USE_MINICPM", "false").lower() == "true"
MINICPM_ENABLED_TASKS = {
    "点击搜索",
    "搜索",
    "search",
    "打开Wi-Fi",
    "打开 Wi-Fi",
    "打开Wi-Fi页面",
    "打开 Wi-Fi 页面",
    "打开蓝牙",
    "打开 蓝牙",
    "打开蓝牙页面",
    "打开 蓝牙 页面",
}


@dataclass
class ScreenAnalysis:
    """屏幕分析结果"""

    image_path: str
    screen_hash: str
    ocr_blocks: List[Dict] = field(default_factory=list)
    ocr_blocks_count: int = 0
    ocr_top_texts: List[str] = field(default_factory=list)
    grounding_target: Optional[Dict] = None
    grounding_candidates: List[Dict] = field(default_factory=list)
    target_found: bool = False
    suggested_actions: List[Dict] = field(default_factory=list)
    screen_summary: str = ""
    # 新增：UI 结构理解相关字段
    ui_elements: List[Dict] = field(default_factory=list)
    ui_elements_count: int = 0
    ui_summary: str = ""
    recommended_targets: List[Dict] = field(default_factory=list)
    hybrid_used: bool = False

    def to_dict(self) -> Dict:
        return {
            "image_path": self.image_path,
            "screen_hash": self.screen_hash,
            "ocr_blocks_count": self.ocr_blocks_count,
            "ocr_top_texts": self.ocr_top_texts,
            "target_found": self.target_found,
            "grounding_target": self.grounding_target,
            "grounding_candidates": self.grounding_candidates,
            "suggested_actions": self.suggested_actions,
            "screen_summary": self.screen_summary,
            # 新增字段
            "ui_elements_count": self.ui_elements_count,
            "ui_elements": self.ui_elements,
            "ui_summary": self.ui_summary,
            "recommended_targets": self.recommended_targets,
            "hybrid_used": self.hybrid_used,
        }


class ScreenAnalyzer:
    """屏幕分析器"""

    def __init__(
        self,
        ocr_provider: str = "mock",
        screen_size: Optional[Tuple[int, int]] = None,
        match_threshold: float = 0.75,
        max_candidates: int = 5,
    ):
        """
        初始化屏幕分析器

        Args:
            ocr_provider: OCR provider 类型
            screen_size: 屏幕尺寸
            match_threshold: 文本匹配阈值
            max_candidates: 最大候选数量
        """
        self.ocr_engine = get_ocr_engine(provider=ocr_provider)
        self.ui_grounding = get_ui_grounding(screen_size=screen_size)
        self.match_threshold = match_threshold
        self.max_candidates = max_candidates

        logger.info(
            f"ScreenAnalyzer 初始化: provider={ocr_provider}, "
            f"screen_size={screen_size}, threshold={match_threshold}"
        )

    def compute_screen_hash(self, image_path: str) -> str:
        """
        计算屏幕截图的 hash

        Args:
            image_path: 图片路径

        Returns:
            MD5 hash 字符串
        """
        try:
            with open(image_path, "rb") as f:
                # 只读取前 100KB 以加快速度
                data = f.read(100 * 1024)
                return hashlib.md5(data).hexdigest()[:16]
        except Exception as e:
            logger.warning(f"计算屏幕 hash 失败: {e}")
            return "unknown"

    def analyze_screen(
        self, image_path: str, expected_targets: Optional[List[str]] = None
    ) -> ScreenAnalysis:
        """
        分析屏幕

        Args:
            image_path: 截图路径
            expected_targets: 期望的目标文本列表

        Returns:
            ScreenAnalysis 分析结果
        """
        logger.info(f"开始分析屏幕: {image_path}")

        # 计算屏幕 hash
        screen_hash = self.compute_screen_hash(image_path)

        # 初始化结果
        analysis = ScreenAnalysis(image_path=image_path, screen_hash=screen_hash)

        # 1. OCR 提取
        ocr_results = self.ocr_engine.extract_text(image_path)

        if not ocr_results:
            logger.warning("OCR 未提取到任何文本")
            analysis.screen_summary = "OCR 未提取到文本"
            return analysis

        # 填充 OCR 结果
        analysis.ocr_blocks = [r.to_dict() for r in ocr_results]
        analysis.ocr_blocks_count = len(ocr_results)

        # 提取高置信度文本
        high_confidence = [r for r in ocr_results if r.confidence >= 0.8]
        analysis.ocr_top_texts = [r.text for r in high_confidence[:10]]

        logger.info(f"OCR 提取到 {len(ocr_results)} 个文本块")

        # 2. 如果有目标文本，进行 grounding
        if expected_targets:
            candidates = []

            for target_text in expected_targets:
                target = self.ui_grounding.find_text_target(
                    ocr_results, target_text, match_threshold=self.match_threshold
                )

                if target:
                    candidates.append(target.to_dict())

                    # 记录第一个匹配的目标
                    if analysis.grounding_target is None:
                        analysis.grounding_target = target.to_dict()
                        analysis.target_found = True

            analysis.grounding_candidates = candidates[: self.max_candidates]

            if analysis.target_found:
                logger.info(
                    f"目标文本已找到: {analysis.grounding_target['text']}, "
                    f"center={analysis.grounding_target['center']}"
                )
            else:
                logger.info(f"未找到目标文本: {expected_targets}")

        # 3. 生成建议动作
        analysis.suggested_actions = self._generate_suggested_actions(ocr_results, expected_targets)

        # 4. 生成屏幕摘要
        analysis.screen_summary = self._generate_summary(analysis)

        logger.info(f"屏幕分析完成: {analysis.screen_summary}")

        return analysis

    def _generate_suggested_actions(
        self, ocr_results: List[OCRResult], expected_targets: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        生成建议动作

        Args:
            ocr_results: OCR 结果
            expected_targets: 期望目标

        Returns:
            建议动作列表
        """
        actions = []

        # 基于 OCR 结果生成建议
        for block in ocr_results[:5]:  # 最多 5 个
            if block.confidence >= 0.8:
                center = self.ui_grounding.bbox_to_tap_point(block.bbox)
                if center:
                    actions.append(
                        {
                            "action": "tap",
                            "params": {"x": center[0], "y": center[1]},
                            "reason": f"点击 '{block.text}'",
                            "confidence": block.confidence,
                            "source": "ocr_grounding",
                        }
                    )

        return actions

    def _generate_summary(self, analysis: ScreenAnalysis) -> str:
        """
        生成屏幕摘要

        Args:
            analysis: 分析结果

        Returns:
            摘要字符串
        """
        parts = []

        # 文本数量
        parts.append(f"文本块: {analysis.ocr_blocks_count}")

        # 高置信文本
        if analysis.ocr_top_texts:
            texts = ", ".join(analysis.ocr_top_texts[:5])
            parts.append(f"高置信: {texts}")

        # 目标状态
        if analysis.target_found:
            target = analysis.grounding_target
            parts.append(f"目标 '{target['text']}' 已定位 (置信: {target['confidence']:.2f})")
        elif analysis.grounding_candidates:
            parts.append(f"候选目标: {len(analysis.grounding_candidates)} 个")

        return "; ".join(parts)

    def detect_ui_elements(
        self,
        image_path: str,
        ocr_blocks: Optional[List[Dict]] = None,
        screen_size: Optional[Tuple[int, int]] = None,
    ) -> List[UIElement]:
        """
        检测 UI 元素 - 整合 OCR、Layout、Icon Heuristic

        Args:
            image_path: 截图路径
            ocr_blocks: OCR 识别结果列表
            screen_size: 屏幕尺寸

        Returns:
            UIElement 列表
        """
        all_elements: List[UIElement] = []

        # 转换 OCR 结果格式
        ocr_list = ocr_blocks if ocr_blocks else []

        # 1. Layout 检测
        if USE_LAYOUT:
            try:
                layout_elements = detect_all_layout_elements(image_path, ocr_list, screen_size)
                all_elements.extend(layout_elements)
                logger.info(f"Layout 检测到 {len(layout_elements)} 个元素")
            except Exception as e:
                logger.warning(f"Layout 检测失败: {e}")

        # 2. Icon Heuristic 检测
        if USE_ICON_HEURISTICS:
            try:
                icon_elements = detect_all_icon_elements(image_path, ocr_list, screen_size)
                all_elements.extend(icon_elements)
                logger.info(f"Icon Heuristic 检测到 {len(icon_elements)} 个元素")
            except Exception as e:
                logger.warning(f"Icon Heuristic 检测失败: {e}")

        # 3. 基于 OCR 创建 UI 元素
        if ocr_blocks:
            for block in ocr_blocks:
                text = block.get("text", "")
                bbox = block.get("bbox", [])
                conf = block.get("confidence", 0.5)

                if not bbox or len(bbox) != 4:
                    continue

                # 创建 OCR 元素
                elem = UIElement(
                    element_type=UIElementType.TEXT,
                    bbox=bbox,
                    center=[(bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2],
                    confidence=conf,
                    source=ElementSource.OCR,
                    label=text,
                    clickable=True,
                    metadata={"ocr_text": text},
                )
                all_elements.append(elem)

        # 4. 合并重复元素
        merged = merge_elements(all_elements, iou_threshold=0.5)

        logger.info(f"UI 元素检测完成: 原始 {len(all_elements)} → 合并后 {len(merged)}")

        return merged

    def analyze_screen_with_layout(
        self,
        image_path: str,
        expected_targets: Optional[List[str]] = None,
        target_spec: Optional[TargetSpec] = None,
    ) -> ScreenAnalysis:
        """
        增强的屏幕分析 - 包含 UI 结构理解

        Args:
            image_path: 截图路径
            expected_targets: 期望的目标文本列表
            target_spec: 目标规格

        Returns:
            ScreenAnalysis 分析结果
        """
        logger.info(f"开始增强分析屏幕: {image_path}")

        # 计算屏幕 hash
        screen_hash = self.compute_screen_hash(image_path)

        # 初始化结果
        analysis = ScreenAnalysis(image_path=image_path, screen_hash=screen_hash)

        # 1. OCR 提取
        ocr_results = self.ocr_engine.extract_text(image_path)

        if not ocr_results:
            logger.warning("OCR 未提取到任何文本")
            analysis.screen_summary = "OCR 未提取到文本"
            return analysis

        # 填充 OCR 结果
        analysis.ocr_blocks = [r.to_dict() for r in ocr_results]
        analysis.ocr_blocks_count = len(ocr_results)

        # 提取高置信度文本
        high_confidence = [r for r in ocr_results if r.confidence >= 0.8]
        analysis.ocr_top_texts = [r.text for r in high_confidence[:10]]

        logger.info(f"OCR 提取到 {len(ocr_results)} 个文本块")

        # 2. UI 元素检测 (Layout + Icon Heuristic)
        ui_elements = self.detect_ui_elements(
            image_path, analysis.ocr_blocks, self.ui_grounding.screen_size
        )

        # 转换为字典
        analysis.ui_elements = [e.to_dict() for e in ui_elements]
        analysis.ui_elements_count = len(ui_elements)

        # 3. 排序和推荐目标
        if target_spec:
            sorted_elements = sort_elements_by_priority(ui_elements, target_spec)
            analysis.recommended_targets = [e.to_dict() for e in sorted_elements[:5]]

            # 尝试找到匹配的目标
            for elem in sorted_elements:
                if elem.element_type.value == target_spec.target_type:
                    # 找到匹配类型的目标
                    if elem.confidence >= LAYOUT_CONFIDENCE_THRESHOLD:
                        analysis.grounding_target = elem.to_dict()
                        analysis.target_found = True
                        analysis.hybrid_used = True
                        logger.info(
                            f"Hybrid Grounding 命中: {elem.element_type.value} "
                            f"'{elem.label}' (conf={elem.confidence:.2f}, source={elem.source.value})"
                        )
                        break
                elif target_spec.target_text and target_spec.target_text in elem.label:
                    # 文本匹配
                    if elem.confidence >= LAYOUT_CONFIDENCE_THRESHOLD:
                        analysis.grounding_target = elem.to_dict()
                        analysis.target_found = True
                        analysis.hybrid_used = True
                        logger.info(
                            f"Hybrid Grounding 命中: {elem.element_type.value} "
                            f"'{elem.label}' (conf={elem.confidence:.2f}, source={elem.source.value})"
                        )
                        break

        # 4. 如果没有找到目标，回退到传统 OCR grounding
        if not analysis.target_found and expected_targets:
            for target_text in expected_targets:
                target = self.ui_grounding.find_text_target(
                    ocr_results, target_text, match_threshold=self.match_threshold
                )

                if target:
                    analysis.grounding_target = target.to_dict()
                    analysis.target_found = True
                    logger.info(f"OCR Grounding 命中: {target.text}")
                    break

        # 5. 生成建议动作
        analysis.suggested_actions = self._generate_suggested_actions_with_ui(
            ui_elements, target_spec
        )

        # 6. 生成 UI 摘要
        analysis.ui_summary = self._generate_ui_summary(analysis)

        # 7. 生成屏幕摘要
        analysis.screen_summary = self._generate_summary(analysis)

        logger.info(f"增强屏幕分析完成: {analysis.screen_summary}")

        return analysis

    def _generate_suggested_actions_with_ui(
        self, ui_elements: List[UIElement], target_spec: Optional[TargetSpec] = None
    ) -> List[Dict]:
        """
        生成建议动作 - 基于 UI 元素

        Args:
            ui_elements: UI 元素列表
            target_spec: 目标规格

        Returns:
            建议动作列表
        """
        actions = []

        # 优先使用高置信 UI 元素
        sorted_elements = sort_elements_by_priority(ui_elements, target_spec)

        for elem in sorted_elements[:5]:
            if not elem.clickable:
                continue

            # 来源映射
            source_map = {
                ElementSource.HYBRID: "hybrid_grounding",
                ElementSource.LAYOUT: "layout_grounding",
                ElementSource.OCR: "ocr_grounding",
                ElementSource.ICON_HEURISTIC: "icon_heuristic",
                ElementSource.MODEL: "model_inference",
            }

            actions.append(
                {
                    "action": "tap",
                    "params": {"x": elem.center[0], "y": elem.center[1]},
                    "reason": f"点击 '{elem.label}' ({elem.element_type.value})",
                    "confidence": elem.confidence,
                    "source": source_map.get(elem.source, "unknown"),
                    "element_type": elem.element_type.value,
                }
            )

        return actions

    def _generate_ui_summary(self, analysis: ScreenAnalysis) -> str:
        """
        生成 UI 结构摘要

        Args:
            analysis: 分析结果

        Returns:
            摘要字符串
        """
        if not analysis.ui_elements:
            return "无 UI 元素"

        # 统计各类型元素
        type_counts: Dict[str, int] = {}
        source_counts: Dict[str, int] = {}

        for elem in analysis.ui_elements:
            etype = elem.get("element_type", "unknown")
            source = elem.get("source", "unknown")

            type_counts[etype] = type_counts.get(etype, 0) + 1
            source_counts[source] = source_counts.get(source, 0) + 1

        parts = []
        parts.append(f"UI 元素: {analysis.ui_elements_count}")

        if type_counts:
            types = ", ".join([f"{k}({v})" for k, v in type_counts.items()])
            parts.append(f"类型: {types}")

        if source_counts:
            sources = ", ".join([f"{k}({v})" for k, v in source_counts.items()])
            parts.append(f"来源: {sources}")

        if analysis.hybrid_used:
            parts.append("使用混合识别")

        return "; ".join(parts)

    def quick_check_target(self, image_path: str, target_text: str) -> Optional[TextTarget]:
        """
        快速检查目标文本是否存在

        Args:
            image_path: 截图路径
            target_text: 目标文本

        Returns:
            TextTarget 或 None
        """
        ocr_results = self.ocr_engine.extract_text(image_path)

        if not ocr_results:
            return None

        return self.ui_grounding.find_text_target(
            ocr_results, target_text, match_threshold=self.match_threshold
        )

    def quick_check_target_with_layout(
        self, image_path: str, target_spec: TargetSpec
    ) -> Optional[UIElement]:
        """
        快速检查目标 - 使用 UI 结构理解

        Args:
            image_path: 截图路径
            target_spec: 目标规格

        Returns:
            UIElement 或 None
        """
        # OCR 提取
        ocr_results = self.ocr_engine.extract_text(image_path)
        ocr_blocks = [r.to_dict() for r in ocr_results] if ocr_results else []

        # UI 元素检测
        ui_elements = self.detect_ui_elements(image_path, ocr_blocks, self.ui_grounding.screen_size)

        # 排序并查找匹配
        sorted_elements = sort_elements_by_priority(ui_elements, target_spec)

        for elem in sorted_elements:
            # 类型匹配
            if elem.element_type.value == target_spec.target_type:
                if elem.confidence >= LAYOUT_CONFIDENCE_THRESHOLD:
                    return elem

            # 文本匹配
            if target_spec.target_text and target_spec.target_text in elem.label:
                if elem.confidence >= LAYOUT_CONFIDENCE_THRESHOLD:
                    return elem

        return None

    def analyze_with_minicpm(
        self,
        image_path: str,
        task: str,
        expected_targets: Optional[List[str]] = None,
        target_spec: Optional[TargetSpec] = None,
        ocr_result: Optional[List[Dict]] = None,
        state_result: Optional[Dict] = None,
    ) -> Dict:
        """
        使用 MiniCPM 进行增强分析（阶段 13 新增）

        流程：截图 → OCR → state detection → 若 OCR/规则足够 → 直接执行
              否则调用 vision_router → MiniCPM → 若 MiniCPM 返回高置信 target → 转成 grounding/action
              否则继续原有 model inference

        Args:
            image_path: 截图路径
            task: 任务描述
            expected_targets: 期望目标文本
            target_spec: 目标规格
            ocr_result: OCR 结果（可选）
            state_result: 状态检测结果（可选）

        Returns:
            包含 MiniCPM 路由结果的字典
        """
        # 检查 MiniCPM 是否启用
        if not USE_MINICPM:
            logger.info("MiniCPM 未启用，使用原有流程")
            return {"use_minicpm": False, "reason": "MiniCPM 未启用", "source": "ocr_grounding"}

        # 检查任务是否在白名单
        if task not in MINICPM_ENABLED_TASKS:
            logger.info(f"任务 '{task}' 不在 MiniCPM 启用列表中")
            return {
                "use_minicpm": False,
                "reason": f"任务不在 MiniCPM 启用列表中",
                "source": "ocr_grounding",
            }

        # 检查 MiniCPM 是否可用
        if MINICPM_IMPORTED and is_minicpm_available():
            try:
                # 调用 vision_router 进行路由决策
                result = route_vision_analysis(
                    image_path=image_path,
                    task=task,
                    ocr_result=ocr_result,
                    state_result=state_result,
                )

                logger.info(
                    f"MiniCPM 路由结果: use_minicpm={result.get('use_minicpm')}, source={result.get('source')}"
                )
                return result

            except Exception as e:
                logger.warning(f"MiniCPM 调用失败: {e}")
                return {
                    "use_minicpm": False,
                    "reason": f"MiniCPM 调用失败: {e}",
                    "source": "ocr_grounding",
                }
        else:
            logger.warning("MiniCPM 不可用，使用原有流程")
            return {"use_minicpm": False, "reason": "MiniCPM 不可用", "source": "ocr_grounding"}


# 全局单例
_screen_analyzer: Optional[ScreenAnalyzer] = None


def get_screen_analyzer(
    ocr_provider: str = "mock", screen_size: Optional[Tuple[int, int]] = None
) -> ScreenAnalyzer:
    """获取全局屏幕分析器"""
    global _screen_analyzer

    if _screen_analyzer is None:
        _screen_analyzer = ScreenAnalyzer(ocr_provider=ocr_provider, screen_size=screen_size)

    return _screen_analyzer


def reset_screen_analyzer():
    """重置屏幕分析器"""
    global _screen_analyzer
    _screen_analyzer = None


if __name__ == "__main__":
    # 测试代码
    print("=== Screen Analyzer 测试 ===")

    analyzer = ScreenAnalyzer(ocr_provider="mock", screen_size=(1080, 2640))

    # 测试分析
    print("\n1. 屏幕分析测试:")
    analysis = analyzer.analyze_screen(
        "/fake/path.png", expected_targets=["设置", "搜索", "浏览器"]
    )

    print(f"   文本块数量: {analysis.ocr_blocks_count}")
    print(f"   高置信文本: {analysis.ocr_top_texts}")
    print(f"   目标找到: {analysis.target_found}")
    print(f"   摘要: {analysis.screen_summary}")

    if analysis.grounding_target:
        print(f"   目标位置: {analysis.grounding_target['center']}")

    # 测试快速检查
    print("\n2. 快速目标检查:")
    target = analyzer.quick_check_target("/fake/path.png", "设置")
    if target:
        print(f"   找到: {target.text}, center={target.center}")
    else:
        print("   未找到")
