"""
MiniCPM Vision Client - MiniCPM 视觉增强客户端

作为"视觉增强工具层"，用于补强 OCR 不足和复杂 UI 理解
不是主脑，只是 vision tool

支持两种模式：
- mock: 本地模拟返回（测试用）
- remote/local_api: 远程 API 调用
"""

import json
import logging
import os
from dataclasses import asdict, dataclass
from typing import Any

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

# 是否启用 MiniCPM
VISION_USE_MINICPM = os.getenv("VISION_USE_MINICPM", "false").lower() == "true"

# MiniCPM 模式: mock / remote / local_api
MINICPM_MODE = os.getenv("MINICPM_MODE", "mock")

# API 基础 URL
MINICPM_BASE_URL = os.getenv("MINICPM_BASE_URL", "")

# 模型名称
MINICPM_MODEL = os.getenv("MINICPM_MODEL", "MiniCPM-V")

# 请求超时（秒）
MINICPM_TIMEOUT = int(os.getenv("MINICPM_TIMEOUT", "60"))


# ========== 数据结构 ==========


@dataclass
class MiniCPMResult:
    """MiniCPM 分析结果"""

    page_type: str  # 页面类型: browser_home, settings_wifi, etc.
    target_found: bool  # 是否找到目标
    target_type: str  # 目标类型: search_box, list_item, button, etc.
    target_label: str  # 目标标签/描述
    bbox: list[float]  # 边界框 [x1, y1, x2, y2]
    center: list[float]  # 中心点 [cx, cy]
    confidence: float  # 置信度 0.0-1.0
    suggested_action: dict[str, Any]  # 建议动作
    reason: str  # 分析理由
    raw_response: dict | None = None  # 原始响应

    def to_dict(self) -> dict:
        return asdict(self)

    def to_grounding_format(self) -> dict:
        """转换为 grounding 格式"""
        return {
            "text": self.target_label,
            "bbox": self.bbox,
            "center": self.center,
            "confidence": self.confidence,
            "element_type": self.target_type,
            "source": "minicpm_vision",
        }

    def to_action_format(self) -> dict:
        """转换为动作格式"""
        action = self.suggested_action.copy()
        action["reason"] = self.reason
        action["confidence"] = self.confidence
        action["source"] = "minicpm_vision"
        return action


# ========== Mock 数据 ==========

# Mock 模式下的预设响应
MOCK_RESPONSES = {
    "browser_home": {
        "page_type": "browser_home",
        "target_found": True,
        "target_type": "search_box",
        "target_label": "搜索",
        "bbox": [450, 100, 630, 180],
        "center": [540, 140],
        "confidence": 0.86,
        "suggested_action": {"action": "tap", "params": {"x": 540, "y": 140}},
        "reason": "检测到顶部搜索框",
    },
    "settings_home": {
        "page_type": "settings_home",
        "target_found": True,
        "target_type": "list_item",
        "target_label": "Wi-Fi",
        "bbox": [50, 300, 1030, 400],
        "center": [540, 350],
        "confidence": 0.92,
        "suggested_action": {"action": "tap", "params": {"x": 540, "y": 350}},
        "reason": "检测到 Wi-Fi 设置项",
    },
    "settings_wifi": {
        "page_type": "settings_wifi",
        "target_found": True,
        "target_type": "toggle",
        "target_label": "Wi-Fi 开关",
        "bbox": [900, 150, 1030, 250],
        "center": [965, 200],
        "confidence": 0.88,
        "suggested_action": {"action": "tap", "params": {"x": 965, "y": 200}},
        "reason": "检测到 Wi-Fi 开关",
    },
    "settings_bluetooth": {
        "page_type": "settings_bluetooth",
        "target_found": True,
        "target_type": "toggle",
        "target_label": "蓝牙开关",
        "bbox": [900, 150, 1030, 250],
        "center": [965, 200],
        "confidence": 0.88,
        "suggested_action": {"action": "tap", "params": {"x": 965, "y": 200}},
        "reason": "检测到蓝牙开关",
    },
    "unknown": {
        "page_type": "unknown",
        "target_found": False,
        "target_type": "",
        "target_label": "",
        "bbox": [],
        "center": [],
        "confidence": 0.0,
        "suggested_action": {"action": "none", "params": {}},
        "reason": "无法识别页面内容",
    },
}


# ========== MiniCPM 客户端类 ==========


