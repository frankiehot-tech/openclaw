"""
Task Whitelist - 任务白名单

定义允许执行的任务列表及其属性
"""

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# 日志文件
POLICY_LOG = "os.path.join(os.path.dirname(os.path.abspath(__file__)), '../logs/policy.log')"

# 配置日志
if os.path.exists(os.path.dirname(POLICY_LOG)):
    file_handler = logging.FileHandler(POLICY_LOG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(file_handler)


@dataclass
class TaskPolicy:
    """任务策略定义"""

    task_name: str
    normalized_task: str
    risk_level: str  # "low", "medium", "high", "critical"
    allowed: bool
    required_state: str | None = None
    target_state: str | None = None
    notes: str = ""


class TaskWhitelist:
    """任务白名单管理器"""

    def __init__(self):
        self._tasks: dict[str, TaskPolicy] = {}
        self._load_default_tasks()
        logger.info(f"TaskWhitelist 初始化: {len(self._tasks)} 个任务")

    def _load_default_tasks(self):
        """加载默认任务白名单"""
        default_tasks = [
            # 低风险导航任务
            TaskPolicy(
                task_name="打开设置",
                normalized_task="打开设置",
                risk_level="low",
                allowed=True,
                required_state=None,
                target_state="settings_home",
                notes="低风险导航任务",
            ),
            TaskPolicy(
                task_name="打开浏览器",
                normalized_task="打开浏览器",
                risk_level="low",
                allowed=True,
                required_state=None,
                target_state="browser_home",
                notes="低风险导航任务",
            ),
            TaskPolicy(
                task_name="点击搜索",
                normalized_task="点击搜索",
                risk_level="low",
                allowed=True,
                required_state=None,
                target_state="search_page",
                notes="低风险交互任务",
            ),
            TaskPolicy(
                task_name="返回上一级",
                normalized_task="返回上一级",
                risk_level="low",
                allowed=True,
                required_state=None,
                target_state=None,
                notes="系统导航任务",
            ),
            TaskPolicy(
                task_name="回到主屏幕",
                normalized_task="回到主屏幕",
                risk_level="low",
                allowed=True,
                required_state=None,
                target_state="home_screen",
                notes="系统导航任务",
            ),
            TaskPolicy(
                task_name="打开Wi-Fi页面",
                normalized_task="打开Wi-Fi页面",
                risk_level="low",
                allowed=True,
                required_state="settings_home",
                target_state="settings_wifi",
                notes="设置页面导航",
            ),
            TaskPolicy(
                task_name="打开蓝牙页面",
                normalized_task="打开蓝牙页面",
                risk_level="low",
                allowed=True,
                required_state="settings_home",
                target_state="settings_bluetooth",
                notes="设置页面导航",
            ),
            TaskPolicy(
                task_name="向上滑动",
                normalized_task="向上滑动",
                risk_level="low",
                allowed=True,
                required_state=None,
                target_state=None,
                notes="手势操作",
            ),
            TaskPolicy(
                task_name="向下滑动",
                normalized_task="向下滑动",
                risk_level="low",
                allowed=True,
                required_state=None,
                target_state=None,
                notes="手势操作",
            ),
            # 额外允许的任务
            TaskPolicy(
                task_name="打开相机",
                normalized_task="打开相机",
                risk_level="low",
                allowed=True,
                required_state=None,
                target_state="camera_app",
                notes="低风险应用启动",
            ),
            TaskPolicy(
                task_name="打开相册",
                normalized_task="打开相册",
                risk_level="low",
                allowed=True,
                required_state=None,
                target_state="gallery_app",
                notes="低风险应用启动",
            ),
            TaskPolicy(
                task_name="打开联系人",
                normalized_task="打开联系人",
                risk_level="low",
                allowed=True,
                required_state=None,
                target_state="contacts_app",
                notes="低风险应用启动",
            ),
            TaskPolicy(
                task_name="打开信息",
                normalized_task="打开信息",
                risk_level="low",
                allowed=True,
                required_state=None,
                target_state="messages_app",
                notes="低风险应用启动",
            ),
            TaskPolicy(
                task_name="打开微信",
                normalized_task="打开微信",
                risk_level="medium",
                allowed=True,
                required_state=None,
                target_state="wechat_app",
                notes="中风险应用启动",
            ),
            TaskPolicy(
                task_name="点击",
                normalized_task="点击",
                risk_level="low",
                allowed=True,
                required_state=None,
                target_state=None,
                notes="通用点击操作",
            ),
            TaskPolicy(
                task_name="长按",
                normalized_task="长按",
                risk_level="low",
                allowed=True,
                required_state=None,
                target_state=None,
                notes="通用长按操作",
            ),
            TaskPolicy(
                task_name="输入文本",
                normalized_task="输入文本",
                risk_level="low",
                allowed=True,
                required_state=None,
                target_state=None,
                notes="文本输入操作",
            ),
        ]

        for task in default_tasks:
            self._tasks[task.normalized_task] = task

    def is_allowed(self, task: str) -> bool:
        """检查任务是否在白名单中"""
        normalized = self._normalize_task(task)

        # 直接匹配
        if normalized in self._tasks:
            return self._tasks[normalized].allowed

        # 模糊匹配
        for task_key in self._tasks:
            if task_key in normalized or normalized in task_key:
                return self._tasks[task_key].allowed

        logger.warning(f"任务不在白名单中: {task}")
        return False

    def get_task_policy(self, task: str) -> TaskPolicy | None:
        """获取任务策略"""
        normalized = self._normalize_task(task)

        if normalized in self._tasks:
            return self._tasks[normalized]

        # 模糊匹配
        for task_key in self._tasks:
            if task_key in normalized or normalized in task_key:
                return self._tasks[task_key]

        return None

    def get_risk_level(self, task: str) -> str:
        """获取任务风险等级"""
        policy = self.get_task_policy(task)
        if policy:
            return policy.risk_level
        return "unknown"

    def get_target_state(self, task: str) -> str | None:
        """获取任务目标状态"""
        policy = self.get_task_policy(task)
        if policy:
            return policy.target_state
        return None

    def get_required_state(self, task: str) -> str | None:
        """获取任务所需状态"""
        policy = self.get_task_policy(task)
        if policy:
            return policy.required_state
        return None

    def _normalize_task(self, task: str) -> str:
        """标准化任务名称"""
        # 去除空格、转小写
        return task.strip().lower()

    def add_task(self, policy: TaskPolicy):
        """添加任务到白名单"""
        self._tasks[policy.normalized_task] = policy
        logger.info(f"添加任务到白名单: {policy.task_name}")

    def remove_task(self, task: str):
        """从白名单移除任务"""
        normalized = self._normalize_task(task)
        if normalized in self._tasks:
            del self._tasks[normalized]
            logger.info(f"从白名单移除任务: {task}")

    def list_allowed_tasks(self) -> list[str]:
        """列出所有允许的任务"""
        return [t.task_name for t in self._tasks.values() if t.allowed]

    def list_low_risk_tasks(self) -> list[str]:
        """列出所有低风险任务"""
        return [t.task_name for t in self._tasks.values() if t.risk_level == "low" and t.allowed]


# 全局单例
_whitelist: TaskWhitelist | None = None


def get_task_whitelist() -> TaskWhitelist:
    """获取全局任务白名单"""
    global _whitelist
    if _whitelist is None:
        _whitelist = TaskWhitelist()
    return _whitelist


# ========== 便捷函数 ==========


def is_task_allowed(task: str) -> bool:
    """
    检查任务是否在白名单中（便捷函数）

    Args:
        task: 任务描述

    Returns:
        是否允许执行
    """
    whitelist = get_task_whitelist()
    return whitelist.is_allowed(task)


def reject_if_not_allowed(task: str) -> dict:
    """
    如果任务不在白名单中，返回拒绝原因

    Args:
        task: 任务描述

    Returns:
        拒绝原因字典: {"allowed": False, "reason": "..."}
    """
    whitelist = get_task_whitelist()
    policy = whitelist.get_task_policy(task)

    if policy:
        return {
            "allowed": False,
            "reason": f"任务 '{task}' 不在白名单中",
            "risk_level": policy.risk_level,
        }

    return {"allowed": False, "reason": f"任务 '{task}' 未定义风险等级", "risk_level": "unknown"}


def get_task_risk_level(task: str) -> str:
    """获取任务风险等级（便捷函数）"""
    whitelist = get_task_whitelist()
    return whitelist.get_risk_level(task)


def get_task_target_state(task: str) -> str | None:
    """获取任务目标状态（便捷函数）"""
    whitelist = get_task_whitelist()
    return whitelist.get_target_state(task)


def get_task_required_state(task: str) -> str | None:
    """获取任务所需状态（便捷函数）"""
    whitelist = get_task_whitelist()
    return whitelist.get_required_state(task)
