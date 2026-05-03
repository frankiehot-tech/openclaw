"""
Task to Target - 任务目标映射

将自然语言任务转换为 UI 目标规格
支持多种任务类型的解析和目标定位
"""

import logging
import re

from .ui_elements import TargetSpec

logger = logging.getLogger(__name__)


# 任务模式定义
# 格式: (正则模式, 目标类型, 目标文本, 意图)
TASK_PATTERNS = [
    # 返回任务
    (r"返回[^\w]*上一[级页]", "back_button", "返回", "tap_target"),
    (r"返回[^\w]*", "back_button", "返回", "tap_target"),
    (r"back", "back_button", "返回", "tap_target"),
    # 搜索任务
    (r"点击[^\w]*搜索", "search_box", "搜索", "tap_target"),
    (r"搜索", "search_box", "搜索", "tap_target"),
    (r"search", "search_box", "搜索", "tap_target"),
    # 打开设置
    (r"打开[^\w]*设置", "list_item", "设置", "tap_target"),
    (r"进入[^\w]*设置", "list_item", "设置", "tap_target"),
    (r"设置", "list_item", "设置", "tap_target"),
    (r"settings", "list_item", "设置", "tap_target"),
    # 打开浏览器
    (r"打开[^\w]*浏览器", "icon_button", "浏览器", "tap_target"),
    (r"进入[^\w]*浏览器", "icon_button", "浏览器", "tap_target"),
    (r"浏览器", "icon_button", "浏览器", "tap_target"),
    (r"browser", "icon_button", "浏览器", "tap_target"),
    (r"chrome", "icon_button", "浏览器", "tap_target"),
    # Wi-Fi
    (r"打开[^\w]*Wi-?Fi", "list_item", "Wi-Fi", "tap_target"),
    (r"进入[^\w]*Wi-?Fi", "list_item", "Wi-Fi", "tap_target"),
    (r"Wi-?Fi", "list_item", "Wi-Fi", "tap_target"),
    (r"无线", "list_item", "Wi-Fi", "tap_target"),
    (r"wlan", "list_item", "Wi-Fi", "tap_target"),
    # 蓝牙
    (r"打开[^\w]*蓝牙", "list_item", "蓝牙", "tap_target"),
    (r"进入[^\w]*蓝牙", "list_item", "蓝牙", "tap_target"),
    (r"蓝牙", "list_item", "蓝牙", "tap_target"),
    (r"bluetooth", "list_item", "蓝牙", "tap_target"),
    # 显示
    (r"打开[^\w]*显示", "list_item", "显示", "tap_target"),
    (r"进入[^\w]*显示", "list_item", "显示", "tap_target"),
    (r"显示", "list_item", "显示", "tap_target"),
    (r"display", "list_item", "显示", "tap_target"),
    # 声音
    (r"打开[^\w]*声音", "list_item", "声音", "tap_target"),
    (r"进入[^\w]*声音", "list_item", "声音", "tap_target"),
    (r"声音", "list_item", "声音", "tap_target"),
    (r"音量", "list_item", "声音", "tap_target"),
    (r"sound", "list_item", "声音", "tap_target"),
    # 通知
    (r"打开[^\w]*通知", "list_item", "通知", "tap_target"),
    (r"进入[^\w]*通知", "list_item", "通知", "tap_target"),
    (r"通知", "list_item", "通知", "tap_target"),
    (r"notification", "list_item", "通知", "tap_target"),
    # 应用
    (r"打开[^\w]*应用", "list_item", "应用", "tap_target"),
    (r"进入[^\w]*应用", "list_item", "应用", "tap_target"),
    (r"应用", "list_item", "应用", "tap_target"),
    (r"application", "list_item", "应用", "tap_target"),
    (r"app", "list_item", "应用", "tap_target"),
    # 电池
    (r"打开[^\w]*电池", "list_item", "电池", "tap_target"),
    (r"进入[^\w]*电池", "list_item", "电池", "tap_target"),
    (r"电池", "list_item", "电池", "tap_target"),
    (r"battery", "list_item", "电池", "tap_target"),
    # 存储
    (r"打开[^\w]*存储", "list_item", "存储", "tap_target"),
    (r"进入[^\w]*存储", "list_item", "存储", "tap_target"),
    (r"存储", "list_item", "存储", "tap_target"),
    (r"storage", "list_item", "存储", "tap_target"),
    # 位置/定位
    (r"打开[^\w]*位置", "list_item", "位置", "tap_target"),
    (r"进入[^\w]*位置", "list_item", "位置", "tap_target"),
    (r"位置", "list_item", "位置", "tap_target"),
    (r"定位", "list_item", "位置", "tap_target"),
    (r"location", "list_item", "位置", "tap_target"),
    # 安全
    (r"打开[^\w]*安全", "list_item", "安全", "tap_target"),
    (r"进入[^\w]*安全", "list_item", "安全", "tap_target"),
    (r"安全", "list_item", "安全", "tap_target"),
    (r"security", "list_item", "安全", "tap_target"),
    # 隐私
    (r"打开[^\w]*隐私", "list_item", "隐私", "tap_target"),
    (r"进入[^\w]*隐私", "list_item", "隐私", "tap_target"),
    (r"隐私", "list_item", "隐私", "tap_target"),
    (r"privacy", "list_item", "隐私", "tap_target"),
    # 账户
    (r"打开[^\w]*账户", "list_item", "账户", "tap_target"),
    (r"进入[^\w]*账户", "list_item", "账户", "tap_target"),
    (r"账户", "list_item", "账户", "tap_target"),
    (r"account", "list_item", "账户", "tap_target"),
    # 语言
    (r"打开[^\w]*语言", "list_item", "语言", "tap_target"),
    (r"进入[^\w]*语言", "list_item", "语言", "tap_target"),
    (r"语言", "list_item", "语言", "tap_target"),
    (r"language", "list_item", "语言", "tap_target"),
    # 日期时间
    (r"打开[^\w]*日期", "list_item", "日期", "tap_target"),
    (r"进入[^\w]*日期", "list_item", "日期", "tap_target"),
    (r"日期", "list_item", "日期", "tap_target"),
    (r"date", "list_item", "日期", "tap_target"),
    # 关于手机
    (r"打开[^\w]*关于", "list_item", "关于手机", "tap_target"),
    (r"进入[^\w]*关于", "list_item", "关于手机", "tap_target"),
    (r"关于手机", "list_item", "关于手机", "tap_target"),
    (r"about", "list_item", "关于手机", "tap_target"),
    # 开发者选项
    (r"打开[^\w]*开发者", "list_item", "开发者选项", "tap_target"),
    (r"进入[^\w]*开发者", "list_item", "开发者选项", "tap_target"),
    (r"开发者选项", "list_item", "开发者选项", "tap_target"),
    (r"developer", "list_item", "开发者选项", "tap_target"),
    # 壁纸
    (r"打开[^\w]*壁纸", "list_item", "壁纸", "tap_target"),
    (r"进入[^\w]*壁纸", "list_item", "壁纸", "tap_target"),
    (r"壁纸", "list_item", "壁纸", "tap_target"),
    (r"wallpaper", "list_item", "壁纸", "tap_target"),
    # 飞行模式
    (r"打开[^\w]*飞行模式", "toggle", "飞行模式", "tap_target"),
    (r"飞行模式", "toggle", "飞行模式", "tap_target"),
    (r"airplane", "toggle", "飞行模式", "tap_target"),
    # NFC
    (r"打开[^\w]*NFC", "toggle", "NFC", "tap_target"),
    (r"NFC", "toggle", "NFC", "tap_target"),
    # 热点
    (r"打开[^\w]*热点", "list_item", "热点", "tap_target"),
    (r"热点", "list_item", "热点", "tap_target"),
    (r"hotspot", "list_item", "热点", "tap_target"),
    # 截图
    (r"截图", "button", "截图", "tap_target"),
    (r"screenshot", "button", "截图", "tap_target"),
    # 关闭
    (r"关闭", "icon_button", "关闭", "tap_target"),
    (r"close", "icon_button", "关闭", "tap_target"),
    # 菜单
    (r"菜单", "icon_button", "菜单", "tap_target"),
    (r"menu", "icon_button", "菜单", "tap_target"),
    # 更多
    (r"更多", "icon_button", "更多", "tap_target"),
    (r"more", "icon_button", "更多", "tap_target"),
    # 刷新
    (r"刷新", "icon_button", "刷新", "tap_target"),
    (r"refresh", "icon_button", "刷新", "tap_target"),
    # 分享
    (r"分享", "icon_button", "分享", "tap_target"),
    (r"share", "icon_button", "分享", "tap_target"),
]