class MiniCPMClient:
    """MiniCPM 视觉增强客户端"""

    def __init__(
        self, mode: str = "mock", base_url: str = "", model: str = "MiniCPM-V", timeout: int = 60
    ):
        """
        初始化 MiniCPM 客户端

        Args:
            mode: 运行模式 (mock / remote / local_api)
            base_url: API 基础 URL
            model: 模型名称
            timeout: 请求超时（秒）
        """
        self.mode = mode
        self.base_url = base_url
        self.model = model
        self.timeout = timeout

        logger.info(
            f"MiniCPMClient 初始化: mode={mode}, base_url={base_url}, "
            f"model={model}, timeout={timeout}"
        )

    def is_available(self) -> bool:
        """
        检查 MiniCPM 是否可用

        Returns:
            是否可用
        """
        if self.mode == "mock":
            return True

        if self.mode in ("remote", "local_api"):
            return bool(self.base_url)

        return False

    def analyze_screen(
        self, image_path: str, task: str, context: dict | None = None
    ) -> MiniCPMResult:
        """
        分析屏幕并定位目标

        Args:
            image_path: 截图路径
            task: 任务描述（如"点击搜索"、"打开Wi-Fi页面"）
            context: 额外上下文信息

        Returns:
            MiniCPMResult 分析结果
        """
        logger.info(f"MiniCPM 分析屏幕: {image_path}, task={task}")

        if self.mode == "mock":
            return self._mock_analyze(task, context)
        elif self.mode in ("remote", "local_api"):
            return self._remote_analyze(image_path, task, context)
        else:
            # 未知模式，返回空结果
            return self._create_empty_result("unknown_mode")

    def _mock_analyze(self, task: str, context: dict | None = None) -> MiniCPMResult:
        """
        Mock 模式分析 - 返回预设响应

        Args:
            task: 任务描述
            context: 上下文

        Returns:
            MiniCPMResult
        """
        # 根据任务类型返回对应的 mock 响应
        task_lower = task.lower()

        if "搜索" in task or "search" in task_lower:
            mock_key = "browser_home"
        elif "wi-fi" in task_lower or "wifi" in task_lower:
            mock_key = "settings_home"
        elif "蓝牙" in task or "bluetooth" in task_lower:
            mock_key = "settings_bluetooth"
        else:
            # 默认返回 settings_home（因为这是最常见的测试场景）
            mock_key = "settings_home"

        mock_data = MOCK_RESPONSES.get(mock_key, MOCK_RESPONSES["unknown"])

        logger.info(f"Mock 模式返回: {mock_key}")

        return MiniCPMResult(
            page_type=mock_data["page_type"],
            target_found=mock_data["target_found"],
            target_type=mock_data["target_type"],
            target_label=mock_data["target_label"],
            bbox=mock_data["bbox"],
            center=mock_data["center"],
            confidence=mock_data["confidence"],
            suggested_action=mock_data["suggested_action"],
            reason=mock_data["reason"],
            raw_response=mock_data,
        )

    def _remote_analyze(
        self, image_path: str, task: str, context: dict | None = None
    ) -> MiniCPMResult:
        """
        远程 API 模式分析

        支持两种 API 格式：
        1. /infer 端点（我们的 mock server）
        2. /v1/chat/completions 端点（OpenAI 兼容）

        Args:
            image_path: 截图路径
            task: 任务描述
            context: 上下文

        Returns:
            MiniCPMResult
        """
        import requests

        if not self.base_url:
            logger.error("MiniCPM base_url 未配置")
            return self._create_empty_result("no_url")

        # 读取图片为 base64
        try:
            import base64

            if os.path.exists(image_path):
                with open(image_path, "rb") as f:
                    image_b64 = base64.b64encode(f.read()).decode("utf-8")
            else:
                # 图片不存在时使用空字符串（mock server 不需要真实图片）
                logger.warning(f"图片不存在: {image_path}，使用空 base64")
                image_b64 = ""
        except Exception as e:
            logger.error(f"读取图片失败: {e}")
            return self._create_empty_result("image_read_error")

        headers = {"Content-Type": "application/json"}

        # 检测 API 端点类型
        # 如果 base_url 包含 /infer，使用 /infer 端点
        # 否则使用 OpenAI 兼容的 /v1/chat/completions 端点
        if "/infer" in self.base_url or "/v1" not in self.base_url:
            # 使用我们的 /infer 端点
            url = self.base_url
            if not url.endswith("/infer"):
                url = f"{self.base_url}/infer"

            payload = {"image_base64": image_b64, "task": task}
        else:
            # 使用 OpenAI 兼容的 /v1/chat/completions 端点
            url = f"{self.base_url}/v1/chat/completions"

            # 构建 prompt
            prompt = self._build_prompt(task, context)

            # 请求体
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                            },
                        ],
                    }
                ],
                "max_tokens": 512,
            }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=self.timeout)

            if response.status_code == 200:
                result = response.json()

                # 检测响应格式
                if "/infer" in url:
                    # 我们的 /infer 端点返回格式
                    return self._parse_infer_response(result)
                else:
                    # OpenAI 格式
                    return self._parse_response(result)
            else:
                logger.error(f"MiniCPM API 错误: {response.status_code}, {response.text}")
                return self._create_empty_result("api_error")

        except requests.exceptions.Timeout:
            logger.error("MiniCPM API 超时")
            return self._create_empty_result("timeout")
        except Exception as e:
            logger.error(f"MiniCPM API 异常: {e}")
            return self._create_empty_result("exception")

    def _parse_infer_response(self, response: dict) -> MiniCPMResult:
        """
        解析 /infer 端点响应

        Args:
            response: API 响应

        Returns:
            MiniCPMResult
        """
        try:
            # /infer 端点返回格式
            target_found = response.get("target_found", False)
            target_type = response.get("target_type", "")
            bbox = response.get("bbox", [])
            confidence = response.get("confidence", 0.0)
            reason = response.get("reason", "")

            # 验证 bbox 有效性
            if not self._validate_bbox(bbox):
                logger.warning(f"无效的 bbox: {bbox}")
                return self._create_empty_result("invalid_bbox")

            # 计算中心点（带边缘保护）
            center = self._calculate_center_with_safety(bbox)

            # 构建 suggested_action
            suggested_action = {"action": "tap", "params": {"x": center[0], "y": center[1]}}

            return MiniCPMResult(
                page_type="unknown",  # /infer 端点不返回 page_type
                target_found=target_found,
                target_type=target_type,
                target_label=target_type,  # 使用 target_type 作为 label
                bbox=bbox,
                center=center,
                confidence=confidence,
                suggested_action=suggested_action,
                reason=reason,
                raw_response=response,
            )

        except Exception as e:
            logger.error(f"/infer 响应解析错误: {e}")
            return self._create_empty_result("response_error")

    def _build_prompt(self, task: str, context: dict | None) -> str:
        """
        构建分析 prompt - 超严格版本（子任务 2）

        Args:
            task: 任务描述
            context: 上下文

        Returns:
            prompt 字符串
        """
        # 超严格 prompt - 只返回 JSON，不要解释
        prompt = f"""你在分析 Samsung Galaxy Z Flip3 手机截图。

任务：{task}

请只返回 JSON，不要解释，不要输出多余内容：

{{
  "target_found": true/false,
  "target_type": "search_box / wifi_item / bluetooth_item / button / list_item / toggle",
  "target_label": "目标描述",
  "bbox": [x1, y1, x2, y2],
  "center": [cx, cy],
  "confidence": 0.0-1.0,
  "reason": "简短理由"
}}

重要：
- bbox 坐标基于 1080x2640 屏幕
- 必须返回有效的 JSON
- 不要返回任何其他内容"""

        if context:
            # 添加上下文信息
            ocr_texts = context.get("ocr_texts", [])
            if ocr_texts:
                prompt += f"\n\n已知 OCR 文本: {', '.join(ocr_texts[:10])}"

        return prompt

    def _calculate_center_with_safety(self, bbox: list[float]) -> list[float]:
        """
        计算中心点并应用边缘保护（子任务 3）

        Args:
            bbox: 边界框 [x1, y1, x2, y2]

        Returns:
            中心点 [cx, cy]
        """
        if not bbox or len(bbox) != 4:
            return [0, 0]

        x1, y1, x2, y2 = bbox

        # 计算原始中心点
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2

        # 边缘保护：不允许点击边缘 5%
        screen_width = 1080
        screen_height = 2640
        margin_x = screen_width * 0.05
        margin_y = screen_height * 0.05

        # 限制在安全范围内
        cx = max(margin_x, min(screen_width - margin_x, cx))
        cy = max(margin_y, min(screen_height - margin_y, cy))

        return [int(cx), int(cy)]

    def _validate_bbox(self, bbox: list[float]) -> bool:
        """
        验证 bbox 是否有效

        Args:
            bbox: 边界框

        Returns:
            是否有效
        """
        if not bbox or len(bbox) != 4:
            return False

        x1, y1, x2, y2 = bbox

        # 检查坐标是否合理
        if x2 <= x1 or y2 <= y1:
            return False

        # 检查是否在屏幕范围内
        if x1 < 0 or y1 < 0 or x2 > 1080 or y2 > 2640:
            return False

        # 检查 bbox 大小是否合理（不能太小也不能太大）
        width = x2 - x1
        height = y2 - y1

        # 最小 20x20 像素
        if width < 20 or height < 20:
            return False

        # 最大不超过屏幕 95%（放宽限制以支持列表项等大元素）
        return not (width > 1080 * 0.95 or height > 2640 * 0.95)

    def _parse_response(self, response: dict) -> MiniCPMResult:
        """
        解析 API 响应（子任务 1 + 3）

        Args:
            response: API 响应

        Returns:
            MiniCPMResult
        """
        try:
            # 提取 content
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")

            # 尝试解析 JSON
            # 可能是纯 JSON，也可能是带 markdown 的
            import re

            json_match = re.search(r"\{.*\}", content, re.DOTALL)

            if json_match:
                data = json.loads(json_match.group())

                # 获取 bbox
                bbox = data.get("bbox", [])

                # 验证 bbox 有效性
                if not self._validate_bbox(bbox):
                    logger.warning(f"无效的 bbox: {bbox}")
                    return self._create_empty_result("invalid_bbox")

                # 计算中心点（带边缘保护）
                center = self._calculate_center_with_safety(bbox)

                # 构建 suggested_action
                suggested_action = {"action": "tap", "params": {"x": center[0], "y": center[1]}}

                return MiniCPMResult(
                    page_type=data.get("page_type", "unknown"),
                    target_found=data.get("target_found", False),
                    target_type=data.get("target_type", ""),
                    target_label=data.get("target_label", ""),
                    bbox=bbox,
                    center=center,
                    confidence=data.get("confidence", 0.0),
                    suggested_action=suggested_action,
                    reason=data.get("reason", ""),
                    raw_response=response,
                )
            else:
                logger.warning("无法从响应中解析 JSON")
                return self._create_empty_result("parse_error")

        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析错误: {e}")
            return self._create_empty_result("json_error")
        except Exception as e:
            logger.error(f"响应解析错误: {e}")
            return self._create_empty_result("response_error")

    def _create_empty_result(self, error_type: str) -> MiniCPMResult:
        """
        创建空结果

        Args:
            error_type: 错误类型

        Returns:
            MiniCPMResult
        """
        return MiniCPMResult(
            page_type="unknown",
            target_found=False,
            target_type="",
            target_label="",
            bbox=[],
            center=[],
            confidence=0.0,
            suggested_action={"action": "none", "params": {}},
            reason=f"分析失败: {error_type}",
            raw_response=None,
        )


