"""
Page State Schema for Phase 1 - Phase 1 页面状态模型

定义 Athena Open Human Phase 1 专用的页面状态枚举。
独立于 agent_system/state/page_states.py，仅用于 Phase 1 发布流程识别。
"""

from dataclasses import asdict, dataclass
from enum import StrEnum


class Phase1PageState(StrEnum):
    """Phase 1 专用页面状态枚举"""

    UNKNOWN = "unknown"
    APP_HOME = "app_home"
    ACCOUNT_HOME = "account_home"
    CREATE_ENTRY = "create_entry"
    DRAFT_EDIT = "draft_edit"
    PRE_PUBLISH_REVIEW = "pre_publish_review"
    PUBLISH_SUCCESS = "publish_success"
    PUBLISH_FAILURE = "publish_failure"
    RISK_PROMPT = "risk_prompt"
    LOGIN_REQUIRED = "login_required"
    OUT_OF_SCOPE = "out_of_scope"

    @classmethod
    def all_states(cls) -> list[str]:
        """获取所有状态值列表"""
        return [state.value for state in cls]

    @classmethod
    def from_string(cls, state_str: str) -> "Phase1PageState":
        """从字符串转换为枚举值"""
        state_str = state_str.lower().strip()
        for state in cls:
            if state.value == state_str:
                return state
        return cls.UNKNOWN


# 状态关键词映射 - 用于规则匹配
STATE_KEYWORDS = {
    Phase1PageState.LOGIN_REQUIRED: [
        "登录",
        "手机号登录",
        "验证码",
        "账号密码",
        "login",
        "sign in",
        "密码",
    ],
    Phase1PageState.RISK_PROMPT: [
        "风险提示",
        "异常操作",
        "安全验证",
        "稍后再试",
        "risk",
        "security",
        "验证",
    ],
    Phase1PageState.PUBLISH_SUCCESS: [
        "发布成功",
        "已发布",
        "发送成功",
        "发表成功",
        "publish success",
        "posted",
    ],
    Phase1PageState.PUBLISH_FAILURE: [
        "发布失败",
        "提交失败",
        "网络异常",
        "发送失败",
        "publish failed",
        "失败",
    ],
    Phase1PageState.PRE_PUBLISH_REVIEW: [
        "发布前确认",
        "确认发布",
        "预览",
        "publish review",
        "confirm",
    ],
    Phase1PageState.DRAFT_EDIT: [
        "标题",
        "正文",
        "请输入内容",
        "草稿",
        "编辑",
        "保存草稿",
        "draft",
        "edit",
    ],
    Phase1PageState.CREATE_ENTRY: [
        "创建",
        "发帖",
        "发布内容",
        "新建",
        "创建帖子",
        "发布新内容",
        "create",
        "post",
        "new",
    ],
    Phase1PageState.ACCOUNT_HOME: [
        "我的",
        "主页",
        "作品",
        "草稿箱",
        "我的主页",
        "个人主页",
        "account",
        "home",
        "profile",
    ],
    Phase1PageState.APP_HOME: ["首页", "推荐", "发现", "home", "main", "feed"],
}


def get_state_keywords(state: Phase1PageState) -> list[str]:
    """获取指定状态的关键词列表"""
    return STATE_KEYWORDS.get(state, [])


@dataclass
class PageStateInfo:
    """页面状态信息（用于内部传递）"""

    state: Phase1PageState
    description: str
    priority: int  # 优先级，数值越高优先级越高

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "PageStateInfo":
        return cls(**data)


# 状态优先级定义 - 用于解决规则冲突
STATE_PRIORITIES = {
    Phase1PageState.OUT_OF_SCOPE: 100,  # 最高优先级
    Phase1PageState.LOGIN_REQUIRED: 90,
    Phase1PageState.RISK_PROMPT: 80,
    Phase1PageState.PUBLISH_SUCCESS: 70,
    Phase1PageState.PUBLISH_FAILURE: 70,
    Phase1PageState.PRE_PUBLISH_REVIEW: 60,
    Phase1PageState.ACCOUNT_HOME: 55,  # 账户主页优先级高于草稿编辑
    Phase1PageState.DRAFT_EDIT: 50,
    Phase1PageState.CREATE_ENTRY: 40,
    Phase1PageState.APP_HOME: 20,
    Phase1PageState.UNKNOWN: 10,
}
