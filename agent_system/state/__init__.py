"""
State Module - 页面状态机

提供页面状态检测、状态转移、状态机管理等功能
"""

from .page_states import PageState, PageStateEnum, get_state_enum
from .simple_state_planner import (
    PlanResult,
    can_execute_directly,
    get_task_required_state,
    get_task_target_state,
    normalize_task,
    plan_next_step,
    should_go_home_first,
    should_open_browser_first,
)
from .state_detector import DetectionResult, StateDetector, detect_page_state
from .state_machine import StateMachine, get_state_machine

__all__ = [
    "PageState",
    "PageStateEnum",
    "get_state_enum",
    "StateDetector",
    "detect_page_state",
    "DetectionResult",
    "StateMachine",
    "get_state_machine",
    # simple_state_planner
    "plan_next_step",
    "PlanResult",
    "normalize_task",
    "should_go_home_first",
    "should_open_browser_first",
    "can_execute_directly",
    "get_task_target_state",
    "get_task_required_state",
]
