"""
Layout Detector - 布局级规则识别

基于屏幕区域、OCR 文本位置和几何启发式识别 UI 元素
不依赖复杂 CV 库，使用轻量级规则
"""

import logging
from typing import Any

from .ui_elements import UIElement, create_ui_element

logger = logging.getLogger(__name__)

# 默认屏幕尺寸 (Z Flip3)
DEFAULT_SCREEN_WIDTH = 1080
DEFAULT_SCREEN_HEIGHT = 2640


def detect_search_boxes(
    image_path: str,
    ocr_blocks: list[dict[str, Any]] | None = None,
    screen_size: tuple[int, int] | None = None,
) -> list[UIElement]:
    """
    识别搜索框

    识别依据：
    - 顶部区域的长条矩形
    - 带放大镜图标或"搜索"占位文本
    - 常见搜索框比例（宽度较大、高度较小）
    - OCR 文本靠近长条区域

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

    # 搜索框通常在顶部区域 (0-20% 高度)
    top_region_end = int(height * 0.20)

    # 检查 OCR 结果中是否有"搜索"相关文本
    if ocr_blocks:
        for block in ocr_blocks:
            text = block.get("text", "")
            bbox = block.get("bbox", [])

            if not bbox or len(bbox) != 4:
                continue

            # 检查是否是搜索相关文本
            search_keywords = ["搜索", "search", "搜索或输入网址", "输入搜索内容"]
            if any(kw in text for kw in search_keywords) and bbox[1] < top_region_end:
                    # 扩展搜索框区域
                    search_bbox = [
                        max(0, bbox[0] - 50),
                        max(0, bbox[1] - 20),
                        min(width, bbox[2] + 50),
                        min(top_region_end, bbox[3] + 20),
                    ]

                    element = create_ui_element(
                        element_type="search_box",
                        bbox=search_bbox,
                        confidence=0.85,
                        source="layout",
                        label=text,
                        clickable=True,
                        metadata={"ocr_text": text, "original_bbox": bbox},
                    )
                    elements.append(element)
                    logger.info(f"Layout: 检测到搜索框 '{text}' at {search_bbox}")

    # 如果没有找到，但有"搜索"文本在顶部，也创建一个候选
    if not elements and ocr_blocks:
        for block in ocr_blocks:
            text = block.get("text", "")
            if "搜索" in text and len(text) <= 10:  # 短文本更可能是搜索框标签
                bbox = block.get("bbox", [])
                if bbox and bbox[1] < top_region_end:
                    # 基于 OCR 位置创建搜索框候选
                    search_bbox = [50, 20, width - 50, 120]
                    element = create_ui_element(
                        element_type="search_box",
                        bbox=search_bbox,
                        confidence=0.60,
                        source="layout",
                        label="搜索框",
                        clickable=True,
                        metadata={"inferred_from": text},
                    )
                    elements.append(element)
                    logger.info(f"Layout: 推断搜索框 at {search_bbox}")

    return elements


def detect_back_buttons(
    image_path: str,
    ocr_blocks: list[dict[str, Any]] | None = None,
    screen_size: tuple[int, int] | None = None,
) -> list[UIElement]:
    """
    识别返回按钮

    识别依据：
    - 顶部左侧区域
    - 左箭头、返回文案、常见返回热区

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

            # 检查是否是返回相关文本
            back_keywords = ["返回", "back", "←"]
            if any(kw in text for kw in back_keywords) and bbox[0] < left_region_end and bbox[1] < top_region_end:
                    # 扩展返回按钮区域
                    back_bbox = [
                        max(0, bbox[0] - 30),
                        max(0, bbox[1] - 10),
                        min(left_region_end + 50, bbox[2] + 20),
                        min(top_region_end + 30, bbox[3] + 10),
                    ]

                    element = create_ui_element(
                        element_type="back_button",
                        bbox=back_bbox,
                        confidence=0.90,
                        source="layout",
                        label=text,
                        clickable=True,
                        metadata={"ocr_text": text, "original_bbox": bbox},
                    )
                    elements.append(element)
                    logger.info(f"Layout: 检测到返回按钮 '{text}' at {back_bbox}")

    # 如果没有找到，基于位置创建默认返回按钮候选
    if not elements:
        # 常见返回按钮位置：顶部左侧
        back_bbox = [10, 80, 120, 180]
        element = create_ui_element(
            element_type="back_button",
            bbox=back_bbox,
            confidence=0.50,
            source="layout",
            label="返回",
            clickable=True,
            metadata={"inferred": "top_left_corner"},
        )
        elements.append(element)
        logger.info(f"Layout: 推断返回按钮 at {back_bbox}")

    return elements


