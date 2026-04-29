"""
Agent Loop - 核心控制循环

执行截图 → 推理 → 执行 → 反馈 循环
包含：
- 页面变化检测
- Retry + Fallback 机制
- 超时控制
- OCR + UI Grounding 增强
- 任务白名单检查
- 页面状态检测与规划
"""

import logging
import os
import sys
import time

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from autoglm_bridge.action_executor import get_action_executor
from autoglm_bridge.memory import get_memory
from autoglm_bridge.model_client import get_model_client
from device_control.device_manager import get_device_manager
from device_control.screen_capture import (
    capture_screen,
    get_screen_hash,
    is_screen_changed,
)

# Vision 模块
from vision.screen_analyzer import get_screen_analyzer

# MiniCPM 路由（阶段 13 新增）
try:
    from vision.vision_router import is_minicpm_available, route_vision_analysis

    MINICPM_IMPORTED = True
except ImportError:
    MINICPM_IMPORTED = False

    def route_vision_analysis(*args, **kwargs):
        return {"use_minicpm": False, "source": "ocr_grounding"}

    def is_minicpm_available():
        return False


# Policy 模块 (任务白名单)
from policy.task_whitelist import is_task_allowed, reject_if_not_allowed
from state.simple_state_planner import plan_next_step

# State 模块 (页面状态检测与规划)
from state.state_detector import detect_page_state

# 配置日志
logger = logging.getLogger(__name__)

# 日志文件
AUTOGLM_LOG = "os.path.join(os.path.dirname(os.path.abspath(__file__)), '../logs/autoglm.log')"
PIPELINE_LOG = "os.path.join(os.path.dirname(os.path.abspath(__file__)), '../logs/pipeline.log')"
POLICY_LOG = "os.path.join(os.path.dirname(os.path.abspath(__file__)), '../logs/policy.log')"
STATE_LOG = "os.path.join(os.path.dirname(os.path.abspath(__file__)), '../logs/state.log')"

# 配置日志
file_handler = logging.FileHandler(AUTOGLM_LOG)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(file_handler)

pipeline_handler = logging.FileHandler(PIPELINE_LOG)
pipeline_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(pipeline_handler)

# Policy 日志
policy_logger = logging.getLogger("policy")
policy_handler = logging.FileHandler(POLICY_LOG)
policy_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
policy_logger.addHandler(policy_handler)

# State 日志
state_logger = logging.getLogger("state")
state_handler = logging.FileHandler(STATE_LOG)
state_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
state_logger.addHandler(state_handler)

# 运行控制参数
TASK_TIMEOUT = 30  # 任务超时（秒）
MAX_NO_CHANGE_STEPS = 2  # 页面无变化最大步数

# Phase 11.5: Post-Action State Check 配置
STATE_ENABLE_POST_ACTION_CHECK = (
    os.environ.get("STATE_ENABLE_POST_ACTION_CHECK", "true").lower() == "true"
)

# Phase 13: MiniCPM 配置
USE_MINICPM = os.environ.get("VISION_USE_MINICPM", "false").lower() == "true"
MINICPM_ENABLED_TASKS = {
    "点击搜索",
    "搜索",
    "search",
    "打开Wi-Fi",
    "打开 Wi-Fi",
    "打开Wi-Fi页面",
    "打开 Wi-Fi 页面",
    "打开蓝牙",
    "打开 蓝牙",
    "打开蓝牙页面",
    "打开 蓝牙 页面",
}

# 目标状态映射 (任务关键词 → 目标状态)
TARGET_STATE_MAPPING = {
    "打开设置": "settings_home",
    "打开浏览器": "browser_home",
    "点击搜索": "browser_home",
    "打开搜索": "browser_home",
    "搜索": "browser_home",
    "打开Wi-Fi": "wifi_settings",
    "打开 Wi-Fi": "wifi_settings",
    "打开蓝牙": "bluetooth_settings",
    "打开 蓝牙": "bluetooth_settings",
}


