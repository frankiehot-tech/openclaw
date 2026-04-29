"""
UI Elements - 统一 UI 元素结构定义

定义所有 UI 元素的统一数据结构，用于 OCR、Layout、Icon Heuristic 等模块的输出统一格式
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class UIElementType(Enum):
    """UI 元素类型枚举"""

    SEARCH_BOX = "search_box"
    BUTTON = "button"
    ICON_BUTTON = "icon_button"
    LIST_ITEM = "list_item"
    BACK_BUTTON = "back_button"
    TAB_BAR = "tab_bar"
    INPUT_FIELD = "input_field"
    TOGGLE = "toggle"
    TEXT = "text"
    UNKNOWN = "unknown"


class ElementSource(Enum):
    """元素来源枚举"""

    OCR = "ocr"
    LAYOUT = "layout"
    ICON_HEURISTIC = "icon_heuristic"
    HYBRID = "hybrid"
    MODEL = "model"


@dataclass
class UIElement:
    """
    统一 UI 元素结构

    Attributes:
        element_type: 元素类型 (search_box|button|icon_button|list_item|back_button|tab_bar|input_field|toggle)
        bbox: 边界框 [x1, y1, x2, y2]
        center: 中心点 [cx, cy]
        confidence: 置信度 0.0-1.0
        source: 来源 (ocr|layout|icon_heuristic|hybrid|model)
        label: 标签文本
        clickable: 是否可点击
        metadata: 额外元数据
    """

    element_type: UIElementType
    bbox: List[float]  # [x1, y1, x2, y2]
    center: List[float]  # [cx, cy]
    confidence: float
    source: ElementSource
    label: str = ""
    clickable: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """验证数据有效性"""
        if not isinstance(self.bbox, list) or len(self.bbox) != 4:
            raise ValueError(f"bbox must be [x1, y1, x2, y2], got {self.bbox}")
        if not isinstance(self.center, list) or len(self.center) != 2:
            raise ValueError(f"center must be [cx, cy], got {self.center}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be 0.0-1.0, got {self.confidence}")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "element_type": self.element_type.value,
            "bbox": self.bbox,
            "center": self.center,
            "confidence": self.confidence,
            "source": self.source.value,
            "label": self.label,
            "clickable": self.clickable,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UIElement":
        """从字典创建"""
        element_type = UIElementType(data.get("element_type", "unknown"))
        source = ElementSource(data.get("source", "model"))

        return cls(
            element_type=element_type,
            bbox=data.get("bbox", [0, 0, 0, 0]),
            center=data.get("center", [0, 0]),
            confidence=data.get("confidence", 0.0),
            source=source,
            label=data.get("label", ""),
            clickable=data.get("clickable", True),
            metadata=data.get("metadata", {}),
        )


@dataclass
class TargetSpec:
    """
    目标规格 - 从任务到 UI 元素的映射

    Attributes:
        intent: 意图 (tap_target|input_text|swipe|back)
        target_type: 目标类型
        target_text: 目标文本
        preferred_sources: 优先来源列表
        fallback_to_model: 是否回退到模型
    """

    intent: str
    target_type: str
    target_text: str = ""
    preferred_sources: List[str] = field(
        default_factory=lambda: ["hybrid", "layout", "ocr", "icon_heuristic"]
    )
    fallback_to_model: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "intent": self.intent,
            "target_type": self.target_type,
            "target_text": self.target_text,
            "preferred_sources": self.preferred_sources,
            "fallback_to_model": self.fallback_to_model,
            "metadata": self.metadata,
        }

    @classmethod
    def from_task(cls, task: str) -> "TargetSpec":
        """
        从任务文本解析目标规格

        Args:
            task: 任务文本，如"点击搜索"、"返回上一级"、"打开 Wi-Fi 页面"

        Returns:
            TargetSpec 实例
        """
        task_lower = task.lower()

        # 返回上一级
        if "返回" in task and "上一级" in task or "返回" in task and "back" in task_lower:
            return cls(
                intent="tap_target",
                target_type="back_button",
                target_text="返回",
                preferred_sources=["hybrid", "layout", "icon_heuristic", "ocr"],
            )

        # 点击搜索
        if "搜索" in task or "search" in task_lower:
            return cls(
                intent="tap_target",
                target_type="search_box",
                target_text="搜索",
                preferred_sources=["hybrid", "layout", "ocr", "icon_heuristic"],
            )

        # 打开 Wi-Fi 页面
        if "wi-fi" in task_lower or "wifi" in task_lower or "无线" in task:
            return cls(
                intent="tap_target",
                target_type="list_item",
                target_text="Wi-Fi",
                preferred_sources=["hybrid", "ocr", "layout"],
            )

        # 打开蓝牙页面
        if "蓝牙" in task or "bluetooth" in task_lower:
            return cls(
                intent="tap_target",
                target_type="list_item",
                target_text="蓝牙",
                preferred_sources=["hybrid", "ocr", "layout"],
            )

        # 打开设置
        if "设置" in task or "settings" in task_lower:
            return cls(
                intent="tap_target",
                target_type="list_item",
                target_text="设置",
                preferred_sources=["hybrid", "ocr", "layout"],
            )

        # 打开浏览器
        if "浏览器" in task or "browser" in task_lower or "chrome" in task_lower:
            return cls(
                intent="tap_target",
                target_type="icon_button",
                target_text="浏览器",
                preferred_sources=["hybrid", "icon_heuristic", "ocr"],
            )

        # 默认：通用点击
        return cls(
            intent="tap_target", target_type="unknown", target_text=task, fallback_to_model=True
        )


def create_ui_element(
    element_type: str,
    bbox: List[float],
    confidence: float,
    source: str,
    label: str = "",
    clickable: bool = True,
    metadata: Optional[Dict[str, Any]] = None,
) -> UIElement:
    """
    便捷函数：创建 UI 元素

    Args:
        element_type: 元素类型字符串
        bbox: 边界框
        confidence: 置信度
        source: 来源字符串
        label: 标签
        clickable: 是否可点击
        metadata: 额外数据

    Returns:
        UIElement 实例
    """
    # 计算中心点
    center = [(bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2]

    return UIElement(
        element_type=UIElementType(element_type),
        bbox=bbox,
        center=center,
        confidence=confidence,
        source=ElementSource(source),
        label=label,
        clickable=clickable,
        metadata=metadata or {},
    )


def merge_elements(elements: List[UIElement], iou_threshold: float = 0.5) -> List[UIElement]:
    """
    合并重复的 UI 元素（基于 IOU）

    Args:
        elements: UI 元素列表
        iou_threshold: IOU 阈值，超过则合并

    Returns:
        去重后的元素列表
    """
    if not elements:
        return []

    # 按置信度排序
    sorted_elements = sorted(elements, key=lambda x: x.confidence, reverse=True)
    result = []

    for elem in sorted_elements:
        merged = False
        for existing in result:
            if _compute_iou(elem.bbox, existing.bbox) > iou_threshold:
                # 保留置信度高的
                if elem.confidence > existing.confidence:
                    result.remove(existing)
                    result.append(elem)
                merged = True
                break
        if not merged:
            result.append(elem)

    return result


def _compute_iou(bbox1: List[float], bbox2: List[float]) -> float:
    """计算两个边界框的 IOU"""
    x1 = max(bbox1[0], bbox2[0])
    y1 = max(bbox1[1], bbox2[1])
    x2 = min(bbox1[2], bbox2[2])
    y2 = min(bbox1[3], bbox2[3])

    if x2 <= x1 or y2 <= y1:
        return 0.0

    intersection = (x2 - x1) * (y2 - y1)
    area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
    area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
    union = area1 + area2 - intersection

    return intersection / union if union > 0 else 0.0


def sort_elements_by_priority(
    elements: List[UIElement], target_spec: Optional[TargetSpec] = None
) -> List[UIElement]:
    """
    按优先级排序 UI 元素

    Args:
        elements: UI 元素列表
        target_spec: 目标规格（用于相关性排序）

    Returns:
        排序后的元素列表
    """
    if not elements:
        return []

    def priority_score(elem: UIElement) -> float:
        score = elem.confidence

        # 来源优先级
        source_priority = {
            ElementSource.HYBRID: 1.0,
            ElementSource.LAYOUT: 0.9,
            ElementSource.OCR: 0.8,
            ElementSource.ICON_HEURISTIC: 0.7,
            ElementSource.MODEL: 0.5,
        }
        score += source_priority.get(elem.source, 0.0) * 0.2

        # 目标类型匹配加分
        if target_spec and elem.element_type.value == target_spec.target_type:
            score += 0.3

        # 文本匹配加分
        if target_spec and target_spec.target_text:
            if target_spec.target_text.lower() in elem.label.lower():
                score += 0.2

        return score

    return sorted(elements, key=priority_score, reverse=True)
