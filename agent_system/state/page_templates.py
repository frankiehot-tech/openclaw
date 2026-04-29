"""
Page Templates - 页面模板库 (Phase 12)

定义每个页面状态的模板，用于精确识别
"""

from dataclasses import dataclass, field


@dataclass
class PageTemplate:
    """页面模板定义"""

    state: str
    required_keywords: list[str] = field(default_factory=list)  # 必须包含的关键词
    optional_keywords: list[str] = field(default_factory=list)  # 可选关键词
    negative_keywords: list[str] = field(default_factory=list)  # 负向关键词（出现则排除）
    ui_hints: list[str] = field(default_factory=list)  # UI 元素提示
    min_score: float = 0.65  # 最低得分阈值
    description: str = ""  # 描述

    def to_dict(self) -> dict:
        return {
            "state": self.state,
            "required_keywords": self.required_keywords,
            "optional_keywords": self.optional_keywords,
            "negative_keywords": self.negative_keywords,
            "ui_hints": self.ui_hints,
            "min_score": self.min_score,
            "description": self.description,
        }


# 页面模板库
PAGE_TEMPLATES: dict[str, PageTemplate] = {
    "home_screen": PageTemplate(
        state="home_screen",
        required_keywords=["主屏幕", "home", "桌面"],
        optional_keywords=[
            "抖音",
            "微信",
            "淘宝",
            "支付宝",
            "微博",
            "相机",
            "天气",
            "时钟",
            "文件管理",
            "应用",
            "设置",
            "Google",
            "文件夹",
            "小组件",
            "壁纸",
            "搜索",
            "更多",
            "通讯录",
            "短信",
            "电话",
            "音乐",
            "视频",
            "浏览器",
            "下载",
            "游戏",
            "计算器",
            "日历",
        ],
        negative_keywords=["设置", "Wi-Fi", "蓝牙", "搜索", "地址", "chrome"],
        ui_hints=["icon_grid", "bottom_nav", "dock_apps"],
        min_score=0.65,
        description="主屏幕：应用图标网格，底部应用栏",
    ),
    "settings_home": PageTemplate(
        state="settings_home",
        required_keywords=["设置", "settings"],
        optional_keywords=[
            "Wi-Fi",
            "WLAN",
            "蓝牙",
            "显示",
            "声音",
            "应用程序",
            "网络",
            "飞行模式",
            "移动网络",
            "连接",
            "通知",
            "应用",
            "存储",
            "电池",
            "安全",
            "关于",
            "更多连接",
        ],
        negative_keywords=["抖音", "微信", "淘宝", "浏览器"],
        ui_hints=["vertical_list", "list_item", "back_button"],
        min_score=0.65,
        description="设置首页：垂直列表项，右侧箭头",
    ),
    "settings_wifi": PageTemplate(
        state="settings_wifi",
        required_keywords=["Wi-Fi", "WLAN", "无线网络"],
        optional_keywords=[
            "网络",
            "开关",
            "已连接",
            "可用网络",
            "WPA",
            "WPA2",
            "密码",
            "显示密码",
            "高级",
            "代理",
            "IP",
            "网关",
        ],
        negative_keywords=["蓝牙", "显示", "声音", "应用"],
        ui_hints=["toggle", "list_item", "switch"],
        min_score=0.65,
        description="Wi-Fi 设置页：开关、网络列表",
    ),
    "settings_bluetooth": PageTemplate(
        state="settings_bluetooth",
        required_keywords=["蓝牙", "bluetooth"],
        optional_keywords=[
            "设备",
            "可见性",
            "已连接",
            "可用设备",
            "已配对",
            "扫描",
            "重命名",
            "接收文件",
            "关闭",
        ],
        negative_keywords=["Wi-Fi", "显示", "声音", "应用"],
        ui_hints=["toggle", "list_item", "switch"],
        min_score=0.65,
        description="蓝牙设置页：开关、设备列表",
    ),
    "browser_home": PageTemplate(
        state="browser_home",
        required_keywords=["Google", "chrome", "浏览器", "browser"],
        optional_keywords=[
            "搜索",
            "地址",
            "输入网址",
            "输入搜索",
            "搜索或输入网址",
            "书签",
            "历史记录",
            "标签页",
            "www",
        ],
        negative_keywords=["抖音", "微信", "设置"],
        ui_hints=["search_box", "address_bar", "bottom_toolbar"],
        min_score=0.65,
        description="浏览器首页：顶部搜索/地址栏",
    ),
    "search_page": PageTemplate(
        state="search_page",
        required_keywords=["搜索", "search", "输入"],
        optional_keywords=[
            "建议",
            "历史记录",
            "结果",
            "搜索结果",
            "热门搜索",
            "输入搜索内容",
            "请输入",
            "清除",
        ],
        negative_keywords=["设置", "Wi-Fi", "蓝牙"],
        ui_hints=["search_input", "search_box", "keyboard"],
        min_score=0.60,
        description="搜索页：搜索框激活状态",
    ),
}


def get_template(state: str) -> PageTemplate | None:
    """获取页面模板"""
    return PAGE_TEMPLATES.get(state)


def get_all_templates() -> dict[str, PageTemplate]:
    """获取所有模板"""
    return PAGE_TEMPLATES


def get_supported_states() -> list[str]:
    """获取支持的状态列表"""
    return list(PAGE_TEMPLATES.keys())


# 任务到目标状态的映射
TASK_TARGET_MAPPING = {
    "打开设置": "settings_home",
    "打开浏览器": "browser_home",
    "点击搜索": "search_page",
    "打开搜索": "search_page",
    "搜索": "search_page",
    "打开 Wi-Fi": "settings_wifi",
    "打开无线网络": "settings_wifi",
    "打开 WLAN": "settings_wifi",
    "打开蓝牙": "settings_bluetooth",
    "打开 Bluetooth": "settings_bluetooth",
}


def get_target_state_from_task(task: str) -> str | None:
    """从任务描述提取目标状态"""
    task_lower = task.lower()

    for keyword, target in TASK_TARGET_MAPPING.items():
        if keyword.lower() in task_lower:
            return target

    return None
