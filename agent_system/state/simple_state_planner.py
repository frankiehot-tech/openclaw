"""
Simple State Planner - 最小状态规划器 (Phase 11.5 强化版)

基于当前页面状态和任务目标，规划执行步骤
包含状态置信度门控 (State Gate)
"""

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# 日志文件
STATE_LOG = "os.path.join(os.path.dirname(os.path.abspath(__file__)), '../logs/state.log')"

# 配置日志
if os.path.exists(os.path.dirname(STATE_LOG)):
    file_handler = logging.FileHandler(STATE_LOG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(file_handler)

# 配置项
STATE_CONFIDENCE_THRESHOLD = float(os.getenv("STATE_CONFIDENCE_THRESHOLD", "0.65"))
STATE_ENABLE_POST_ACTION_CHECK = (
    os.getenv("STATE_ENABLE_POST_ACTION_CHECK", "true").lower() == "true"
)


@dataclass
class PlanResult:
    """规划结果"""

    plan_type: (
        str  # "direct_execute", "go_home_first", "open_browser_first", "conservative_fallback"
    )
    next_action: str  # "home", "open_browser", "open_settings", "direct"
    reason: str
    requires_precondition: bool = False
    precondition_action: str | None = None
    # State Gate 相关字段
    state_gate_used: bool = False
    state_gate_reason: str = ""
    state_confidence: float = 0.0
    original_state: str = "unknown"


# 任务到目标状态的映射 (Phase 12 扩展)
TASK_TARGET_STATE = {
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
    "返回上一级": "back",
    "回到主屏幕": "home_screen",
    "向上滑动": "swipe_up",
    "向下滑动": "swipe_down",
}

# 任务需要的前置状态 (Phase 12 扩展)
TASK_REQUIRED_STATE = {
    "打开设置": "home_screen",
    "打开浏览器": "home_screen",
    "点击搜索": "browser_home",
    "打开搜索": "browser_home",
    "搜索": "browser_home",
    "打开 Wi-Fi": "settings_home",
    "打开无线网络": "settings_home",
    "打开 WLAN": "settings_home",
    "打开蓝牙": "settings_home",
    "打开 Bluetooth": "settings_home",
    "返回上一级": None,  # 任何状态都可以
    "回到主屏幕": None,
    "向上滑动": None,
    "向下滑动": None,
}


def normalize_task(task: str) -> str:
    """标准化任务名称"""
    task = task.strip().lower()

    # 常见任务名映射
    task_mapping = {
        "打开设置": "打开设置",
        "打开浏览器": "打开浏览器",
        "点击搜索": "点击搜索",
        "返回上一级": "返回上一级",
        "返回": "返回上一级",
        "回到主屏幕": "回到主屏幕",
        "home": "回到主屏幕",
        "向上滑动": "向上滑动",
        "向下滑动": "向下滑动",
    }

    for key, value in task_mapping.items():
        if key in task:
            return value

    return task


def plan_next_step(task: str, current_state: str, state_confidence: float = 0.0) -> PlanResult:
    """
    规划下一步动作 (带状态置信度门控)

    Args:
        task: 任务名称
        current_state: 当前页面状态 (home_screen, settings_home, browser_home, unknown)
        state_confidence: 状态检测置信度 (0.0-1.0)

    Returns:
        PlanResult: 规划结果
    """
    task = normalize_task(task)

    # 记录规划输入
    logger.info(
        f"状态规划输入: task={task}, current_state={current_state}, confidence={state_confidence:.2f}"
    )

    # ========== State Gate: 置信度门控 ==========
    # 如果置信度低于阈值，使用保守策略
    if state_confidence < STATE_CONFIDENCE_THRESHOLD:
        logger.warning(
            f"State Gate 触发: 置信度 {state_confidence:.2f} < 阈值 {STATE_CONFIDENCE_THRESHOLD}"
        )

        # 对于需要前置状态的任务，使用保守策略
        required_state = TASK_REQUIRED_STATE.get(task)
        if required_state is not None:
            # 保守策略：先回到主屏幕
            logger.info(f"保守策略: 任务 {task} 需要前置状态 {required_state}，先回到主屏幕")
            return PlanResult(
                plan_type="conservative_fallback",
                next_action="home",
                reason=f"状态置信度低 ({state_confidence:.2f})，使用保守策略先回到主屏幕",
                requires_precondition=True,
                precondition_action="回到主屏幕",
                state_gate_used=True,
                state_gate_reason=f"low_confidence_{current_state}",
                state_confidence=state_confidence,
                original_state=current_state,
            )

        # 无前置状态要求，直接执行
        return PlanResult(
            plan_type="direct_execute",
            next_action="direct",
            reason=f"状态置信度低但任务 {task} 无前置状态要求",
            state_gate_used=True,
            state_gate_reason=f"low_confidence_{current_state}_no_precondition",
            state_confidence=state_confidence,
            original_state=current_state,
        )

    # ========== 正常规划流程 ==========
    # 获取任务需要的前置状态
    required_state = TASK_REQUIRED_STATE.get(task)

    # 如果任务没有前置状态要求，直接执行
    if required_state is None:
        logger.info(f"任务 {task} 无前置状态要求，直接执行")
        return PlanResult(
            plan_type="direct_execute",
            next_action="direct",
            reason=f"任务 {task} 无前置状态要求",
            state_confidence=state_confidence,
            original_state=current_state,
        )

    # 检查当前状态是否满足要求
    if current_state == required_state:
        logger.info(f"当前状态 {current_state} 已满足任务 {task} 的前置条件")
        return PlanResult(
            plan_type="direct_execute",
            next_action="direct",
            reason=f"当前状态已满足 {task} 的前置条件",
            state_confidence=state_confidence,
            original_state=current_state,
        )

    # 规则 A: 任务 = "打开浏览器"，若当前状态不是 home_screen，返回计划先执行 home
    if task == "打开浏览器" and current_state != "home_screen":
        logger.info(f"打开浏览器需要先回到主屏幕，当前状态: {current_state}")
        return PlanResult(
            plan_type="go_home_first",
            next_action="home",
            reason="打开浏览器前需要先回到主屏幕",
            requires_precondition=True,
            precondition_action="回到主屏幕",
            state_confidence=state_confidence,
            original_state=current_state,
        )

    # 规则 B: 任务 = "打开设置"，若当前状态不是 home_screen，返回计划先执行 home
    if task == "打开设置" and current_state != "home_screen":
        logger.info(f"打开设置需要先回到主屏幕，当前状态: {current_state}")
        return PlanResult(
            plan_type="go_home_first",
            next_action="home",
            reason="打开设置前需要先回到主屏幕",
            requires_precondition=True,
            precondition_action="回到主屏幕",
            state_confidence=state_confidence,
            original_state=current_state,
        )

    # 规则 C: 任务 = "点击搜索"，若当前状态不是 browser_home，返回计划先打开浏览器
    if task == "点击搜索" and current_state != "browser_home":
        logger.info(f"点击搜索需要先打开浏览器，当前状态: {current_state}")
        return PlanResult(
            plan_type="open_browser_first",
            next_action="open_browser",
            reason="点击搜索前需要先打开浏览器",
            requires_precondition=True,
            precondition_action="打开浏览器",
            state_confidence=state_confidence,
            original_state=current_state,
        )

    # 规则 D (Phase 12): 任务 = "打开 Wi-Fi"，若当前是 home_screen → 先打开设置
    if task in ["打开 Wi-Fi", "打开无线网络", "打开 WLAN"]:
        if current_state == "home_screen":
            logger.info(f"打开 Wi-Fi 需要先打开设置，当前状态: {current_state}")
            return PlanResult(
                plan_type="open_settings_first",
                next_action="open_settings",
                reason="打开 Wi-Fi 前需要先打开设置",
                requires_precondition=True,
                precondition_action="打开设置",
                state_confidence=state_confidence,
                original_state=current_state,
            )
        elif current_state == "settings_wifi":
            logger.info("当前已在 Wi-Fi 页面，直接成功")
            return PlanResult(
                plan_type="direct_execute",
                next_action="direct",
                reason="当前已在 Wi-Fi 页面",
                state_confidence=state_confidence,
                original_state=current_state,
            )

    # 规则 E (Phase 12): 任务 = "打开蓝牙"，若当前是 home_screen → 先打开设置
    if task in ["打开蓝牙", "打开 Bluetooth"]:
        if current_state == "home_screen":
            logger.info(f"打开蓝牙需要先打开设置，当前状态: {current_state}")
            return PlanResult(
                plan_type="open_settings_first",
                next_action="open_settings",
                reason="打开蓝牙前需要先打开设置",
                requires_precondition=True,
                precondition_action="打开设置",
                state_confidence=state_confidence,
                original_state=current_state,
            )
        elif current_state == "settings_bluetooth":
            logger.info("当前已在蓝牙页面，直接成功")
            return PlanResult(
                plan_type="direct_execute",
                next_action="direct",
                reason="当前已在蓝牙页面",
                state_confidence=state_confidence,
                original_state=current_state,
            )

    # 规则 F (Phase 12): 任务 = "点击搜索"，若当前已是 search_page → 不重复点击
    if task in ["点击搜索", "打开搜索", "搜索"]:
        if current_state == "search_page":
            logger.info("当前已在搜索页面，不重复点击")
            return PlanResult(
                plan_type="direct_execute",
                next_action="direct",
                reason="当前已在搜索页面",
                state_confidence=state_confidence,
                original_state=current_state,
            )

    # 默认：直接执行
    logger.info(f"使用默认规划: 直接执行任务 {task}")
    return PlanResult(
        plan_type="direct_execute",
        next_action="direct",
        reason="默认直接执行",
        state_confidence=state_confidence,
        original_state=current_state,
    )


def get_task_target_state(task: str) -> str | None:
    """获取任务的目标状态"""
    task = normalize_task(task)
    return TASK_TARGET_STATE.get(task)


def get_task_required_state(task: str) -> str | None:
    """获取任务需要的前置状态"""
    task = normalize_task(task)
    return TASK_REQUIRED_STATE.get(task)


# 便捷函数
def should_go_home_first(task: str, current_state: str, state_confidence: float = 0.0) -> bool:
    """判断是否需要先回到主屏幕"""
    result = plan_next_step(task, current_state, state_confidence)
    return result.plan_type == "go_home_first"


def should_open_browser_first(task: str, current_state: str, state_confidence: float = 0.0) -> bool:
    """判断是否需要先打开浏览器"""
    result = plan_next_step(task, current_state, state_confidence)
    return result.plan_type == "open_browser_first"


def can_execute_directly(task: str, current_state: str, state_confidence: float = 0.0) -> bool:
    """判断是否可以直接执行"""
    result = plan_next_step(task, current_state, state_confidence)
    return result.plan_type == "direct_execute"


def is_state_gate_used(result: PlanResult) -> bool:
    """判断是否使用了 state gate"""
    return result.state_gate_used


def get_state_gate_info(result: PlanResult) -> dict:
    """获取 state gate 信息"""
    return {
        "state_gate_used": result.state_gate_used,
        "state_gate_reason": result.state_gate_reason,
        "state_confidence": result.state_confidence,
        "original_state": result.original_state,
    }