# ========== 全局单例 ==========

_minicpm_client: MiniCPMClient | None = None


def get_minicpm_client() -> MiniCPMClient:
    """获取全局 MiniCPM 客户端"""
    global _minicpm_client

    if _minicpm_client is None:
        _minicpm_client = MiniCPMClient(
            mode=MINICPM_MODE,
            base_url=MINICPM_BASE_URL,
            model=MINICPM_MODEL,
            timeout=MINICPM_TIMEOUT,
        )

    return _minicpm_client


def reset_minicpm_client():
    """重置 MiniCPM 客户端"""
    global _minicpm_client
    _minicpm_client = None


# ========== 便捷函数 ==========


def analyze_screen(image_path: str, task: str, context: dict | None = None) -> MiniCPMResult:
    """
    分析屏幕（便捷函数）

    Args:
        image_path: 截图路径
        task: 任务描述
        context: 额外上下文

    Returns:
        MiniCPMResult
    """
    client = get_minicpm_client()
    return client.analyze_screen(image_path, task, context)


def is_minicpm_available() -> bool:
    """检查 MiniCPM 是否可用"""
    client = get_minicpm_client()
    return client.is_available()


# ========== 测试 ==========

if __name__ == "__main__":
    print("=== MiniCPM Client 测试 ===")

    # 测试 mock 模式
    client = MiniCPMClient(mode="mock")
    print(f"\n1. Mock 模式可用: {client.is_available()}")

    # 测试"点击搜索"
    result = client.analyze_screen("/fake/screen.png", "点击搜索")
    print("\n2. 分析 '点击搜索':")
    print(f"   page_type: {result.page_type}")
    print(f"   target_found: {result.target_found}")
    print(f"   target_type: {result.target_type}")
    print(f"   target_label: {result.target_label}")
    print(f"   center: {result.center}")
    print(f"   confidence: {result.confidence}")
    print(f"   suggested_action: {result.suggested_action}")
    print(f"   reason: {result.reason}")

    # 测试"打开Wi-Fi页面"
    result = client.analyze_screen("/fake/screen.png", "打开Wi-Fi页面")
    print("\n3. 分析 '打开Wi-Fi页面':")
    print(f"   page_type: {result.page_type}")
    print(f"   target_found: {result.target_found}")
    print(f"   target_label: {result.target_label}")
    print(f"   center: {result.center}")

    # 测试"打开蓝牙页面"
    result = client.analyze_screen("/fake/screen.png", "打开蓝牙页面")
    print("\n4. 分析 '打开蓝牙页面':")
    print(f"   page_type: {result.page_type}")
    print(f"   target_found: {result.target_found}")
    print(f"   target_label: {result.target_label}")
    print(f"   center: {result.center}")

    print("\n=== 测试完成 ===")
