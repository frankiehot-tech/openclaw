"""
Page States - 页面状态定义

定义标准页面状态枚举及数据结构
"""

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Dict, List, Optional


class PageStateEnum(str, Enum):
    """页面状态枚举"""

    UNKNOWN = "unknown"
    HOME_SCREEN = "home_screen"
    SETTINGS_HOME = "settings_home"
    SETTINGS_WIFI = "settings_wifi"
    SETTINGS_BLUETOOTH = "settings_bluetooth"
    SETTINGS_DISPLAY = "settings_display"
    SETTINGS_SOUND = "settings_sound"
    SETTINGS_BATTERY = "settings_battery"
    SETTINGS_APPLICATIONS = "settings_applications"
    BROWSER_HOME = "browser_home"
    SEARCH_PAGE = "search_page"
    APP_GRID = "app_grid"
    SYSTEM_DIALOG = "system_dialog"
    CAMERA_APP = "camera_app"
    GALLERY_APP = "gallery_app"
    CONTACTS_APP = "contacts_app"
    MESSAGES_APP = "messages_app"
    WECHAT_APP = "wechat_app"
    LOCK_SCREEN = "lock_screen"
    NOTIFICATION_PANEL = "notification_panel"


@dataclass
class PageState:
    """页面状态数据结构"""

    state: str
    confidence: float
    signals: List[str]
    source: str = "ocr"  # "ocr" | "hybrid" | "inference"

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "PageState":
        return cls(**data)


def get_state_enum(state_str: str) -> PageStateEnum:
    """将字符串转换为页面状态枚举"""
    state_str = state_str.lower().strip()

    for enum_val in PageStateEnum:
        if enum_val.value == state_str:
            return enum_val

    return PageStateEnum.UNKNOWN


# 页面状态识别关键词
STATE_KEYWORDS = {
    PageStateEnum.HOME_SCREEN: ["主屏幕", "主页", "home", "应用", "时钟", "天气"],
    PageStateEnum.SETTINGS_HOME: ["设置", "settings", "wi-fi", "蓝牙", "显示", "声音", "应用程序"],
    PageStateEnum.SETTINGS_WIFI: ["wi-fi", "wlan", "无线网络", "wpa", "网络"],
    PageStateEnum.SETTINGS_BLUETOOTH: ["蓝牙", "bluetooth", "设备", "可见性"],
    PageStateEnum.SETTINGS_DISPLAY: ["显示", "display", "亮度", "壁纸", "字体"],
    PageStateEnum.SETTINGS_SOUND: ["声音", "sound", "音量", "铃声", "震动"],
    PageStateEnum.SETTINGS_BATTERY: ["电池", "battery", "电源", "省电"],
    PageStateEnum.SETTINGS_APPLICATIONS: ["应用程序", "apps", "应用", "默认应用"],
    PageStateEnum.BROWSER_HOME: ["google", "chrome", "浏览器", "browser", "地址", "搜索"],
    PageStateEnum.SEARCH_PAGE: ["搜索", "search", "输入", "建议", "结果"],
    PageStateEnum.APP_GRID: ["应用", "apps", "全部应用", "应用程序"],
    PageStateEnum.SYSTEM_DIALOG: ["允许", "取消", "确定", "拒绝", "权限", "dialog"],
    PageStateEnum.CAMERA_APP: ["相机", "camera", "拍照", "摄影"],
    PageStateEnum.GALLERY_APP: ["相册", "gallery", "照片", "图库"],
    PageStateEnum.CONTACTS_APP: ["联系人", "contacts", "通讯录"],
    PageStateEnum.MESSAGES_APP: ["信息", "messages", "短信", "收件箱"],
    PageStateEnum.WECHAT_APP: ["微信", "wechat", "聊天"],
    PageStateEnum.LOCK_SCREEN: ["锁屏", "lock", "解锁", "滑动", "密码", "指纹", "面容"],
    PageStateEnum.NOTIFICATION_PANEL: ["通知", "notification", "下拉", "快捷"],
}


# 状态转移图 - 从当前状态可以转移到哪些状态
STATE_TRANSITIONS = {
    PageStateEnum.UNKNOWN: [
        PageStateEnum.HOME_SCREEN,
        PageStateEnum.LOCK_SCREEN,
    ],
    PageStateEnum.HOME_SCREEN: [
        PageStateEnum.SETTINGS_HOME,
        PageStateEnum.BROWSER_HOME,
        PageStateEnum.APP_GRID,
        PageStateEnum.CAMERA_APP,
        PageStateEnum.GALLERY_APP,
        PageStateEnum.CONTACTS_APP,
        PageStateEnum.MESSAGES_APP,
        PageStateEnum.WECHAT_APP,
        PageStateEnum.LOCK_SCREEN,
    ],
    PageStateEnum.SETTINGS_HOME: [
        PageStateEnum.SETTINGS_WIFI,
        PageStateEnum.SETTINGS_BLUETOOTH,
        PageStateEnum.SETTINGS_DISPLAY,
        PageStateEnum.SETTINGS_SOUND,
        PageStateEnum.SETTINGS_BATTERY,
        PageStateEnum.SETTINGS_APPLICATIONS,
        PageStateEnum.HOME_SCREEN,
    ],
    PageStateEnum.SETTINGS_WIFI: [
        PageStateEnum.SETTINGS_HOME,
    ],
    PageStateEnum.SETTINGS_BLUETOOTH: [
        PageStateEnum.SETTINGS_HOME,
    ],
    PageStateEnum.BROWSER_HOME: [
        PageStateEnum.SEARCH_PAGE,
        PageStateEnum.HOME_SCREEN,
    ],
    PageStateEnum.SEARCH_PAGE: [
        PageStateEnum.BROWSER_HOME,
    ],
    PageStateEnum.APP_GRID: [
        PageStateEnum.HOME_SCREEN,
    ],
    PageStateEnum.LOCK_SCREEN: [
        PageStateEnum.HOME_SCREEN,
    ],
}


def get_available_transitions(current_state: PageStateEnum) -> List[PageStateEnum]:
    """获取当前状态可用的转移"""
    return STATE_TRANSITIONS.get(current_state, [])