def detect_bottom_nav(
    image_path: str,
    ocr_blocks: list[dict[str, Any]] | None = None,
    screen_size: tuple[int, int] | None = None,
) -> list[UIElement]:
    """
    识别底部导航栏

    识别依据：
    - 底部固定区域
    - 多个均匀分布的点击目标
    - 常见"首页/搜索/我的/设置"等文案

    Args:
        image_path: 截图路径
        ocr_blocks: OCR 识别结果列表
        screen_size: 屏幕尺寸 (width, height)

    Returns:
        UIElement 列表
    """
    elements = []

    screen_size[0] if screen_size else DEFAULT_SCREEN_WIDTH
    height = screen_size[1] if screen_size else DEFAULT_SCREEN_HEIGHT

    # 底部导航栏通常在底部 10% 区域
    bottom_region_start = int(height * 0.90)

    # 检查 OCR 结果中是否有底部导航相关文本
    if ocr_blocks:
        nav_keywords = ["首页", "home", "搜索", "发现", "消息", "我的", "profile", "设置", "tab"]
        found_nav_items = []

        for block in ocr_blocks:
            text = block.get("text", "")
            bbox = block.get("bbox", [])

            if not bbox or len(bbox) != 4:
                continue

            # 检查是否在底部区域
            if bbox[1] > bottom_region_start and any(kw in text.lower() for kw in [k.lower() for k in nav_keywords]):
                    found_nav_items.append((text, bbox))

        # 如果找到多个底部导航项，创建一个导航栏元素
        if len(found_nav_items) >= 2:
            # 计算导航栏边界
            min_x = min(bbox[0] for _, bbox in found_nav_items)
            max_x = max(bbox[2] for _, bbox in found_nav_items)
            min_y = min(bbox[1] for _, bbox in found_nav_items)
            max(bbox[3] for _, bbox in found_nav_items)

            nav_bbox = [min_x - 20, min_y - 10, max_x + 20, height - 10]

            element = create_ui_element(
                element_type="tab_bar",
                bbox=nav_bbox,
                confidence=0.80,
                source="layout",
                label="底部导航栏",
                clickable=False,  # 导航栏本身不可点击，是容器
                metadata={"nav_items": [text for text, _ in found_nav_items]},
            )
            elements.append(element)
            logger.info(f"Layout: 检测到底部导航栏，包含 {len(found_nav_items)} 个项目")

    return elements


