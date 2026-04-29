"""
Vision Router - 视觉路由决策器

决定何时调用 MiniCPM 进行视觉增强，何时使用 OCR 结果
遵循 OCR-first, MiniCPM-second 原则
"""

import logging
import os

# 添加项目根目录到路径
import sys
from dataclasses import asdict, dataclass
from typing import Any

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from vision.minicpm_client import (
    VISION_USE_MINICPM,
    MiniCPMResult,
    get_minicpm_client,
    is_minicpm_available,
)

# 配置日志
logger = logging.getLogger(__name__)

# 日志文件
VISION_LOG = "os.path.join(os.path.dirname(os.path.abspath(__file__)), '../logs/vision.log')"

# 配置日志
if os.path.exists(os.path.dirname(VISION_LOG)):
    file_handler = logging.FileHandler(VISION_LOG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(file_handler)


# ========== 配置项 ==========

# MiniCPM 置信度阈值
MINICPM_CONFIDENCE_THRESHOLD = float(os.getenv("MINICPM_CONFIDENCE_THRESHOLD", "0.70"))

# OCR 高置信度阈值（高于此值不调用 MiniCPM）
OCR_HIGH_CONFIDENCE_THRESHOLD = float(os.getenv("OCR_HIGH_CONFIDENCE_THRESHOLD", "0.85"))

# 复杂 UI 类型列表（这些类型更依赖 MiniCPM）
COMPLEX_UI_TYPES = {
    "search_box",
    "search_input",
    "list_item",
    "toggle",
    "switch",
    "checkbox",
    "radio_button",
    "popup",
    "dialog",
    "modal",
    "drawer",
    "navigation_bar",
    "tab_bar",
    "fab",  # Floating Action Button
    "icon_button",
}

# 启用 MiniCPM 的任务列表（仅这些任务会调用 MiniCPM）
MINICPM_ENABLED_TASKS = {
    "点击搜索",
    "打开Wi-Fi页面",
    "打开Wi-Fi",
    "打开蓝牙页面",
    "打开蓝牙",
    "搜索",
    "search",
}


# ========== 数据结构 ==========


@dataclass
class VisionRouteDecision:
    """视觉路由决策结果"""

    use_minicpm: bool  # 是否使用 MiniCPM
    decision_reason: str  # 决策原因
    source: str  # 最终使用的来源: ocr_grounding, minicpm_vision, model_inference, fallback
    grounding_target: dict | None = None  # grounding 目标
    suggested_action: dict | None = None  # 建议动作
    minicpm_result: MiniCPMResult | None = None  # MiniCPM 结果（如果调用了）
    ocr_confidence: float = 0.0  # OCR 置信度
    minicpm_confidence: float = 0.0  # MiniCPM 置信度

    def to_dict(self) -> dict:
        return asdict(self)

    def add_to_context(self, context: dict) -> dict:
        """添加到执行上下文"""
        context["vision_route"] = self.to_dict()
        context["minicpm_used"] = self.use_minicpm
        context["action_source"] = self.source

        if self.minicpm_result:
            context["minicpm_page_type"] = self.minicpm_result.page_type
            context["minicpm_target_type"] = self.minicpm_result.target_type
            context["minicpm_confidence"] = self.minicpm_result.confidence

        return context


# ========== 路由决策逻辑 ==========


class VisionRouter:
    """视觉路由决策器"""

    def __init__(
        self,
        minicpm_confidence_threshold: float = MINICPM_CONFIDENCE_THRESHOLD,
        ocr_high_confidence_threshold: float = OCR_HIGH_CONFIDENCE_THRESHOLD,
    ):
        """
        初始化视觉路由

        Args:
            minicpm_confidence_threshold: MiniCPM 置信度阈值
            ocr_high_confidence_threshold: OCR 高置信度阈值
        """
        self.minicpm_confidence_threshold = minicpm_confidence_threshold
        self.ocr_high_confidence_threshold = ocr_high_confidence_threshold

        logger.info(
            f"VisionRouter 初始化: minicpm_threshold={minicpm_confidence_threshold}, "
            f"ocr_threshold={ocr_high_confidence_threshold}"
        )

    def should_use_minicpm(
        self, task: str, ocr_result: dict | None = None, state_result: dict | None = None
    ) -> tuple[bool, str]:
        """
        判断是否应该使用 MiniCPM

        Args:
            task: 任务描述
            ocr_result: OCR grounding 结果
            state_result: 状态检测结果

        Returns:
            (是否使用 MiniCPM, 原因)
        """
        # 1. 检查 MiniCPM 是否启用
        if not VISION_USE_MINICPM:
            return False, "MiniCPM 未启用 (VISION_USE_MINICPM=false)"

        # 2. 检查任务是否在白名单
        if not self._is_minicpm_enabled_task(task):
            return False, f"任务 '{task}' 不在 MiniCPM 启用列表中"

        # 3. 检查 MiniCPM 是否可用
        if not is_minicpm_available():
            return False, "MiniCPM 不可用"

        # 4. 检查 OCR 结果
        if ocr_result:
            ocr_confidence = ocr_result.get("confidence", 0.0)
            target_type = ocr_result.get("element_type", "")

            # OCR 高置信度命中 → 不调用 MiniCPM
            if ocr_confidence >= self.ocr_high_confidence_threshold:
                return False, f"OCR 高置信度命中 (conf={ocr_confidence:.2f})"

            # OCR 目标是复杂 UI 类型 → 考虑调用 MiniCPM
            if target_type in COMPLEX_UI_TYPES:
                if ocr_confidence < self.ocr_high_confidence_threshold:
                    return True, f"OCR 目标为复杂 UI ({target_type}) 且置信度较低"

        # 5. 默认调用 MiniCPM（作为增强层）
        return True, "默认使用 MiniCPM 增强"

    def _is_minicpm_enabled_task(self, task: str) -> bool:
        """
        检查任务是否在 MiniCPM 启用列表

        Args:
            task: 任务描述

        Returns:
            是否启用
        """
        task_lower = task.lower()

        for enabled_task in MINICPM_ENABLED_TASKS:
            if enabled_task.lower() in task_lower:
                return True

        return False

    def route_vision_analysis(
        self,
        image_path: str,
        task: str,
        ocr_result: dict | None = None,
        state_result: dict | None = None,
        context: dict | None = None,
    ) -> VisionRouteDecision:
        """
        路由视觉分析

        决策流程：
        1. OCR 高置信命中 → 直接使用 OCR 结果
        2. OCR 未命中 / 低置信 / 复杂 UI → 调用 MiniCPM
        3. MiniCPM 返回高置信 → 转换为 grounding/action
        4. 否则 → 回退到原有流程 (model inference)

        Args:
            image_path: 截图路径
            task: 任务描述
            ocr_result: OCR grounding 结果
            state_result: 状态检测结果
            context: 额外上下文

        Returns:
            VisionRouteDecision 决策结果
        """
        logger.info(f"VisionRouter 分析: task={task}")

        # 1. 判断是否使用 MiniCPM
        should_use, reason = self.should_use_minicpm(task, ocr_result, state_result)

        if not should_use:
            # 不使用 MiniCPM，使用 OCR 结果
            logger.info(f"不使用 MiniCPM: {reason}")

            if ocr_result and ocr_result.get("confidence", 0) > 0:
                return VisionRouteDecision(
                    use_minicpm=False,
                    decision_reason=reason,
                    source="ocr_grounding",
                    grounding_target=ocr_result,
                    suggested_action=self._ocr_to_action(ocr_result),
                    ocr_confidence=ocr_result.get("confidence", 0.0),
                )
            else:
                # OCR 也没有结果，回退到 model inference
                return VisionRouteDecision(
                    use_minicpm=False,
                    decision_reason=f"{reason}; OCR 也未命中",
                    source="model_inference",
                    grounding_target=None,
                    suggested_action=None,
                    ocr_confidence=0.0,
                )

        # 2. 使用 MiniCPM
        logger.info(f"使用 MiniCPM: {reason}")

        # 构建上下文
        minicpm_context = self._build_context(ocr_result, state_result, context)

        # 调用 MiniCPM（带异常处理）
        client = get_minicpm_client()

        try:
            minicpm_result = client.analyze_screen(image_path, task, minicpm_context)
        except Exception as e:
            logger.error(f"MiniCPM 调用异常: {e}")
            # 回退到 model inference
            return VisionRouteDecision(
                use_minicpm=False,
                decision_reason=f"MiniCPM 调用失败: {str(e)}",
                source="fallback",
                grounding_target=None,
                suggested_action=None,
                minicpm_confidence=0.0,
            )

        # 3. 检查 MiniCPM 结果
        if (
            minicpm_result.target_found
            and minicpm_result.confidence >= self.minicpm_confidence_threshold
        ):
            # MiniCPM 高置信命中
            logger.info(
                f"MiniCPM 命中: {minicpm_result.target_label}, "
                f"conf={minicpm_result.confidence:.2f}"
            )

            return VisionRouteDecision(
                use_minicpm=True,
                decision_reason=f"MiniCPM 高置信命中 (conf={minicpm_result.confidence:.2f})",
                source="minicpm_vision",
                grounding_target=minicpm_result.to_grounding_format(),
                suggested_action=minicpm_result.to_action_format(),
                minicpm_result=minicpm_result,
                minicpm_confidence=minicpm_result.confidence,
            )
        elif minicpm_result.target_found:
            # MiniCPM 低置信，尝试结合 OCR
            logger.warning(
                f"MiniCPM 低置信: {minicpm_result.target_label}, "
                f"conf={minicpm_result.confidence:.2f}"
            )

            # 如果 OCR 有结果，比较置信度
            if ocr_result and ocr_result.get("confidence", 0) > minicpm_result.confidence:
                return VisionRouteDecision(
                    use_minicpm=False,
                    decision_reason="MiniCPM 低置信，OCR 置信度更高",
                    source="ocr_grounding",
                    grounding_target=ocr_result,
                    suggested_action=self._ocr_to_action(ocr_result),
                    minicpm_result=minicpm_result,
                    ocr_confidence=ocr_result.get("confidence", 0.0),
                    minicpm_confidence=minicpm_result.confidence,
                )
            else:
                # 使用 MiniCPM 结果
                return VisionRouteDecision(
                    use_minicpm=True,
                    decision_reason=f"MiniCPM 低置信但无更好选择 (conf={minicpm_result.confidence:.2f})",
                    source="minicpm_vision",
                    grounding_target=minicpm_result.to_grounding_format(),
                    suggested_action=minicpm_result.to_action_format(),
                    minicpm_result=minicpm_result,
                    minicpm_confidence=minicpm_result.confidence,
                )
        else:
            # MiniCPM 未找到目标，回退
            logger.warning("MiniCPM 未找到目标，回退到 model inference")

            return VisionRouteDecision(
                use_minicpm=True,
                decision_reason="MiniCPM 未找到目标",
                source="fallback",
                grounding_target=None,
                suggested_action=None,
                minicpm_result=minicpm_result,
                minicpm_confidence=0.0,
            )

    def _build_context(
        self,
        ocr_result: dict | None,
        state_result: dict | None,
        extra_context: dict | None,
    ) -> dict:
        """
        构建 MiniCPM 上下文

        Args:
            ocr_result: OCR 结果
            state_result: 状态结果
            extra_context: 额外上下文

        Returns:
            上下文字典
        """
        context = {}

        # 添加 OCR 文本
        if ocr_result:
            text = ocr_result.get("text", "")
            if text:
                context["ocr_texts"] = [text]

        # 添加状态信息
        if state_result:
            page_type = state_result.get("page_type", "")
            if page_type:
                context["page_type"] = page_type

        # 合并额外上下文
        if extra_context:
            context.update(extra_context)

        return context

    def _ocr_to_action(self, ocr_result: dict) -> dict:
        """
        将 OCR 结果转换为动作格式

        Args:
            ocr_result: OCR 结果

        Returns:
            动作字典
        """
        center = ocr_result.get("center", [])

        if center and len(center) == 2:
            return {
                "action": "tap",
                "params": {"x": int(center[0]), "y": int(center[1])},
                "reason": f"点击 '{ocr_result.get('text', '')}'",
                "confidence": ocr_result.get("confidence", 0.0),
                "source": "ocr_grounding",
            }

        return {
            "action": "none",
            "params": {},
            "reason": "无法生成动作",
            "confidence": 0.0,
            "source": "ocr_grounding",
        }


# ========== 全局单例 ==========

_vision_router: VisionRouter | None = None


def get_vision_router() -> VisionRouter:
    """获取全局视觉路由"""
    global _vision_router

    if _vision_router is None:
        _vision_router = VisionRouter()

    return _vision_router


def reset_vision_router():
    """重置视觉路由"""
    global _vision_router
    _vision_router = None


# ========== 便捷函数 ==========


def route_vision_analysis(
    image_path: str,
    task: str,
    ocr_result: dict | None = None,
    state_result: dict | None = None,
    context: dict | None = None,
) -> VisionRouteDecision:
    """
    路由视觉分析（便捷函数）

    Args:
        image_path: 截图路径
        task: 任务描述
        ocr_result: OCR 结果
        state_result: 状态结果
        context: 额外上下文

    Returns:
        VisionRouteDecision
    """
    router = get_vision_router()
    return router.route_vision_analysis(image_path, task, ocr_result, state_result, context)


def should_use_minicpm(
    task: str, ocr_result: dict | None = None, state_result: dict | None = None
) -> tuple[bool, str]:
    """
    判断是否使用 MiniCPM（便捷函数）

    Args:
        task: 任务描述
        ocr_result: OCR 结果
        state_result: 状态结果

    Returns:
        (是否使用, 原因)
    """
    router = get_vision_router()
    return router.should_use_minicpm(task, ocr_result, state_result)


# ========== Qwen 轻量路线 ==========

import requests

QWEN_SERVICE_URL = os.getenv("QWEN_SERVICE_URL", "http://127.0.0.1:8001")
QWEN_TIMEOUT = 30  # 固定 30 秒超时


def describe_with_qwen(
    image_path: str,
    prompt: str = "请用一句中文描述这张截图中最显眼的界面内容，不要猜测看不清的细节。",
) -> dict[str, Any]:
    """
    使用 Qwen 服务描述图片

    Args:
        image_path: 图片路径
        prompt: 可选提示词

    Returns:
        {"ok": bool, "text": str, "error": str}
    """
    try:
        response = requests.post(
            f"{QWEN_SERVICE_URL}/describe",
            json={"image_path": image_path, "prompt": prompt},
            timeout=QWEN_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except requests.Timeout:
        logger.error(f"Qwen 服务超时 ({QWEN_TIMEOUT}s)")
        return {"ok": False, "error": f"Qwen 服务超时 ({QWEN_TIMEOUT}s)"}
    except requests.ConnectionError as e:
        logger.error(f"Qwen 服务连接失败: {e}")
        return {"ok": False, "error": f"Qwen 服务连接失败: {e}"}
    except requests.RequestException as e:
        logger.error(f"Qwen 服务调用失败: {e}")
        return {"ok": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Qwen 描述异常: {e}")
        return {"ok": False, "error": str(e)}


# ========== 测试 ==========

if __name__ == "__main__":
    print("=== Vision Router 测试 ===")

    # 设置测试环境
    os.environ["VISION_USE_MINICPM"] = "true"

    router = VisionRouter()

    # 测试 1: OCR 高置信，不使用 MiniCPM
    print("\n1. OCR 高置信测试:")
    ocr_high = {"text": "设置", "confidence": 0.9, "center": [540, 200], "element_type": "text"}
    should_use, reason = router.should_use_minicpm("打开设置", ocr_high)
    print(f"   should_use: {should_use}, reason: {reason}")

    # 测试 2: 复杂 UI 类型，使用 MiniCPM
    print("\n2. 复杂 UI 测试:")
    ocr_low = {
        "text": "搜索",
        "confidence": 0.5,
        "center": [540, 150],
        "element_type": "search_box",
    }
    should_use, reason = router.should_use_minicpm("点击搜索", ocr_low)
    print(f"   should_use: {should_use}, reason: {reason}")

    # 测试 3: 完整路由流程
    print("\n3. 完整路由测试:")
    decision = router.route_vision_analysis(
        "/fake/screen.png", "点击搜索", ocr_result=None, state_result=None
    )
    print(f"   use_minicpm: {decision.use_minicpm}")
    print(f"   decision_reason: {decision.decision_reason}")
    print(f"   source: {decision.source}")
    if decision.minicpm_result:
        print(f"   minicpm_page_type: {decision.minicpm_result.page_type}")
        print(f"   minicpm_target_type: {decision.minicpm_result.target_type}")
        print(f"   minicpm_confidence: {decision.minicpm_result.confidence}")
    if decision.suggested_action:
        print(f"   suggested_action: {decision.suggested_action}")

    # 测试 4: 打开 Wi-Fi 页面
    print("\n4. 打开Wi-Fi页面测试:")
    decision = router.route_vision_analysis(
        "/fake/screen.png", "打开Wi-Fi页面", ocr_result=None, state_result=None
    )
    print(f"   use_minicpm: {decision.use_minicpm}")
    print(f"   source: {decision.source}")
    if decision.minicpm_result:
        print(f"   target_label: {decision.minicpm_result.target_label}")
        print(f"   center: {decision.minicpm_result.center}")

    # 测试 5: 打开蓝牙页面
    print("\n5. 打开蓝牙页面测试:")
    decision = router.route_vision_analysis(
        "/fake/screen.png", "打开蓝牙页面", ocr_result=None, state_result=None
    )
    print(f"   use_minicpm: {decision.use_minicpm}")
    print(f"   source: {decision.source}")
    if decision.minicpm_result:
        print(f"   target_label: {decision.minicpm_result.target_label}")
        print(f"   center: {decision.minicpm_result.center}")

    print("\n=== 测试完成 ===")