def parse_task(task: str) -> TargetSpec:
    """
    解析任务文本，生成目标规格

    Args:
        task: 任务文本，如"点击搜索"、"返回上一级"、"打开设置"

    Returns:
        TargetSpec 实例
    """
    task_lower = task.lower().strip()

    # 尝试匹配预定义模式
    for pattern, target_type, target_text, intent in TASK_PATTERNS:
        if re.search(pattern, task_lower):
            logger.info(
                f"任务解析: '{task}' -> type={target_type}, text={target_text}, intent={intent}"
            )

            return TargetSpec(
                intent=intent,
                target_type=target_type,
                target_text=target_text,
                preferred_sources=["hybrid", "layout", "ocr", "icon_heuristic"],
                fallback_to_model=True,
                metadata={"original_task": task, "pattern": pattern},
            )

    # 默认：通用点击任务
    logger.info(f"任务解析: '{task}' -> 默认通用任务")

    return TargetSpec(
        intent="tap_target",
        target_type="unknown",
        target_text=task,
        fallback_to_model=True,
        metadata={"original_task": task, "pattern": "default"},
    )


def parse_tasks(tasks: list[str]) -> list[TargetSpec]:
    """
    批量解析任务

    Args:
        tasks: 任务列表

    Returns:
        TargetSpec 列表
    """
    return [parse_task(task) for task in tasks]