def detect_list_items(
    image_path: str,
    ocr_blocks: list[dict[str, Any]] | None = None,
    screen_size: tuple[int, int] | None = None,
) -> list[UIElement]:
    """
    识别列表项

    识别依据：
    - 垂直排列文本块
    - 文本 + 右箭头/开关的结构
    - "Wi-Fi""蓝牙""显示"等设置页条目

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

    if not ocr_blocks:
        return elements

    # 列表项通常在中间区域，排除顶部和底部
    top_exclude = int(height * 0.15)
    bottom_exclude = int(height * 0.85)

    # 常见设置列表项关键词
    list_item_keywords = [
        "Wi-Fi",
        "无线",
        "WLAN",
        "wifi",
        "蓝牙",
        "Bluetooth",
        "bluetooth",
        "显示",
        "显示",
        "display",
        "声音",
        "音量",
        "sound",
        "通知",
        "notification",
        "应用",
        "application",
        "电池",
        "battery",
        "存储",
        "storage",
        "网络",
        "network",
        "连接",
        "connection",
        "辅助功能",
        "accessibility",
        "关于手机",
        "about",
        "开发者选项",
        "developer",
        "软件更新",
        "update",
        "语言",
        "language",
        "日期",
        "date",
        "时间",
        "time",
        "账户",
        "account",
        "隐私",
        "privacy",
        "安全",
        "security",
        "位置",
        "location",
        "壁纸",
        "wallpaper",
        "主题",
        "theme",
        "字体",
        "font",
        "手势",
        "gesture",
        "导航",
        "navigation",
        "快捷方式",
        "shortcut",
        "备份",
        "backup",
        "重置",
        "reset",
        "账户",
        "account",
    ]

    # 按 Y 坐标排序 OCR 块
    sorted_blocks = sorted(ocr_blocks, key=lambda b: b.get("bbox", [0, 0, 0, 0])[1])

    for block in sorted_blocks:
        text = block.get("text", "")
        bbox = block.get("bbox", [])

        if not bbox or len(bbox) != 4:
            continue

        # 检查是否在有效区域内
        if bbox[1] < top_exclude or bbox[1] > bottom_exclude:
            continue

        # 检查是否是列表项关键词
        matched_keyword = None
        for keyword in list_item_keywords:
            if keyword.lower() in text.lower():
                matched_keyword = keyword
                break

        if matched_keyword:
            # 创建列表项元素
            bbox[2] - bbox[0]
            bbox[3] - bbox[1]

            # 扩展为完整的列表项区域
            list_bbox = [0, max(0, bbox[1] - 5), width, min(height, bbox[3] + 5)]

            element = create_ui_element(
                element_type="list_item",
                bbox=list_bbox,
                confidence=0.85,
                source="layout",
                label=text,
                clickable=True,
                metadata={"ocr_text": text, "original_bbox": bbox, "keyword": matched_keyword},
            )
            elements.append(element)
            logger.info(f"Layout: 检测到列表项 '{text}' at {list_bbox}")

    return elements


def detect_toggles(
    image_path: str,
    ocr_blocks: list[dict[str, Any]] | None = None,
    screen_size: tuple[int, int] | None = None,
) -> list[UIElement]:
    """
    识别开关控件

    识别依据：
    - 列表项附近可能有开关
    - OCR 文本 + 右侧开关区域

    Args:
        image_path: 截图路径
        ocr_blocks: OCR 识别结果列表
        screen_size: 屏幕尺寸 (width, height)

    Returns:
        UIElement 列表
    """
    elements = []

    width = screen_size[0] if screen_size else DEFAULT_SCREEN_WIDTH
    screen_size[1] if screen_size else DEFAULT_SCREEN_HEIGHT

    if not ocr_blocks:
        return elements

    # 开关通常在屏幕右侧 80-95% 区域
    toggle_x_start = int(width * 0.80)

    # 查找可能的开关位置（基于已知的列表项）
    for block in ocr_blocks:
        text = block.get("text", "")
        bbox = block.get("bbox", [])

        if not bbox or len(bbox) != 4:
            continue

        # 检查是否是设置类文本（可能带开关）
        toggle_keywords = ["Wi-Fi", "蓝牙", "NFC", "定位", "飞行模式", "同步"]
        if any(kw in text for kw in toggle_keywords):
            # 在文本右侧创建开关候选
            toggle_bbox = [toggle_x_start, bbox[1], width - 20, bbox[3]]

            element = create_ui_element(
                element_type="toggle",
                bbox=toggle_bbox,
                confidence=0.70,
                source="layout",
                label=f"{text} 开关",
                clickable=True,
                metadata={"associated_text": text},
            )
            elements.append(element)
            logger.info(f"Layout: 检测到开关 '{text}' at {toggle_bbox}")

    return elements


def detect_all_layout_elements(
    image_path: str,
    ocr_blocks: list[dict[str, Any]] | None = None,
    screen_size: tuple[int, int] | None = None,
) -> list[UIElement]:
    """
    检测所有布局元素

    Args:
        image_path: 截图路径
        ocr_blocks: OCR 识别结果列表
        screen_size: 屏幕尺寸 (width, height)

    Returns:
        所有检测到的 UI 元素列表
    """
    all_elements = []

    # 检测各类元素
    all_elements.extend(detect_search_boxes(image_path, ocr_blocks, screen_size))
    all_elements.extend(detect_back_buttons(image_path, ocr_blocks, screen_size))
    all_elements.extend(detect_bottom_nav(image_path, ocr_blocks, screen_size))
    all_elements.extend(detect_list_items(image_path, ocr_blocks, screen_size))
    all_elements.extend(detect_toggles(image_path, ocr_blocks, screen_size))

    logger.info(f"Layout: 共检测到 {len(all_elements)} 个布局元素")

    return all_elements


if __name__ == "__main__":
    # 测试代码
    print("=== Layout Detector 测试 ===")

    # 模拟 OCR 结果
    test_ocr_blocks = [
        {"text": "设置", "bbox": [100, 50, 200, 100], "confidence": 0.99},
        {"text": "搜索", "bbox": [200, 30, 500, 80], "confidence": 0.95},
        {"text": "Wi-Fi", "bbox": [50, 300, 200, 350], "confidence": 0.90},
        {"text": "蓝牙", "bbox": [50, 400, 200, 450], "confidence": 0.88},
        {"text": "返回", "bbox": [20, 80, 80, 130], "confidence": 0.85},
    ]

    # 测试检测
    elements = detect_all_layout_elements("test.png", test_ocr_blocks, (1080, 2640))

    print(f"\n检测到 {len(elements)} 个元素:")
    for elem in elements:
        print(
            f"  - {elem.element_type.value}: {elem.label} (conf={elem.confidence:.2f}, source={elem.source.value})"
        )
