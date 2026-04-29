"""
Risk Policy - 风险策略

提供任务风险分类、敏感任务拒绝等功能
"""

import logging
import os
from typing import Dict, Optional

from .task_whitelist import TaskWhitelist, get_task_whitelist

logger = logging.getLogger(__name__)

# 日志文件
POLICY_LOG = "os.path.join(os.path.dirname(os.path.abspath(__file__)), '../logs/policy.log')"

# 配置日志
if os.path.exists(os.path.dirname(POLICY_LOG)):
    file_handler = logging.FileHandler(POLICY_LOG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(file_handler)


# 敏感任务关键词 - 默认拒绝
SENSITIVE_KEYWORDS = [
    "登录",
    "登陆",
    "login",
    "signin",
    "支付",
    "付款",
    "pay",
    "checkout",
    "发送消息",
    "发消息",
    "发短信",
    "send message",
    "删除",
    "remove",
    "delete",
    "del",
    "下单",
    "购买",
    "buy",
    "order",
    "purchase",
    "转账",
    "汇款",
    "transfer",
    "修改账号",
    "修改密码",
    "change password",
    "change account",
    "验证码",
    "verification code",
    "code",
    "注册",
    "register",
    "sign up",
    "充值",
    "recharge",
    "top up",
    "绑定",
    "bind",
    "实名",
    "real name",
    "银行卡",
    "credit card",
    "debit card",
    "身份证",
    "id card",
    "隐私",
    "privacy",
    "设置密码",
    "set password",
    "解锁",
    "unlock",
    "刷机",
    "root",
    "恢复出厂",
    "factory reset",
]


class RiskPolicy:
    """风险策略管理器"""

    def __init__(self, whitelist: Optional[TaskWhitelist] = None):
        self._whitelist = whitelist or get_task_whitelist()
        self._sensitive_keywords = SENSITIVE_KEYWORDS.copy()
        logger.info("RiskPolicy 初始化")

    def is_task_allowed(self, task: str) -> bool:
        """
        检查任务是否允许执行

        Args:
            task: 任务名称

        Returns:
            bool: 是否允许执行
        """
        # 首先检查白名单
        if not self._whitelist.is_allowed(task):
            logger.warning(f"任务不在白名单中: {task}")
            return False

        # 检查敏感词
        if self.reject_if_sensitive(task):
            logger.warning(f"任务包含敏感词: {task}")
            return False

        return True

    def get_task_policy(self, task: str) -> Dict:
        """
        获取任务策略详情

        Args:
            task: 任务名称

        Returns:
            Dict: 任务策略
        """
        policy = self._whitelist.get_task_policy(task)
        if not policy:
            return {
                "task": task,
                "allowed": False,
                "reason": "task_not_whitelisted",
                "risk_level": "unknown",
            }

        is_sensitive = self.reject_if_sensitive(task)

        return {
            "task": task,
            "allowed": policy.allowed and not is_sensitive,
            "reason": (
                "allowed"
                if policy.allowed and not is_sensitive
                else ("sensitive_keyword" if is_sensitive else "not_in_whitelist")
            ),
            "risk_level": policy.risk_level,
            "target_state": policy.target_state,
            "required_state": policy.required_state,
            "notes": policy.notes,
        }

    def classify_task_risk(self, task: str) -> str:
        """
        分类任务风险等级

        Args:
            task: 任务名称

        Returns:
            str: 风险等级 ("low", "medium", "high", "critical", "unknown")
        """
        # 检查敏感词
        if self.reject_if_sensitive(task):
            return "critical"

        # 从白名单获取风险等级
        risk_level = self._whitelist.get_risk_level(task)
        return risk_level

    def reject_if_sensitive(self, task: str) -> bool:
        """
        检查任务是否包含敏感关键词

        Args:
            task: 任务名称

        Returns:
            bool: 是否包含敏感词
        """
        task_lower = task.lower()

        for keyword in self._sensitive_keywords:
            if keyword.lower() in task_lower:
                logger.warning(f"检测到敏感关键词 '{keyword}' in task: {task}")
                return True

        return False

    def add_sensitive_keyword(self, keyword: str):
        """添加敏感关键词"""
        if keyword.lower() not in [k.lower() for k in self._sensitive_keywords]:
            self._sensitive_keywords.append(keyword)
            logger.info(f"添加敏感关键词: {keyword}")

    def remove_sensitive_keyword(self, keyword: str):
        """移除敏感关键词"""
        keyword_lower = keyword.lower()
        self._sensitive_keywords = [
            k for k in self._sensitive_keywords if k.lower() != keyword_lower
        ]
        logger.info(f"移除敏感关键词: {keyword}")

    def get_rejection_reason(self, task: str) -> Optional[str]:
        """
        获取任务被拒绝的原因

        Args:
            task: 任务名称

        Returns:
            Optional[str]: 拒绝原因，如果允许则返回 None
        """
        if not self._whitelist.is_allowed(task):
            return "task_not_whitelisted"

        if self.reject_if_sensitive(task):
            return "sensitive_keyword"

        return None


# 全局单例
_risk_policy: Optional[RiskPolicy] = None


def get_risk_policy() -> RiskPolicy:
    """获取全局风险策略"""
    global _risk_policy
    if _risk_policy is None:
        _risk_policy = RiskPolicy()
    return _risk_policy


def is_task_allowed(task: str) -> bool:
    """快速检查任务是否允许"""
    return get_risk_policy().is_task_allowed(task)


def get_task_policy(task: str) -> Dict:
    """快速获取任务策略"""
    return get_risk_policy().get_task_policy(task)


def classify_task_risk(task: str) -> str:
    """快速分类任务风险"""
    return get_risk_policy().classify_task_risk(task)


def reject_if_sensitive(task: str) -> bool:
    """快速检查敏感词"""
    return get_risk_policy().reject_if_sensitive(task)