class AgentLoop:
    """Agent 控制循环"""

    def __init__(self, device_id: str | None = None, use_mock: bool = True, max_steps: int = 5):
        """
        初始化 Agent 循环

        Args:
            device_id: 设备序列号
            use_mock: 是否使用 mock 模式
            max_steps: 单次任务最大步数
        """
        self.device_id = device_id
        self.use_mock = use_mock
        self.max_steps = max_steps

        # 初始化组件
        self.model_client = get_model_client(use_mock=use_mock)
        self.action_executor = get_action_executor(device_id)
        self.memory = get_memory()
        self.device_manager = get_device_manager()

        logger.info(f"AgentLoop 初始化: device={device_id}, mock={use_mock}, max_steps={max_steps}")

    def _extract_target_from_task(self, task: str) -> list[str]:
        """
        从任务中提取可能的目标文本

        Args:
            task: 任务描述

        Returns:
            目标文本列表
        """
        # 常见目标关键词
        keywords = [
            "设置",
            "搜索",
            "浏览器",
            "返回",
            "主页",
            "微信",
            "信息",
            "通讯录",
            "相机",
            "相册",
            "音乐",
            "视频",
            "文件",
            "下载",
            "应用",
            "商店",
            "天气",
            "时钟",
            "计算器",
            "备忘录",
            "Settings",
            "Search",
            "Browser",
            "Back",
            "Home",
            "Camera",
        ]

        task_lower = task.lower()
        found = []

        for kw in keywords:
            if kw.lower() in task_lower:
                found.append(kw)

        return found

    def _try_ocr_grounding(
        self, screenshot_path: str, task: str
    ) -> tuple[dict | None, dict | None]:
        """
        尝试使用 OCR grounding 生成动作

        Args:
            screenshot_path: 截图路径
            task: 任务描述

        Returns:
            (grounding_result, ocr_context):
            - grounding_result: 如果 grounding 成功，返回动作字典；否则返回 None
            - ocr_context: OCR 上下文信息（用于 model inference）
        """
        ocr_context = None

        if not screenshot_path or not os.path.exists(screenshot_path):
            return None, ocr_context

        # 提取任务中的目标文本
        target_texts = self._extract_target_from_task(task)

        if not target_texts:
            return None, ocr_context

        # 从环境变量读取 OCR provider
        ocr_provider = os.environ.get("VISION_OCR_PROVIDER", "mock")

        # 使用 screen analyzer 进行分析
        analyzer = get_screen_analyzer(ocr_provider=ocr_provider, screen_size=(1080, 2640))

        logger.info(f"OCR Provider: {ocr_provider}")

        analysis = analyzer.analyze_screen(screenshot_path, expected_targets=target_texts)

        # 构建 OCR 上下文（用于 fallback）
        ocr_texts = []
        if analysis.ocr_blocks:
            # 提取前 10 个高置信度文本
            sorted_results = sorted(
                analysis.ocr_blocks, key=lambda x: x.get("confidence", 0), reverse=True
            )[:10]
            ocr_texts = [r.get("text", "") for r in sorted_results if r.get("text")]

        ocr_context = {
            "ocr_provider": ocr_provider,
            "ocr_texts": ocr_texts,
            "ocr_blocks_count": analysis.ocr_blocks_count,
            "target_texts": target_texts,
            "target_found": analysis.target_found,
        }

        # 如果找到目标，使用 grounding 结果
        if analysis.target_found and analysis.grounding_target:
            target = analysis.grounding_target
            center = target["center"]

            logger.info(
                f"OCR Grounding 命中: {target['text']}, "
                f"center={center}, confidence={target['confidence']:.2f}"
            )

            return {
                "action": "tap",
                "x": center[0],
                "y": center[1],
                "action_source": "ocr_grounding",
                "grounding_target": target["text"],
                "grounding_confidence": target["confidence"],
            }, ocr_context

        logger.info(f"OCR Grounding 未命中目标: {target_texts}")
        return None, ocr_context

    def _try_minicpm_routing(
        self,
        screenshot_path: str,
        task: str,
        ocr_result: list[dict] | None = None,
        state_result: dict | None = None,
    ) -> dict | None:
        """
        尝试使用 MiniCPM 路由生成动作（阶段 13 新增）

        流程：截图 → OCR → state detection → 若 OCR/规则足够 → 直接执行
              否则调用 vision_router → MiniCPM → 若 MiniCPM 返回高置信 target → 转成 grounding/action
              否则继续原有 model inference

        Args:
            screenshot_path: 截图路径
            task: 任务描述
            ocr_result: OCR 结果（可选）
            state_result: 状态检测结果（可选）

        Returns:
            如果 MiniCPM 路由成功，返回动作字典；否则返回 None
        """
        # 检查 MiniCPM 是否启用
        if not USE_MINICPM:
            logger.info("MiniCPM 未启用，跳过")
            return None

        # 检查任务是否在白名单
        if task not in MINICPM_ENABLED_TASKS:
            logger.info(f"任务 '{task}' 不在 MiniCPM 启用列表中")
            return None

        # 检查 MiniCPM 是否可用
        if not MINICPM_IMPORTED or not is_minicpm_available():
            logger.warning("MiniCPM 不可用，跳过")
            return None

        try:
            # 调用 vision_router 进行路由决策
            decision = route_vision_analysis(
                image_path=screenshot_path,
                task=task,
                ocr_result=ocr_result,
                state_result=state_result,
            )

            # 检查是否使用 MiniCPM
            if not decision.use_minicpm:
                logger.info(f"MiniCPM 路由决策不使用 MiniCPM: {decision.decision_reason}")
                return None

            # 获取 MiniCPM 返回的目标
            grounding_target = decision.grounding_target
            suggested_action = decision.suggested_action

            if not grounding_target and not suggested_action:
                logger.warning("MiniCPM 未返回有效目标")
                return None

            # 转换为动作
            if suggested_action and suggested_action.get("action") == "tap":
                center = suggested_action.get("params", {})
                x = center.get("x")
                y = center.get("y")
                confidence = decision.minicpm_confidence if decision.minicpm_confidence > 0 else 0.7

                # 获取 MiniCPM 结果中的信息
                minicpm_target_type = None
                minicpm_page_type = None
                if decision.minicpm_result:
                    minicpm_target_type = decision.minicpm_result.target_type
                    minicpm_page_type = decision.minicpm_result.page_type

                logger.info(
                    f"MiniCPM 生成动作: tap ({x}, {y}), "
                    f"confidence={confidence:.2f}, target={minicpm_target_type}"
                )

                return {
                    "action": "tap",
                    "x": x,
                    "y": y,
                    "action_source": "minicpm_vision",
                    "minicpm_used": True,
                    "minicpm_target_type": minicpm_target_type,
                    "minicpm_confidence": confidence,
                    "minicpm_page_type": minicpm_page_type,
                    "minicpm_reason": decision.decision_reason,
                }

        except Exception as e:
            logger.warning(f"MiniCPM 路由调用失败: {e}")

        return None

    def run_step(
        self,
        task: str,
        history: list[dict],
        device_id: str | None = None,
        prev_screenshot_path: str | None = None,
        use_vision: bool = True,
    ) -> dict:
        """
        执行单步（带页面变化检测和重试）

        Args:
            task: 当前任务
            history: 历史步骤
            device_id: 设备ID
            prev_screenshot_path: 上一张截图路径（用于页面变化检测）
            use_vision: 是否使用 OCR/grounding 增强

        Returns:
            步骤结果:
            {
                "step": 1,
                "screenshot_path": "...",
                "screen_hash": "...",
                "screen_changed": true/false,
                "model_output": {...},
                "executed_action": {...},
                "result": "success/failed",
                "error": "...",
                "failure_type": "...",
                "fallback_used": "back/home",
                "action_source": "ocr_grounding/model_inference/fallback"
            }
        """
        step_num = len(history) + 1
        step_start_time = time.time()

        logger.info(f"=== 执行步骤 {step_num} ===")
        logger.info(f"任务: {task}")

        # 1. 截图
        screenshot_path = capture_screen(device_id or self.device_id)
        screen_hash = None
        screen_changed = True

        if screenshot_path:
            logger.info(f"截图成功: {screenshot_path}")
            screen_hash = get_screen_hash(screenshot_path)

            # 检测页面变化
            if prev_screenshot_path:
                screen_changed = is_screen_changed(prev_screenshot_path, screenshot_path)
                logger.info(f"页面变化: {screen_changed}")
        else:
            logger.warning("截图失败，将使用 None")

        # 2. 优先尝试 OCR Grounding
        action_source = "model_inference"
        model_output = None
        ocr_context = None
        ocr_result = None

        if use_vision and screenshot_path:
            grounding_output, ocr_context = self._try_ocr_grounding(screenshot_path, task)
            if grounding_output:
                model_output = grounding_output
                action_source = "ocr_grounding"
                logger.info(f"使用 OCR Grounding 生成动作: {model_output}")
                # 保存 OCR 结果用于 MiniCPM
                ocr_result = ocr_context.get("ocr_texts", []) if ocr_context else []

        # 2.5 如果 OCR grounding 未命中，尝试 MiniCPM 路由（阶段 13 新增）
        if model_output is None and use_vision and screenshot_path:
            # 获取 OCR 上下文中的文本
            ocr_texts = ocr_context.get("ocr_texts", []) if ocr_context else []
            ocr_result_dict = [{"text": t} for t in ocr_texts]

            minicpm_output = self._try_minicpm_routing(
                screenshot_path, task, ocr_result=ocr_result_dict, state_result=None
            )

            if minicpm_output:
                model_output = minicpm_output
                action_source = "minicpm_vision"
                logger.info(f"使用 MiniCPM Vision 生成动作: {model_output}")

        # 3. 如果 OCR grounding 和 MiniCPM 都未命中，回退到 model inference
        if model_output is None:
            # 构建增强的模型输入（包含 OCR 上下文）
            enhanced_task = task
            if ocr_context:
                # 将 OCR 信息添加到任务描述中
                ocr_texts = ocr_context.get("ocr_texts", [])
                if ocr_texts:
                    ocr_info = ", ".join(ocr_texts[:10])
                    enhanced_task = f"{task}\n\n当前屏幕可见文本: {ocr_info}"
                    logger.info(f"增强模型输入: 添加 {len(ocr_texts)} 个 OCR 文本")

            # 调用模型推理（强制使用真实模式）
            model_output = self.model_client.infer_action(
                task=enhanced_task,
                screenshot_path=screenshot_path,
                history=history[-3:] if history else [],  # 最近 3 步历史
                use_mock=False,  # 强制使用真实模式
            )
            action_source = "model_inference"
            logger.info(f"使用 Model Inference 生成动作: {model_output}")

            # 4. 检查模型输出是否有错误
            if model_output.get("action") == "error":
                error_reason = model_output.get("reason", "未知错误")
                error_type = "api_error"

                # 识别错误类型
                if "超时" in error_reason:
                    error_type = "timeout"
                elif "解析" in error_reason or "JSON" in error_reason:
                    error_type = "invalid_json"
                elif "API" in error_reason:
                    error_type = "api_error"

                logger.error(f"Model Inference 错误: {error_type} - {error_reason}")

                # 回退到 back 操作
                model_output = {
                    "action": "back",
                    "params": {},
                    "reason": f"Model inference 失败 ({error_type})，回退到 back",
                    "action_source": "fallback",
                    "error_type": error_type,
                }
                action_source = "fallback"

        logger.info(f"模型输出: {model_output}")
        logger.info(f"动作来源: {action_source}")

        # 3. 执行动作（带安全校验和重试）
        executed_action = model_output.copy()

        # 使用带安全校验的执行
        success, message, failure_type = self.action_executor.execute_with_safety(
            model_output, history
        )

        executed_action["result"] = message
        executed_action["success"] = success

        logger.info(f"执行结果: {success} - {message}")

        # 4. 如果执行失败，尝试 fallback
        fallback_used = None
        if not success:
            logger.warning(f"执行失败，尝试 fallback: {failure_type}")

            # 按顺序尝试 fallback
            for fallback_action in ["back", "home"]:
                logger.info(f"尝试 fallback: {fallback_action}")
                fb_success, fb_msg = self.action_executor.execute({"action": fallback_action})

                if fb_success:
                    fallback_used = fallback_action
                    logger.info(f"Fallback 成功: {fallback_action}")
                    break

        # 5. 记录到记忆
        result = "success" if success else "failed"
        error = None if success else message

        # 计算步骤耗时
        step_duration = time.time() - step_start_time

        self.memory.add_step(
            step=step_num,
            task=task,
            screenshot_path=screenshot_path,
            model_output=model_output,
            executed_action=executed_action,
            result=result,
            error=error,
            screen_hash=screen_hash,
            fallback_used=fallback_used,
            failure_type=failure_type,
            step_duration=step_duration,
        )

        # 6. 检查循环
        if self.memory.is_loop_detected(model_output, threshold=3):
            logger.warning("检测到循环动作，停止执行")
            return {
                "step": step_num,
                "screenshot_path": screenshot_path,
                "screen_hash": screen_hash,
                "screen_changed": screen_changed,
                "model_output": model_output,
                "executed_action": executed_action,
                "result": "stopped",
                "error": "检测到循环动作",
                "failure_type": "loop_detected",
                "fallback_used": fallback_used,
                "step_duration": step_duration,
            }

        return {
            "step": step_num,
            "screenshot_path": screenshot_path,
            "screen_hash": screen_hash,
            "screen_changed": screen_changed,
            "model_output": model_output,
            "executed_action": executed_action,
            "result": result,
            "error": error,
            "failure_type": failure_type,
            "fallback_used": fallback_used,
            "step_duration": step_duration,
        }

    def run_task(
        self, task: str, max_steps: int | None = None, device_id: str | None = None
    ) -> dict:
        """
        执行完整任务 (带白名单检查和状态规划)

        执行顺序:
        task → whitelist check → screen capture → OCR/screen analysis
        → detect_page_state → simple_state_planner
        → 如果需要先 home 或先打开浏览器，则优先执行规划步骤
        → 再执行原目标任务

        Args:
            task: 任务描述
            max_steps: 最大步数（覆盖默认值）
            device_id: 设备ID

        Returns:
            任务结果:
            {
                "task": "...",
                "total_steps": 5,
                "steps": [...],
                "final_result": "success/failed/stopped",
                "history": [...],
                "task_allowed": true/false,
                "current_state": "...",
                "state_confidence": 0.0,
                "plan_type": "...",
                "planner_reason": "..."
            }
        """
        max_steps = max_steps or self.max_steps

        # ========== 1. 白名单检查 ==========
        policy_logger.info(f"任务进入白名单检查: {task}")

        # 检查任务是否在白名单内
        if not is_task_allowed(task):
            reject_result = reject_if_not_allowed(task)
            policy_logger.warning(f"任务被拒绝: {reject_result}")

            return {
                "task": task,
                "total_steps": 0,
                "steps": [],
                "final_result": "rejected",
                "history": [],
                "task_allowed": False,
                "reject_reason": reject_result.get("reason") if reject_result else "unknown",
                "current_state": None,
                "state_confidence": 0.0,
                "plan_type": None,
                "planner_reason": None,
            }

        policy_logger.info(f"任务通过白名单检查: {task}")

        # 开始任务
        self.memory.start_task(task)

        logger.info(f"========== 开始任务: {task} ==========")
        logger.info(f"最大步数: {max_steps}")

        # 确保设备可用
        actual_device_id = device_id or self.device_id
        if not actual_device_id:
            actual_device_id = self.device_manager.ensure_device_available()
            if actual_device_id:
                logger.info(f"使用设备: {actual_device_id}")

        # ========== 2. 页面状态检测 ==========
        # 先截取一张图来检测当前页面状态
        initial_screenshot = capture_screen(actual_device_id)

        current_state = "unknown"
        state_confidence = 0.0
        state_signals = []

        if initial_screenshot:
            # 使用 screen analyzer 进行分析
            ocr_provider = os.environ.get("VISION_OCR_PROVIDER", "mock")
            analyzer = get_screen_analyzer(ocr_provider=ocr_provider, screen_size=(1080, 2640))

            analysis = analyzer.analyze_screen(initial_screenshot)

            # 提取 OCR 文本
            ocr_texts = []
            if analysis.ocr_blocks:
                ocr_texts = [r.get("text", "") for r in analysis.ocr_blocks if r.get("text")]

            # 检测页面状态
            detection_result = detect_page_state(ocr_results=ocr_texts)
            current_state = detection_result.state
            state_confidence = detection_result.confidence
            state_signals = detection_result.signals

            state_logger.info(
                f"页面状态检测: {current_state}, 置信度: {state_confidence:.2f}, 信号: {state_signals}"
            )

        # ========== 3. 状态规划 ==========
        plan_result = plan_next_step(task, current_state)
        plan_type = plan_result.plan_type
        planner_reason = plan_result.reason

        state_logger.info(
            f"状态规划: task={task}, current_state={current_state}, plan_type={plan_type}, reason={planner_reason}"
        )

        # ========== 4. 执行规划步骤（如需要）==========
        steps = []

        # 如果需要先执行前置步骤
        if plan_result.requires_precondition and plan_result.precondition_action:
            precondition_task = plan_result.precondition_action
            logger.info(f"需要先执行前置步骤: {precondition_task}")

            # 执行前置步骤
            for step_num in range(1, 3):  # 最多 2 步执行前置任务
                history = self.memory.get_history()
                result = self.run_step(precondition_task, history, actual_device_id)
                steps.append(result)

                # 记录到 pipeline 日志
                pipeline_handler.emit(
                    logging.LogRecord(
                        "pipeline",
                        logging.INFO,
                        "",
                        0,
                        f"[PRECONDITION STEP {step_num}] action={result['model_output'].get('action')}, result={result['result']}",
                        [],
                        None,
                    )
                )

                # 如果前置步骤成功完成
                if result["result"] == "success":
                    logger.info(f"前置步骤完成: {precondition_task}")
                    break
                elif result["result"] == "failed":
                    logger.warning(f"前置步骤失败: {precondition_task}")
                    break

        # ========== 5. 执行原任务 ==========
        target_state = None

        # 从任务中提取目标状态
        for keyword, target in TARGET_STATE_MAPPING.items():
            if keyword in task:
                target_state = target
                break

        for step_num in range(1, max_steps + 1):
            # 获取历史
            history = self.memory.get_history()

            # 执行单步
            result = self.run_step(task, history, actual_device_id)
            steps.append(result)

            # 记录到 pipeline 日志
            pipeline_handler.emit(
                logging.LogRecord(
                    "pipeline",
                    logging.INFO,
                    "",
                    0,
                    f"[STEP {step_num}] action={result['model_output'].get('action')}, result={result['result']}",
                    [],
                    None,
                )
            )

            # ========== Phase 11.5: Post-Action State Check ==========
            post_action_state = None
            post_action_state_confidence = 0.0
            post_action_check_passed = False
            post_action_check_failed = False
            correction_action_used = None

            if STATE_ENABLE_POST_ACTION_CHECK and target_state and result["result"] == "success":
                # 等待一小段时间让页面稳定
                time.sleep(0.8)

                # 重新截图并检测状态
                post_screenshot = capture_screen(actual_device_id)

                if post_screenshot:
                    # 使用 screen analyzer 进行分析
                    ocr_provider = os.environ.get("VISION_OCR_PROVIDER", "mock")
                    analyzer = get_screen_analyzer(
                        ocr_provider=ocr_provider, screen_size=(1080, 2640)
                    )

                    post_analysis = analyzer.analyze_screen(post_screenshot)

                    # 提取 OCR 文本
                    post_ocr_texts = []
                    if post_analysis.ocr_blocks:
                        post_ocr_texts = [
                            r.get("text", "") for r in post_analysis.ocr_blocks if r.get("text")
                        ]

                    # 检测动作后状态
                    post_detection = detect_page_state(ocr_results=post_ocr_texts)
                    post_action_state = post_detection.state
                    post_action_state_confidence = post_detection.confidence

                    # 判断是否达到目标状态
                    if post_action_state == target_state:
                        post_action_check_passed = True
                        state_logger.info(
                            f"[POST-ACTION CHECK PASSED] task={task}, target={target_state}, "
                            f"actual={post_action_state}, confidence={post_action_state_confidence:.2f}"
                        )
                    else:
                        post_action_check_failed = True
                        state_logger.warning(
                            f"[POST-ACTION CHECK FAILED] task={task}, target={target_state}, "
                            f"actual={post_action_state}, confidence={post_action_state_confidence:.2f}"
                        )

                        # ========== Phase 11.5: 修正动作（允许一次）==========
                        # 判断修正动作类型
                        correction_action = None
                        if "设置" in task or "浏览器" in task:
                            correction_action = "home"
                        elif "搜索" in task:
                            correction_action = "back"

                        if correction_action:
                            state_logger.info(f"[POST-ACTION] 执行修正动作: {correction_action}")

                            # 执行修正动作
                            correction_result = self.action_executor.execute(
                                {"action": correction_action}
                            )

                            if correction_result[0]:  # success
                                correction_action_used = correction_action
                                state_logger.info(
                                    f"[POST-ACTION] 修正动作成功: {correction_action}"
                                )
                            else:
                                state_logger.warning(
                                    f"[POST-ACTION] 修正动作失败: {correction_action}"
                                )

            # 记录 post-action 状态到 memory
            if self.memory.steps:
                last_step = self.memory.steps[-1]
                last_step.post_action_state = post_action_state
                last_step.post_action_state_confidence = post_action_state_confidence
                last_step.post_action_state_check_passed = post_action_check_passed
                last_step.post_action_state_check_failed = post_action_check_failed
                last_step.target_state = target_state

            # 写入 state 日志
            if STATE_ENABLE_POST_ACTION_CHECK and target_state:
                state_logger.info(
                    f"[POST-ACTION STATE] task={task}, target={target_state}, "
                    f"post_state={post_action_state}, confidence={post_action_state_confidence:.2f}, "
                    f"passed={post_action_check_passed}, failed={post_action_check_failed}"
                )

            # 检查是否需要停止
            if result["result"] in ["stopped", "failed"]:
                logger.info(f"步骤 {step_num} 停止: {result['result']}")
                break

            # 如果动作是 back 或 home，认为任务可能完成
            action = result["model_output"].get("action")
            if action in ["home"]:
                logger.info("检测到 home 动作，任务可能完成")
                break

        # 任务结束
        final_result = "stopped" if steps and steps[-1].get("result") == "stopped" else "completed"

        logger.info(f"========== 任务完成: {task} ==========")
        logger.info(f"总步数: {len(steps)}")
        logger.info(f"最终结果: {final_result}")

        return {
            "task": task,
            "total_steps": len(steps),
            "steps": steps,
            "final_result": final_result,
            "history": self.memory.get_history(),
            "task_allowed": True,
            "current_state": current_state,
            "state_confidence": state_confidence,
            "plan_type": plan_type,
            "planner_reason": planner_reason,
        }

    def set_mock_mode(self, enabled: bool):
        """切换 mock 模式"""
        self.use_mock = enabled
        self.model_client.set_mock_mode(enabled)
        logger.info(f"切换模式: {'MOCK' if enabled else 'REAL'}")


# 全局单例
_loop: AgentLoop | None = None


def get_agent_loop(
    device_id: str | None = None, use_mock: bool = True, max_steps: int = 5
) -> AgentLoop:
    """获取全局 Agent 循环实例"""
    global _loop

    if _loop is None:
        _loop = AgentLoop(device_id=device_id, use_mock=use_mock, max_steps=max_steps)

    return _loop


def reset_agent_loop():
    """重置 Agent 循环"""
    global _loop
    _loop = None


if __name__ == "__main__":
    # 测试代码
    print("=== Agent Loop 测试 ===")

    # 创建 Agent 循环（mock 模式）
    agent = AgentLoop(use_mock=True, max_steps=3)

    # 执行测试任务
    result = agent.run_task("打开设置")

    print(f"\n任务: {result['task']}")
    print(f"总步数: {result['total_steps']}")
    print(f"最终结果: {result['final_result']}")

    # 打印每一步
    for step in result["steps"]:
        print(f"\n步骤 {step['step']}:")
        print(f"  动作: {step['model_output'].get('action')}")
        print(f"  结果: {step['result']}")
        print(f"  截图: {step['screenshot_path']}")
