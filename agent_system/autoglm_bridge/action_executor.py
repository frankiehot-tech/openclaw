"""
Action Executor - 动作执行器

将模型输出映射到 device_control 层
包含动作白名单校验和安全校验
"""

import logging
import os
import sys
import time

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from device_control.adb_client import ADBClient

# 配置日志
logger = logging.getLogger(__name__)

# 日志文件
AUTOGLM_LOG = "os.path.join(os.path.dirname(os.path.abspath(__file__)), '../logs/autoglm.log')"

# 配置日志
file_handler = logging.FileHandler(AUTOGLM_LOG)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(file_handler)


# 动作白名单 - 只允许这些动作
ALLOWED_ACTIONS = {"tap", "swipe", "input_text", "back", "home"}

# 安全配置
EDGE_MARGIN_RATIO = 0.05  # 边缘区域比例 5%（降低以允许更多操作）
MAX_SWIPE_DISTANCE = 2000  # 最大滑动距离
MAX_INPUT_TEXT_LENGTH = 500  # 最大输入文本长度
MAX_REPEATED_TAPS = 3  # 最大连续点击次数
ACTION_DELAY = 0.5  # 动作执行延迟（秒）
MAX_RETRIES = 2  # 最大重试次数


class ActionExecutor:
    """动作执行器"""

    def __init__(self, device_id: str | None = None):
        """
        初始化动作执行器

        Args:
            device_id: 设备序列号
        """
        self.device_id = device_id
        self.adb_client = ADBClient(device_id)

        # 获取屏幕尺寸用于校验
        self.screen_size = self.adb_client.get_screen_size()
        if self.screen_size:
            logger.info(f"屏幕尺寸: {self.screen_size[0]}x{self.screen_size[1]}")

    def validate_action(self, action: dict) -> tuple[bool, str | None]:
        """
        校验动作是否合法（新格式 + 旧格式兼容）

        Args:
            action: 动作字典

        Returns:
            (是否合法, 错误信息)
        """
        # 检查动作类型
        action_type = action.get("action")
        if action_type not in ALLOWED_ACTIONS:
            return False, f"不支持的动作类型: {action_type}"

        # 新格式：使用 params
        if "params" in action:
            params = action.get("params", {})

            # 校验 tap
            if action_type == "tap":
                x = params.get("x")
                y = params.get("y")

                if x is None or y is None:
                    return False, "tap 动作缺少坐标"

                if not self._validate_coords(x, y):
                    return False, f"坐标超出屏幕范围: ({x}, {y})"

            # 校验 swipe
            elif action_type == "swipe":
                required = ["x1", "y1", "x2", "y2"]
                for key in required:
                    if key not in params:
                        return False, f"swipe 动作缺少 {key}"

                if not self._validate_coords(params["x1"], params["y1"]):
                    return False, "起点坐标超出屏幕范围"

                if not self._validate_coords(params["x2"], params["y2"]):
                    return False, "终点坐标超出屏幕范围"

            # 校验 input_text
            elif action_type == "input_text":
                if "text" not in params:
                    return False, "input_text 动作缺少 text"
        else:
            # 旧格式兼容
            # 校验 tap
            if action_type == "tap":
                x = action.get("x")
                y = action.get("y")

                if x is None or y is None:
                    return False, "tap 动作缺少坐标"

                if not self._validate_coords(x, y):
                    return False, f"坐标超出屏幕范围: ({x}, {y})"

            # 校验 swipe
            elif action_type == "swipe":
                required = ["x1", "y1", "x2", "y2"]
                for key in required:
                    if key not in action:
                        return False, f"swipe 动作缺少 {key}"

                if not self._validate_coords(action["x1"], action["y1"]):
                    return False, "起点坐标超出屏幕范围"

                if not self._validate_coords(action["x2"], action["y2"]):
                    return False, "终点坐标超出屏幕范围"

            # 校验 input_text
            elif action_type == "input_text":
                if "text" not in action:
                    return False, "input_text 动作缺少 text"

        # back 和 home 不需要额外校验
        return True, None

    def _validate_coords(self, x: int, y: int) -> bool:
        """
        校验坐标是否在屏幕范围内

        Args:
            x: X 坐标
            y: Y 坐标

        Returns:
            是否有效
        """
        if not self.screen_size:
            # 没有屏幕尺寸信息，跳过校验
            return True

        width, height = self.screen_size
        return 0 <= x <= width and 0 <= y <= height

    def validate_action_safety(
        self, action: dict, history: list[dict] | None = None, screen_meta: dict | None = None
    ) -> tuple[bool, str | None, str | None]:
        """
        增强安全校验

        规则：
        1. 禁止连续点击同一坐标超过 3 次
        2. 禁止点击屏幕边缘区域（上下左右各 10%）
        3. 限制 swipe 最大距离
        4. 限制 input_text 最大长度
        5. 对未知 action 直接拒绝

        Args:
            action: 动作字典
            history: 历史步骤列表
            screen_meta: 屏幕元数据

        Returns:
            (是否安全, 错误信息, failure_type)
        """
        action_type = action.get("action")

        # 规则 5: 对未知 action 直接拒绝
        if action_type not in ALLOWED_ACTIONS:
            return False, f"未知动作类型: {action_type}", "invalid_action"

        # 提取参数
        params = action.get("params", {})

        # 规则 1: 禁止连续点击同一坐标超过 3 次
        if action_type == "tap" and history:
            # 获取最近的历史记录
            recent_taps = []
            for step in reversed(history[-10:]):  # 检查最近10步
                step_action = step.get("executed_action", {})
                step_type = step_action.get("action")
                step_params = step_action.get("params", {})

                if step_type == "tap":
                    x = step_params.get("x") or step_action.get("x")
                    y = step_params.get("y") or step_action.get("y")
                    if x is not None and y is not None:
                        recent_taps.append((x, y))

            # 检查当前点击是否与最近点击重复
            current_x = params.get("x") if params else action.get("x")
            current_y = params.get("y") if params else action.get("y")

            if current_x is not None and current_y is not None:
                # 统计连续相同坐标
                consecutive_count = 0
                for x, y in reversed(recent_taps):
                    if x == current_x and y == current_y:
                        consecutive_count += 1
                    else:
                        break

                if consecutive_count >= MAX_REPEATED_TAPS:
                    return (False, f"连续点击同一坐标超过 {MAX_REPEATED_TAPS} 次", "loop_detected")

        # 规则 2: 禁止点击屏幕边缘区域
        if action_type == "tap" and self.screen_size:
            width, height = self.screen_size
            margin_x = int(width * EDGE_MARGIN_RATIO)
            margin_y = int(height * EDGE_MARGIN_RATIO)

            x = params.get("x") if params else action.get("x")
            y = params.get("y") if params else action.get("y")

            if x is not None and y is not None:
                # 检查是否在边缘区域
                if x < margin_x or x > width - margin_x or y < margin_y or y > height - margin_y:
                    return (
                        False,
                        f"点击坐标在边缘区域 ({x}, {y})，边缘限制: {margin_x}x{margin_y}",
                        "edge_click_blocked",
                    )

        # 规则 3: 限制 swipe 最大距离
        if action_type == "swipe" and self.screen_size:
            x1 = params.get("x1") if params else action.get("x1")
            y1 = params.get("y1") if params else action.get("y1")
            x2 = params.get("x2") if params else action.get("x2")
            y2 = params.get("y2") if params else action.get("y2")

            if all(v is not None for v in [x1, y1, x2, y2]):
                distance = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
                if distance > MAX_SWIPE_DISTANCE:
                    return (
                        False,
                        f"滑动距离 {distance:.0f} 超过最大限制 {MAX_SWIPE_DISTANCE}",
                        "invalid_action",
                    )

        # 规则 4: 限制 input_text 最大长度
        if action_type == "input_text":
            text = params.get("text") if params else action.get("text")
            if text and len(text) > MAX_INPUT_TEXT_LENGTH:
                return (
                    False,
                    f"输入文本长度 {len(text)} 超过最大限制 {MAX_INPUT_TEXT_LENGTH}",
                    "invalid_action",
                )

        return True, None, None

    def execute_with_safety(
        self, action: dict, history: list[dict] | None = None, screen_meta: dict | None = None
    ) -> tuple[bool, str, str | None]:
        """
        带安全校验的执行

        执行顺序：validate_output → validate_action → validate_action_safety → execute

        Args:
            action: 动作字典
            history: 历史步骤列表
            screen_meta: 屏幕元数据

        Returns:
            (是否成功, 结果信息, failure_type)
        """
        # 步骤 1: 基础校验
        valid, error = self.validate_action(action)
        if not valid:
            return False, error, "invalid_action"

        # 步骤 2: 安全校验
        safe, safety_error, failure_type = self.validate_action_safety(action, history, screen_meta)
        if not safe:
            logger.warning(f"安全校验失败: {safety_error}")
            return False, safety_error, failure_type

        # 步骤 3: 执行（带重试）
        success, message = self.execute_with_retry(action, MAX_RETRIES)

        if not success:
            return False, message, "adb_error"

        # 执行成功后添加延迟
        time.sleep(ACTION_DELAY)

        return True, message, None

    def execute(self, action: dict) -> tuple[bool, str]:
        """
        执行动作（新格式 + 旧格式兼容）

        Args:
            action: 动作字典

        Returns:
            (是否成功, 结果信息)
        """
        # 校验动作
        valid, error = self.validate_action(action)
        if not valid:
            logger.error(f"动作校验失败: {error}")
            return False, error

        action_type = action.get("action")

        # 提取参数（新格式优先）
        params = action.get("params", {})

        try:
            if action_type == "tap":
                # 新格式
                if params:
                    x = params.get("x")
                    y = params.get("y")
                else:
                    # 旧格式兼容
                    x = action.get("x")
                    y = action.get("y")

                success = self.adb_client.tap(x, y)
                return success, f"点击 ({x}, {y})"

            elif action_type == "swipe":
                # 新格式
                if params:
                    x1 = params.get("x1")
                    y1 = params.get("y1")
                    x2 = params.get("x2")
                    y2 = params.get("y2")
                else:
                    # 旧格式兼容
                    x1 = action.get("x1")
                    y1 = action.get("y1")
                    x2 = action.get("x2")
                    y2 = action.get("y2")

                duration = action.get("duration", 300)

                success = self.adb_client.swipe(x1, y1, x2, y2, duration)
                return success, f"滑动 ({x1},{y1}) -> ({x2},{y2})"

            elif action_type == "input_text":
                # 新格式
                if params:
                    text = params.get("text")
                else:
                    # 旧格式兼容
                    text = action.get("text")

                success = self.adb_client.input_text(text)
                return success, f"输入: {text}"

            elif action_type == "back":
                success = self.adb_client.press_back()
                return success, "返回"

            elif action_type == "home":
                success = self.adb_client.press_home()
                return success, "主页"

            else:
                return False, f"未知动作: {action_type}"

        except Exception as e:
            logger.error(f"执行动作异常: {str(e)}")
            return False, str(e)

    def execute_with_retry(self, action: dict, max_retries: int = 3) -> tuple[bool, str]:
        """
        带重试的执行

        Args:
            action: 动作字典
            max_retries: 最大重试次数

        Returns:
            (是否成功, 结果信息)
        """
        for attempt in range(max_retries):
            success, message = self.execute(action)

            if success:
                return True, message

            logger.warning(f"执行失败 (尝试 {attempt + 1}/{max_retries}): {message}")

        return False, f"重试 {max_retries} 次后仍失败"


