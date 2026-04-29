"""
Icon Heuristics - 图标级启发式识别

基于位置先验、附近 OCR 文本和常见图标热区识别 UI 元素
不依赖复杂 CV 库，使用轻量级启发式规则
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from .ui_elements import ElementSource, UIElement, UIElementType, create_ui_element

logger = logging.getLogger(__name__)

# 默认屏幕尺寸 (Z Flip3)
DEFAULT_SCREEN_WIDTH = 1080
DEFAULT_SCREEN_HEIGHT = 2640

# 常见图标热区定义
# 格式: (x1, y1, x2, y2, icon_name, keywords)
COMMON_ICON_HOTSPOTS = [
    # 搜索图标 - 顶部居中或居右
    ([500, 10, 800, 100], "search_icon", ["搜索", "search", "放大镜"]),
    # 返回图标 - 顶部左侧
    ([0, 50, 120, 180], "back_icon", ["返回", "back", "←"]),
    # 关闭图标 - 顶部右侧
    ([950, 50, 1080, 180], "close_icon", ["关闭", "close", "×", "X"]),
    # 菜单图标 - 顶部左侧
    ([0, 50, 100, 180], "menu_icon", ["菜单", "menu", "☰"]),
    # 设置图标 - 顶部右侧或列表中
    ([900, 50, 1080, 180], "settings_icon", ["设置", "settings", "⚙"]),
    # 分享图标
    ([800, 50, 950, 180], "share_icon", ["分享", "share", "↗"]),
    # 更多选项
    ([900, 50, 1080, 180], "more_icon", ["更多", "more", "..."]),
    # 刷新图标
    ([900, 50, 1080, 180], "refresh_icon", ["刷新", "refresh", "↻"]),
    # 收藏/书签
    ([800, 50, 950, 180], "bookmark_icon", ["收藏", "bookmark", "★"]),
    # 通知图标
    ([900, 50, 1080, 180], "notification_icon", ["通知", "notification", "🔔"]),
]


def detect_search_icon(
    image_path: str,
    ocr_blocks: Optional[List[Dict[str, Any]]] = None,
    screen_size: Optional[Tuple[int, int]] = None,
) -> List[UIElement]:
    """
    识别搜索图标

    识别依据：
    - 位置先验：顶部居中或居右
    - 附近 OCR 文本包含"搜索"关键词
    - 常见搜索图标热区

    Args:
        image_path: 截图路径
        ocr_blocks: OCR 识别结果列表
        screen_size: 屏幕尺寸 (width, height)

    Returns:
        UIElement 列表
    """
    elements = []

    width = screen_size[0] if screen_size else DEFAULT_SCREEN_WIDTH
    height = screen_size[1] if screen_size else DEFAULT_SCREEN_HEIGHT

    # 搜索框/图标通常在顶部 20% 区域
    top_region_end = int(height * 0.20)

    # 检查 OCR 结果中是否有"搜索"相关文本
    if ocr_blocks:
        for block in ocr_blocks:
            text = block.get("text", "")
            bbox = block.get("bbox", [])

            if not bbox or len(bbox) != 4:
                continue

            # 检查是否包含搜索关键词
            search_keywords = ["搜索", "search", "搜索或输入网址"]
            if any(kw in text for kw in search_keywords):
                # 检查是否在顶部区域
                if bbox[1] < top_region_end:
                    # 扩展为搜索框区域
                    search_bbox = [
                        max(0, bbox[0] - 100),
                        max(0, bbox[1] - 20),
                        min(width, bbox[2] + 100),
                        min(top_region_end, bbox[3] + 30),
                    ]

                    element = create_ui_element(
                        element_type="search_box",
                        bbox=search_bbox,
                        confidence=0.80,
                        source="icon_heuristic",
                        label="搜索框",
                        clickable=True,
                        metadata={"ocr_text": text, "original_bbox": bbox},
                    )
                    elements.append(element)
                    logger.info(f"Icon Heuristic: 检测到搜索框 '{text}' at {search_bbox}")

    # 如果没有找到，基于位置创建搜索图标候选
    if not elements:
        # 常见搜索框位置：顶部居中
        search_bbox = [100, 20, width - 100, 120]
        element = create_ui_element(
            element_type="search_box",
            bbox=search_bbox,
            confidence=0.55,
            source="icon_heuristic",
            label="搜索框",
            clickable=True,
            metadata={"inferred": "top_center_region"},
        )
        elements.append(element)
        logger.info(f"Icon Heuristic: 推断搜索框 at {search_bbox}")

    return elements


def detect_back_icon(
    image_path: str,
    ocr_blocks: Optional[List[Dict[str, Any]]] = None,
    screen_size: Optional[Tuple[int, int]] = None,
) -> List[UIElement]:
    """
    识别返回图标

    识别依据：
    - 位置先验：顶部左侧
    - 附近 OCR 文本包含"返回"关键词
    - 常见返回图标热区

    Args:
        image_path: 截图路径
        ocr_blocks: OCR 识别结果列表
        screen_size: 屏幕尺寸 (width, height)

    Returns:
        UIElement 列表
    """
    elements = []

    width = screen_size[0] if screen_size else DEFAULT_SCREEN_WIDTH
    height = screen_size[1] if screen_size else DEFAULT_SCREEN_HEIGHT

    # 返回按钮通常在顶部左侧 (0-15% 宽度, 0-15% 高度)
    left_region_end = int(width * 0.15)
    top_region_end = int(height * 0.15)

    # 检查 OCR 结果中是否有"返回"相关文本
    if ocr_blocks:
        for block in ocr_blocks:
            text = block.get("text", "")
            bbox = block.get("bbox", [])

            if not bbox or len(bbox) != 4:
                continue

            # 检查是否包含返回关键词
            back_keywords = ["返回", "back", "←"]
            if any(kw in text for kw in back_keywords):
                # 检查是否在左上角区域
                if bbox[0] < left_region_end and bbox[1] < top_region_end:
                    # 扩展为返回按钮区域
                    back_bbox = [
                        max(0, bbox[0] - 30),
                        max(0, bbox[1] - 10),
                        min(left_region_end + 50, bbox[2] + 30),
                        min(top_region_end + 30, bbox[3] + 10),
                    ]

                    element = create_ui_element(
                        element_type="back_button",
                        bbox=back_bbox,
                        confidence=0.90,
                        source="icon_heuristic",
                        label="返回",
                        clickable=True,
                        metadata={"ocr_text": text, "original_bbox": bbox},
                    )
                    elements.append(element)
                    logger.info(f"Icon Heuristic: 检测到返回按钮 '{text}' at {back_bbox}")

    # 如果没有找到，基于位置创建返回图标候选
    if not elements:
        # 常见返回按钮位置：顶部左侧
        back_bbox = [10, 80, 120, 180]
        element = create_ui_element(
            element_type="back_button",
            bbox=back_bbox,
            confidence=0.50,
            source="icon_heuristic",
            label="返回",
            clickable=True,
            metadata={"inferred": "top_left_corner"},
        )
        elements.append(element)
        logger.info(f"Icon Heuristic: 推断返回按钮 at {back_bbox}")

    return elements


def detect_settings_icon(
    image_path: str,
    ocr_blocks: Optional[List[Dict[str, Any]]] = None,
    screen_size: Optional[Tuple[int, int]] = None,
) -> List[UIElement]:
    """
    识别设置图标

    识别依据：
    - 位置先验：顶部右侧
    - 附近 OCR 文本包含"设置"关键词
    - 常见设置图标热区

    Args:
        image_path: 截图路径
        ocr_blocks: OCR 识别结果列表
        screen_size: 屏幕尺寸 (width, height)

    Returns:
        UIElement 列表
    """
    elements = []

    width = screen_size[0] if screen_size else DEFAULT_SCREEN_WIDTH
    height = screen_size[1] if screen_size else DEFAULT_SCREEN_HEIGHT

    # 设置图标通常在顶部右侧 (85-100% 宽度, 0-15% 高度)
    right_region_start = int(width * 0.85)
    top_region_end = int(height * 0.15)

    # 检查 OCR 结果中是否有"设置"相关文本
    if ocr_blocks:
        for block in ocr_blocks:
            text = block.get("text", "")
            bbox = block.get("bbox", [])

            if not bbox or len(bbox) != 4:
                continue

            # 检查是否包含设置关键词
            settings_keywords = ["设置", "settings", "⚙"]
            if any(kw in text for kw in settings_keywords):
                # 检查是否在顶部右侧区域
                if bbox[0] > right_region_start and bbox[1] < top_region_end:
                    # 扩展为设置按钮区域
                    settings_bbox = [
                        max(right_region_start - 30, bbox[0] - 20),
                        max(0, bbox[1] - 10),
                        min(width, bbox[2] + 20),
                        min(top_region_end + 30, bbox[3] + 10),
                    ]

                    element = create_ui_element(
                        element_type="icon_button",
                        bbox=settings_bbox,
                        confidence=0.85,
                        source="icon_heuristic",
                        label="设置",
                        clickable=True,
                        metadata={"ocr_text": text, "original_bbox": bbox},
                    )
                    elements.append(element)
                    logger.info(f"Icon Heuristic: 检测到设置按钮 '{text}' at {settings_bbox}")

    # 如果没有找到，基于位置创建设置图标候选
    if not elements:
        # 常见设置按钮位置：顶部右侧
        settings_bbox = [950, 80, 1080, 180]
        element = create_ui_element(
            element_type="icon_button",
            bbox=settings_bbox,
            confidence=0.45,
            source="icon_heuristic",
            label="设置",
            clickable=True,
            metadata={"inferred": "top_right_corner"},
        )
        elements.append(element)
        logger.info(f"Icon Heuristic: 推断设置按钮 at {settings_bbox}")

    return elements


def detect_close_icon(
    image_path: str,
    ocr_blocks: Optional[List[Dict[str, Any]]] = None,
    screen_size: Optional[Tuple[int, int]] = None,
) -> List[UIElement]:
    """
    识别关闭图标

    识别依据：
    - 位置先验：顶部右侧
    - 附近 OCR 文本包含"关闭"关键词
    - 常见关闭图标热区（×, X）

    Args:
        image_path: 截图路径
        ocr_blocks: OCR 识别结果列表
        screen_size: 屏幕尺寸 (width, height)

    Returns:
        UIElement 列表
    """
    elements = []

    width = screen_size[0] if screen_size else DEFAULT_SCREEN_WIDTH
    height = screen_size[1] if screen_size else DEFAULT_SCREEN_HEIGHT

    # 关闭按钮通常在顶部右侧 (90-100% 宽度, 0-10% 高度)
    right_region_start = int(width * 0.90)
    top_region_end = int(height * 0.10)

    # 检查 OCR 结果中是否有"关闭"相关文本
    if ocr_blocks:
        for block in ocr_blocks:
            text = block.get("text", "")
            bbox = block.get("bbox", [])

            if not bbox or len(bbox) != 4:
                continue

            # 检查是否包含关闭关键词
            close_keywords = ["关闭", "close", "×", "X"]
            if any(kw in text for kw in close_keywords):
                # 检查是否在顶部右侧区域
                if bbox[0] > right_region_start and bbox[1] < top_region_end:
                    close_bbox = [
                        max(right_region_start - 20, bbox[0] - 15),
                        max(0, bbox[1] - 10),
                        min(width, bbox[2] + 15),
                        min(top_region_end + 20, bbox[3] + 10),
                    ]

                    element = create_ui_element(
                        element_type="icon_button",
                        bbox=close_bbox,
                        confidence=0.85,
                        source="icon_heuristic",
                        label="关闭",
                        clickable=True,
                        metadata={"ocr_text": text, "original_bbox": bbox},
                    )
                    elements.append(element)
                    logger.info(f"Icon Heuristic: 检测到关闭按钮 '{text}' at {close_bbox}")

    return elements


def detect_menu_icon(
    image_path: str,
    ocr_blocks: Optional[List[Dict[str, Any]]] = None,
    screen_size: Optional[Tuple[int, int]] = None,
) -> List[UIElement]:
    """
    识别菜单图标

    识别依据：
    - 位置先验：顶部左侧
    - 附近 OCR 文本包含"菜单"关键词
    - 常见菜单图标热区（☰, 三条横线）

    Args:
        image_path: 截图路径
        ocr_blocks: OCR 识别结果列表
        screen_size: 屏幕尺寸 (width, height)

    Returns:
        UIElement 列表
    """
    elements = []

    width = screen_size[0] if screen_size else DEFAULT_SCREEN_WIDTH
    height = screen_size[1] if screen_size else DEFAULT_SCREEN_HEIGHT

    # 菜单按钮通常在顶部左侧 (0-10% 宽度, 0-10% 高度)
    left_region_end = int(width * 0.10)
    top_region_end = int(height * 0.10)

    # 检查 OCR 结果中是否有"菜单"相关文本
    if ocr_blocks:
        for block in ocr_blocks:
            text = block.get("text", "")
            bbox = block.get("bbox", [])

            if not bbox or len(bbox) != 4:
                continue

            # 检查是否包含菜单关键词
            menu_keywords = ["菜单", "menu", "☰"]
            if any(kw in text for kw in menu_keywords):
                # 检查是否在左上角区域
                if bbox[0] < left_region_end and bbox[1] < top_region_end:
                    menu_bbox = [
                        max(0, bbox[0] - 20),
                        max(0, bbox[1] - 10),
                        min(left_region_end + 40, bbox[2] + 20),
                        min(top_region_end + 20, bbox[3] + 10),
                    ]

                    element = create_ui_element(
                        element_type="icon_button",
                        bbox=menu_bbox,
                        confidence=0.85,
                        source="icon_heuristic",
                        label="菜单",
                        clickable=True,
                        metadata={"ocr_text": text, "original_bbox": bbox},
                    )
                    elements.append(element)
                    logger.info(f"Icon Heuristic: 检测到菜单按钮 '{text}' at {menu_bbox}")

    return elements


def detect_all_icon_elements(
    image_path: str,
    ocr_blocks: Optional[List[Dict[str, Any]]] = None,
    screen_size: Optional[Tuple[int, int]] = None,
) -> List[UIElement]:
    """
    检测所有图标元素

    Args:
        image_path: 截图路径
        ocr_blocks: OCR 识别结果列表
        screen_size: 屏幕尺寸 (width, height)

    Returns:
        所有检测到的 UI 元素列表
    """
    all_elements = []

    # 检测各类图标
    all_elements.extend(detect_search_icon(image_path, ocr_blocks, screen_size))
    all_elements.extend(detect_back_icon(image_path, ocr_blocks, screen_size))
    all_elements.extend(detect_settings_icon(image_path, ocr_blocks, screen_size))
    all_elements.extend(detect_close_icon(image_path, ocr_blocks, screen_size))
    all_elements.extend(detect_menu_icon(image_path, ocr_blocks, screen_size))

    logger.info(f"Icon Heuristic: 共检测到 {len(all_elements)} 个图标元素")

    return all_elements


if __name__ == "__main__":
    # 测试代码
    print("=== Icon Heuristics 测试 ===")

    # 模拟 OCR 结果
    test_ocr_blocks = [
        {"text": "设置", "bbox": [950, 80, 1050, 130], "confidence": 0.99},
        {"text": "搜索", "bbox": [300, 30, 500, 80], "confidence": 0.95},
        {"text": "返回", "bbox": [30, 80, 80, 130], "confidence": 0.90},
        {"text": "关闭", "bbox": [1000, 30, 1050, 80], "confidence": 0.85},
    ]

    # 测试检测
    elements = detect_all_icon_elements("test.png", test_ocr_blocks, (1080, 2640))

    print(f"\n检测到 {len(elements)} 个图标元素:")
    for elem in elements:
        print(
            f"  - {elem.element_type.value}: {elem.label} (conf={elem.confidence:.2f}, source={elem.source.value})"
        )