def get_common_tasks() -> dict[str, str]:
    """
    获取常见任务模板

    Returns:
        任务到描述的映射
    """
    return {
        "打开设置": "打开系统设置页面",
        "打开浏览器": "打开浏览器应用",
        "打开 Wi-Fi": "打开 Wi-Fi 设置",
        "打开蓝牙": "打开蓝牙设置",
        "打开显示": "打开显示设置",
        "打开声音": "打开声音设置",
        "打开通知": "打开通知设置",
        "打开位置": "打开位置/定位设置",
        "打开电池": "打开电池设置",
        "打开存储": "打开存储设置",
        "打开安全": "打开安全设置",
        "打开隐私": "打开隐私设置",
        "打开飞行模式": "切换飞行模式",
        "返回上一级": "返回上一页面",
        "点击搜索": "点击搜索框",
        "截图": "截取当前屏幕",
    }


def is_low_risk_task(task: str) -> bool:
    """
    判断是否为低风险任务

    低风险任务包括：
    - 查看/打开设置类页面
    - 点击搜索
    - 返回
    - 截图

    Args:
        task: 任务文本

    Returns:
        是否为低风险任务
    """
    low_risk_patterns = [
        r"打开[^\w]*(设置|浏览器|Wi-?Fi|蓝牙|显示|声音|通知|位置|电池|存储|安全|隐私|应用)",
        r"进入[^\w]*(设置|浏览器|Wi-?Fi|蓝牙|显示|声音|通知|位置|电池|存储|安全|隐私|应用)",
        r"返回[^\w]*",
        r"点击[^\w]*搜索",
        r"搜索",
        r"截图",
        r"screenshot",
    ]

    task_lower = task.lower()

    return any(re.search(pattern, task_lower) for pattern in low_risk_patterns)


def get_task_category(task: str) -> str:
    """
    获取任务类别

    Args:
        task: 任务文本

    Returns:
        任务类别
    """
    task_lower = task.lower()

    if re.search(r"返回|back", task_lower):
        return "navigation"

    if re.search(r"打开|进入|settings", task_lower):
        return "open_settings"

    if re.search(r"点击|tap", task_lower):
        return "tap"

    if re.search(r"输入|input|type", task_lower):
        return "input"

    if re.search(r"滑动|swipe", task_lower):
        return "swipe"

    if re.search(r"截图|screenshot", task_lower):
        return "utility"

    return "unknown"


if __name__ == "__main__":
    # 测试代码
    print("=== Task to Target 测试 ===")

    test_tasks = [
        "打开设置",
        "打开浏览器",
        "返回上一级",
        "点击搜索",
        "打开 Wi-Fi",
        "打开蓝牙",
        "截图",
        "进入显示设置",
    ]

    print("\n任务解析结果:")
    for task in test_tasks:
        spec = parse_task(task)
        print(f"\n  任务: {task}")
        print(f"    -> 类型: {spec.target_type}")
        print(f"    -> 文本: {spec.target_text}")
        print(f"    -> 意图: {spec.intent}")
        print(f"    -> 低风险: {is_low_risk_task(task)}")
        print(f"    -> 类别: {get_task_category(task)}")

    print("\n\n常见任务模板:")
    common = get_common_tasks()
    for task, desc in common.items():
        print(f"  {task}: {desc}")