# 全局缓存
_executor: ActionExecutor | None = None


def get_action_executor(device_id: str | None = None) -> ActionExecutor:
    """获取动作执行器"""
    global _executor

    if _executor is None or _executor.device_id != device_id:
        _executor = ActionExecutor(device_id)

    return _executor


def reset_action_executor():
    """重置动作执行器"""
    global _executor
    _executor = None


if __name__ == "__main__":
    # 测试代码
    print("=== Action Executor 测试 ===")

    executor = ActionExecutor()

    # 测试有效动作
    valid_actions = [
        {"action": "tap", "x": 500, "y": 1200},
        {"action": "swipe", "x1": 540, "y1": 2000, "x2": 540, "y2": 500},
        {"action": "input_text", "text": "hello"},
        {"action": "back"},
        {"action": "home"},
    ]

    print("\n有效动作测试:")
    for action in valid_actions:
        valid, error = executor.validate_action(action)
        print(f"  {action['action']}: {'✓' if valid else f'✗ {error}'}")

    # 测试无效动作
    invalid_actions = [
        {"action": "tap"},  # 缺少坐标
        {"action": "tap", "x": -1, "y": 100},  # 坐标无效
        {"action": "unknown"},  # 未知动作
    ]

    print("\n无效动作测试:")
    for action in invalid_actions:
        valid, error = executor.validate_action(action)
        print(f"  {action.get('action', 'unknown')}: {'✓' if valid else f'✗ {error}'}")
