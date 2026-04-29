"""
State Machine - 状态机

管理页面状态转移、生成转移计划、判断目标状态是否达成
"""

import logging
import os
from dataclasses import dataclass, field

from .page_states import PageStateEnum, get_available_transitions
from .state_detector import DetectionResult, StateDetector

logger = logging.getLogger(__name__)

# 日志文件
STATE_LOG = "os.path.join(os.path.dirname(os.path.abspath(__file__)), '../logs/state_machine.log')"

# 配置日志
if os.path.exists(os.path.dirname(STATE_LOG)):
    file_handler = logging.FileHandler(STATE_LOG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(file_handler)


@dataclass
class TransitionStep:
    """状态转移步骤"""

    step: int
    action: str  # "tap", "swipe", "back", "home"
    target: str  # 点击目标文本或滑动方向
    params: dict = field(default_factory=dict)
    description: str = ""


@dataclass
class TransitionPlan:
    """状态转移计划"""

    from_state: PageStateEnum
    to_state: PageStateEnum
    steps: list[TransitionStep]
    is_direct: bool  # 是否可以直接转移
    reason: str = ""


class StateMachine:
    """状态机管理器"""

    def __init__(self, confidence_threshold: float = 0.70):
        self.confidence_threshold = confidence_threshold
        self._detector = StateDetector(confidence_threshold=confidence_threshold)
        self._current_state: PageStateEnum | None = None
        self._current_confidence: float = 0.0
        self._current_signals: list[str] = []
        logger.info(f"StateMachine 初始化: threshold={confidence_threshold}")

    def get_current_state(
        self,
        ocr_results: list[str] = None,
        image_path: str = None,
        screen_analysis: dict = None,
        history: list[dict] = None,
    ) -> DetectionResult:
        """
        获取当前页面状态

        Args:
            ocr_results: OCR 识别到的文本列表
            image_path: 截图路径
            screen_analysis: 屏幕分析结果
            history: 历史动作记录

        Returns:
            DetectionResult: 当前状态
        """
        result = self._detector.detect_page_state(
            ocr_results=ocr_results,
            image_path=image_path,
            screen_analysis=screen_analysis,
            history=history,
        )

        # 更新内部状态
        self._current_state = result.state
        self._current_confidence = result.confidence
        self._current_signals = result.signals

        return result

    def can_execute_task_in_state(self, task: str, current_state: PageStateEnum) -> bool:
        """
        检查任务是否可以在当前状态执行

        Args:
            task: 任务名称
            from policy.task_whitelist import get_task_whitelist

            Returns:
                bool: 是否可以执行
        """
        from policy.task_whitelist import get_task_whitelist

        whitelist = get_task_whitelist()
        required_state = whitelist.get_required_state(task)

        # 如果任务没有状态要求，可以在任何状态执行
        if not required_state:
            return True

        # 检查当前状态是否匹配
        required = PageStateEnum(required_state) if required_state else None
        return current_state == required

    def get_transition_plan(self, task: str, current_state: PageStateEnum = None) -> TransitionPlan:
        """
        生成从当前状态到目标状态的转移计划

        Args:
            task: 任务名称
            current_state: 当前状态（可选，默认使用内部状态）

        Returns:
            TransitionPlan: 转移计划
        """
        from policy.task_whitelist import get_task_whitelist

        if current_state is None:
            current_state = self._current_state or PageStateEnum.UNKNOWN

        whitelist = get_task_whitelist()
        target_state_str = whitelist.get_target_state(task)

        # 如果任务没有目标状态，返回空计划
        if not target_state_str:
            return TransitionPlan(
                from_state=current_state,
                to_state=current_state,
                steps=[],
                is_direct=True,
                reason="任务无需状态转移",
            )

        target_state = PageStateEnum(target_state_str)

        # 如果当前状态就是目标状态，无需转移
        if current_state == target_state:
            return TransitionPlan(
                from_state=current_state,
                to_state=target_state,
                steps=[],
                is_direct=True,
                reason="已在目标状态",
            )

        # 生成转移计划
        steps = self._generate_transition_steps(current_state, target_state)

        return TransitionPlan(
            from_state=current_state,
            to_state=target_state,
            steps=steps,
            is_direct=len(steps) <= 1,
            reason=f"从 {current_state.value} 转移到 {target_state.value}",
        )

    def _generate_transition_steps(
        self, from_state: PageStateEnum, to_state: PageStateEnum
    ) -> list[TransitionStep]:
        """生成状态转移步骤"""
        steps = []

        # 状态转移映射 - 定义常见的状态转移动作
        state_action_map = {
            (PageStateEnum.HOME_SCREEN, PageStateEnum.SETTINGS_HOME): [
                TransitionStep(1, "tap", "设置", description="点击设置图标")
            ],
            (PageStateEnum.HOME_SCREEN, PageStateEnum.BROWSER_HOME): [
                TransitionStep(1, "tap", "浏览器", description="点击浏览器图标")
            ],
            (PageStateEnum.HOME_SCREEN, PageStateEnum.CAMERA_APP): [
                TransitionStep(1, "tap", "相机", description="点击相机图标")
            ],
            (PageStateEnum.HOME_SCREEN, PageStateEnum.GALLERY_APP): [
                TransitionStep(1, "tap", "相册", description="点击相册图标")
            ],
            (PageStateEnum.SETTINGS_HOME, PageStateEnum.SETTINGS_WIFI): [
                TransitionStep(1, "tap", "Wi-Fi", description="点击 Wi-Fi")
            ],
            (PageStateEnum.SETTINGS_HOME, PageStateEnum.SETTINGS_BLUETOOTH): [
                TransitionStep(1, "tap", "蓝牙", description="点击蓝牙")
            ],
            (PageStateEnum.SETTINGS_HOME, PageStateEnum.SETTINGS_DISPLAY): [
                TransitionStep(1, "tap", "显示", description="点击显示")
            ],
            (PageStateEnum.SETTINGS_HOME, PageStateEnum.HOME_SCREEN): [
                TransitionStep(1, "home", "", description="回到主屏幕")
            ],
            (PageStateEnum.SETTINGS_WIFI, PageStateEnum.SETTINGS_HOME): [
                TransitionStep(1, "back", "", description="返回设置首页")
            ],
            (PageStateEnum.SETTINGS_BLUETOOTH, PageStateEnum.SETTINGS_HOME): [
                TransitionStep(1, "back", "", description="返回设置首页")
            ],
            (PageStateEnum.BROWSER_HOME, PageStateEnum.SEARCH_PAGE): [
                TransitionStep(1, "tap", "搜索", description="点击搜索框")
            ],
            (PageStateEnum.BROWSER_HOME, PageStateEnum.HOME_SCREEN): [
                TransitionStep(1, "home", "", description="回到主屏幕")
            ],
            (PageStateEnum.SEARCH_PAGE, PageStateEnum.BROWSER_HOME): [
                TransitionStep(1, "back", "", description="返回浏览器首页")
            ],
            (PageStateEnum.LOCK_SCREEN, PageStateEnum.HOME_SCREEN): [
                TransitionStep(1, "swipe", "up", description="向上滑动解锁")
            ],
        }

        # 查找直接转移
        key = (from_state, to_state)
        if key in state_action_map:
            steps = state_action_map[key]
        else:
            # 尝试通过中间状态转移
            available = get_available_transitions(from_state)
            for intermediate in available:
                intermediate_key = (from_state, intermediate)
                if intermediate_key in state_action_map:
                    # 添加第一步
                    steps.extend(state_action_map[intermediate_key])

                    # 尝试添加第二步
                    second_key = (intermediate, to_state)
                    if second_key in state_action_map:
                        second_steps = state_action_map[second_key]
                        for s in second_steps:
                            s.step = s.step + 1
                        steps.extend(second_steps)
                    break

        if not steps:
            # 无法生成计划，返回通用步骤
            logger.warning(f"无法生成转移计划: {from_state} -> {to_state}")
            steps = [TransitionStep(1, "tap", "unknown", description="需要手动操作")]

        return steps

    def is_target_state_reached(self, task: str, current_state: PageStateEnum = None) -> bool:
        """
        判断是否已达到目标状态

        Args:
            task: 任务名称
            current_state: 当前状态

        Returns:
            bool: 是否达到目标状态
        """
        from policy.task_whitelist import get_task_whitelist

        if current_state is None:
            current_state = self._current_state

        whitelist = get_task_whitelist()
        target_state_str = whitelist.get_target_state(task)

        if not target_state_str:
            # 没有目标状态的任务，假设执行即完成
            return True

        target_state = PageStateEnum(target_state_str)
        return current_state == target_state

    def get_state_info(self) -> dict:
        """获取当前状态信息"""
        return {
            "state": self._current_state.value if self._current_state else "unknown",
            "confidence": self._current_confidence,
            "signals": self._current_signals,
        }

    def reset(self):
        """重置状态机"""
        self._current_state = None
        self._current_confidence = 0.0
        self._current_signals = []
        logger.info("状态机已重置")


# 全局状态机
_state_machine: StateMachine | None = None


def get_state_machine(confidence_threshold: float = 0.70) -> StateMachine:
    """获取全局状态机"""
    global _state_machine

    if _state_machine is None:
        _state_machine = StateMachine(confidence_threshold=confidence_threshold)

    return _state_machine
