"""
State Detector - 页面状态检测 (Phase 11.5 强化版)

基于多维信号的打分制状态识别：
- OCR 文本信号（关键词组合）
- UI 元素信号（search_box, list_item, back_button, bottom_nav）
- 布局/区域信号（图标分布、列表项、搜索区域）
- 历史动作信号（上一步操作推断）

输出格式：
{
  "state": "settings_home",
  "confidence": 0.82,
  "signals": ["设置", "Wi-Fi", "蓝牙"],
  "score_breakdown": {
    "keyword_score": 0.5,
    "layout_score": 0.2,
    "history_score": 0.1,
    "ocr_density_score": 0.02
  }
}
"""

import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# 日志文件
STATE_LOG = "os.path.join(os.path.dirname(os.path.abspath(__file__)), '../logs/state.log')"

# 配置日志
if os.path.exists(os.path.dirname(STATE_LOG)):
    file_handler = logging.FileHandler(STATE_LOG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(file_handler)


# 最小状态枚举 (只支持 3 个状态)
LITE_STATES = ["home_screen", "settings_home", "browser_home", "unknown"]

# 配置项
STATE_CONFIDENCE_THRESHOLD = float(os.getenv("STATE_CONFIDENCE_THRESHOLD", "0.65"))
STATE_USE_HISTORY_SIGNAL = os.getenv("STATE_USE_HISTORY_SIGNAL", "true").lower() == "true"


@dataclass
class ScoreBreakdown:
    """打分明细"""

    keyword_score: float = 0.0
    layout_score: float = 0.0
    history_score: float = 0.0
    ocr_density_score: float = 0.0

    def total(self) -> float:
        return self.keyword_score + self.layout_score + self.history_score + self.ocr_density_score

    def to_dict(self) -> dict:
        return {
            "keyword_score": round(self.keyword_score, 3),
            "layout_score": round(self.layout_score, 3),
            "history_score": round(self.history_score, 3),
            "ocr_density_score": round(self.ocr_density_score, 3),
            "total": round(self.total(), 3),
        }


@dataclass
class DetectionResult:
    """检测结果"""

    state: str  # "home_screen", "settings_home", "browser_home", "unknown"
    confidence: float
    signals: list[str]
    source: str = "ocr"
    details: dict = field(default_factory=dict)
    score_breakdown: ScoreBreakdown | None = None

    def to_dict(self) -> dict:
        result = {
            "state": self.state,
            "confidence": round(self.confidence, 3),
            "signals": self.signals,
            "source": self.source,
            "details": self.details or {},
        }
        if self.score_breakdown:
            result["score_breakdown"] = self.score_breakdown.to_dict()
        return result


# 状态关键词组合（比单关键词更精确）
# Phase 12 扩展：新增 search_page, settings_wifi, settings_bluetooth
LITE_STATE_KEYWORD_COMBOS = {
    "home_screen": {
        "core": [
            "抖音",
            "微信",
            "淘宝",
            "支付宝",
            "微博",
            "相机",
            "天气",
            "时钟",
            "文件管理",
            "应用",
            "设置",
            "Google",
            "home",
            "主屏幕",
            "桌面",
        ],
        "auxiliary": [
            "文件夹",
            "小组件",
            "壁纸",
            "搜索",
            "更多",
            "通讯录",
            "短信",
            "电话",
            "音乐",
            "视频",
            "浏览器",
            "下载",
            "游戏",
            "计算器",
            "日历",
        ],
    },
    "settings_home": {
        "core": [
            "设置",
            "Wi-Fi",
            "WLAN",
            "蓝牙",
            "显示",
            "声音",
            "应用程序",
            "网络",
            "settings",
            "飞行模式",
            "移动网络",
        ],
        "auxiliary": ["连接", "通知", "应用", "存储", "电池", "安全", "关于", "更多连接"],
    },
    "settings_wifi": {
        "core": ["Wi-Fi", "WLAN", "无线网络"],
        "auxiliary": [
            "网络",
            "开关",
            "已连接",
            "可用网络",
            "WPA",
            "WPA2",
            "密码",
            "显示密码",
            "高级",
            "代理",
            "IP",
            "网关",
        ],
    },
    "settings_bluetooth": {
        "core": ["蓝牙", "bluetooth"],
        "auxiliary": [
            "设备",
            "可见性",
            "已连接",
            "可用设备",
            "已配对",
            "扫描",
            "重命名",
            "接收文件",
            "关闭",
        ],
    },
    "browser_home": {
        "core": [
            "Google",
            "chrome",
            "浏览器",
            "搜索",
            "地址",
            "browser",
            "www",
            "输入网址",
            "输入搜索",
        ],
        "auxiliary": ["搜索或输入网址", "书签", "历史记录", "标签页"],
    },
    "search_page": {
        "core": ["搜索", "search", "输入"],
        "auxiliary": [
            "建议",
            "历史记录",
            "结果",
            "搜索结果",
            "热门搜索",
            "输入搜索内容",
            "请输入",
            "清除",
        ],
    },
}

# 布局特征权重
LAYOUT_FEATURES = {
    "home_screen": {
        # 主屏幕：图标网格分布，底部有应用栏
        "icon_grid": 0.15,
        "bottom_nav": 0.10,
        "dock_apps": 0.08,
    },
    "settings_home": {
        # 设置页：垂直列表项，右侧箭头
        "vertical_list": 0.20,
        "list_item": 0.15,
        "back_button": 0.08,
    },
    "browser_home": {
        # 浏览器：顶部搜索/地址栏
        "search_box": 0.20,
        "address_bar": 0.18,
        "bottom_toolbar": 0.08,
    },
}


class StateDetector:
    """页面状态检测器 (Phase 11.5 强化版 - 打分制)"""

    def __init__(self, confidence_threshold: float = 0.65):
        self.confidence_threshold = confidence_threshold
        logger.info(f"StateDetector (Phase 11.5) 初始化: threshold={confidence_threshold}")

    def detect_page_state(
        self,
        ocr_results: list[str] = None,
        image_path: str = None,
        screen_analysis: dict = None,
        history: list[dict] = None,
    ) -> DetectionResult:
        """
        检测页面状态 (打分制)

        Args:
            ocr_results: OCR 识别到的文本列表
            image_path: 截图路径（可选）
            screen_analysis: 屏幕分析结果（可选）
            history: 历史动作记录（可选）

        Returns:
            DetectionResult: 检测结果
        """
        # 如果没有 OCR 结果，尝试从截图获取
        if not ocr_results and image_path and os.path.exists(image_path):
            ocr_results = self._extract_text_from_image(image_path)

        # 如果没有 OCR 结果，尝试从 screen_analysis 获取
        if not ocr_results and screen_analysis:
            ocr_results = self._extract_from_screen_analysis(screen_analysis)

        # 如果仍然没有文本，返回 unknown
        if not ocr_results:
            logger.warning("无法获取 OCR 结果，返回 unknown 状态")
            return DetectionResult(
                state="unknown",
                confidence=0.0,
                signals=[],
                source="none",
                score_breakdown=ScoreBreakdown(),
            )

        # 提取 UI 元素信息
        ui_elements = self._extract_ui_elements(screen_analysis)

        # 使用打分制检测状态
        return self._detect_with_scoring(ocr_results, ui_elements, history)

    def _extract_from_screen_analysis(self, screen_analysis: dict) -> list[str]:
        """从 screen_analysis 提取文本"""
        ocr_results = []

        if "text_blocks" in screen_analysis:
            ocr_results = [tb.get("text", "") for tb in screen_analysis["text_blocks"]]
        elif "high_confidence_texts" in screen_analysis:
            ocr_results = screen_analysis["high_confidence_texts"]
        elif "ocr_top_texts" in screen_analysis:
            ocr_results = screen_analysis["ocr_top_texts"]

        return ocr_results

    def _extract_ui_elements(self, screen_analysis: dict) -> dict:
        """从 screen_analysis 提取 UI 元素信息"""
        ui_elements = {
            "has_search_box": False,
            "has_list_item": False,
            "has_back_button": False,
            "has_bottom_nav": False,
            "has_icon_grid": False,
            "has_vertical_list": False,
            "has_address_bar": False,
            "has_bottom_toolbar": False,
            "ui_elements_count": 0,
            "element_types": [],
        }

        if not screen_analysis:
            return ui_elements

        # 从 ui_elements 提取
        if "ui_elements" in screen_analysis:
            ui_elements["ui_elements_count"] = len(screen_analysis["ui_elements"])

            for elem in screen_analysis["ui_elements"]:
                elem_type = elem.get("element_type", "")
                ui_elements["element_types"].append(elem_type)

                if elem_type in ["search_box", "search_input"]:
                    ui_elements["has_search_box"] = True
                if elem_type in ["list_item", "list"]:
                    ui_elements["has_list_item"] = True
                if elem_type == "back_button":
                    ui_elements["has_back_button"] = True
                if elem_type in ["bottom_nav", "navigation_bar"]:
                    ui_elements["has_bottom_nav"] = True
                if elem_type in ["icon", "app_icon", "icon_grid"]:
                    ui_elements["has_icon_grid"] = True
                if elem_type in ["address_bar", "url_bar"]:
                    ui_elements["has_address_bar"] = True
                if elem_type in ["toolbar", "bottom_toolbar"]:
                    ui_elements["has_bottom_toolbar"] = True

        return ui_elements

    def _extract_text_from_image(self, image_path: str) -> list[str]:
        """从图片提取文本（需要 EasyOCR）"""
        try:
            from vision.ocr_engine import get_ocr_engine

            ocr_engine = get_ocr_engine(provider="easyocr")
            results = ocr_engine.extract_text(image_path)

            return [r.text for r in results]
        except Exception as e:
            logger.warning(f"OCR 提取失败: {e}")
            return []

    def _calculate_keyword_score(
        self, ocr_results: list[str], state: str
    ) -> tuple[float, list[str]]:
        """计算关键词得分 - Phase 11.5 优化版：每个匹配直接加分"""
        keyword_combo = LITE_STATE_KEYWORD_COMBOS.get(state, {})
        core_keywords = keyword_combo.get("core", [])
        auxiliary_keywords = keyword_combo.get("auxiliary", [])

        matched_core = []
        matched_auxiliary = []

        for text in ocr_results:
            text_lower = text.lower()

            # 检查核心关键词
            for kw in core_keywords:
                if kw.lower() in text_lower and kw not in matched_core:
                    matched_core.append(kw)
                    break

            # 检查辅助关键词
            for kw in auxiliary_keywords:
                if kw.lower() in text_lower and kw not in matched_auxiliary:
                    matched_auxiliary.append(kw)
                    break

        # Phase 11.5 优化：每个匹配直接加分，更激进
        # 核心关键词每个 0.15 分，辅助关键词每个 0.08 分
        # 最高 0.7 分封顶
        core_score = min(len(matched_core) * 0.15, 0.7)
        aux_score = min(len(matched_auxiliary) * 0.08, 0.3)

        total_score = min(core_score + aux_score, 1.0)
        all_matched = matched_core + matched_auxiliary

        return total_score, all_matched

    def _calculate_layout_score(self, ui_elements: dict, state: str) -> float:
        """计算布局得分"""
        layout_features = LAYOUT_FEATURES.get(state, {})

        score = 0.0

        if state == "home_screen":
            if ui_elements.get("has_icon_grid"):
                score += layout_features.get("icon_grid", 0.15)
            if ui_elements.get("has_bottom_nav"):
                score += layout_features.get("bottom_nav", 0.10)

        elif state == "settings_home":
            if ui_elements.get("has_vertical_list") or ui_elements.get("has_list_item"):
                score += layout_features.get("vertical_list", 0.20)
            if ui_elements.get("has_list_item"):
                score += layout_features.get("list_item", 0.15)
            if ui_elements.get("has_back_button"):
                score += layout_features.get("back_button", 0.08)

        elif state == "browser_home":
            if ui_elements.get("has_search_box"):
                score += layout_features.get("search_box", 0.20)
            if ui_elements.get("has_address_bar"):
                score += layout_features.get("address_bar", 0.18)
            if ui_elements.get("has_bottom_toolbar"):
                score += layout_features.get("bottom_toolbar", 0.08)

        return min(score, 1.0)

    def _calculate_history_score(self, history: list[dict], state: str) -> float:
        """计算历史动作得分"""
        if not history or not STATE_USE_HISTORY_SIGNAL:
            return 0.0

        # 获取最近的动作
        recent_actions = []
        for h in history[-3:]:
            action = h.get("action", "") or h.get("task", "")
            recent_actions.append(action)

        score = 0.0

        # 根据上一步动作推断当前状态
        if state == "settings_home":
            if any("打开设置" in a or "tap_settings" in a for a in recent_actions):
                score = 0.5
            elif any("设置" in a for a in recent_actions):
                score = 0.3

        elif state == "browser_home":
            if any("打开浏览器" in a or "tap_browser" in a for a in recent_actions):
                score = 0.5
            elif any("浏览器" in a or "chrome" in a for a in recent_actions):
                score = 0.3

        elif state == "home_screen":
            if any("回到主屏幕" in a or "home" in a for a in recent_actions):
                score = 0.5
            elif any("返回" in a or "back" in a for a in recent_actions):
                score = 0.2

        return score

    def _calculate_ocr_density_score(self, ocr_results: list[str]) -> float:
        """计算 OCR 文本密度得分"""
        if not ocr_results:
            return 0.0

        # 文本块数量
        text_count = len(ocr_results)

        # 密度得分：10-30 个文本块得满分
        density_score = min(text_count / 20.0, 1.0) * 0.1

        return density_score

    def _calculate_negative_penalty(self, ocr_results: list[str], state: str) -> float:
        """Phase 12: 计算负向关键词惩罚"""
        # 负向关键词定义
        negative_keywords_map = {
            "home_screen": ["设置", "Wi-Fi", "蓝牙", "搜索", "地址", "chrome", "浏览器"],
            "settings_home": ["抖音", "微信", "淘宝", "浏览器", "相机"],
            "settings_wifi": ["蓝牙", "显示", "声音", "应用", "相机"],
            "settings_bluetooth": ["Wi-Fi", "显示", "声音", "应用", "相机"],
            "browser_home": ["抖音", "微信", "设置", "相机"],
            "search_page": ["设置", "Wi-Fi", "蓝牙", "相机", "文件"],
        }

        negative_keywords = negative_keywords_map.get(state, [])

        penalty = 0.0
        for text in ocr_results:
            text_lower = text.lower()
            for neg_kw in negative_keywords:
                if neg_kw.lower() in text_lower:
                    penalty += 0.15  # 每个负向关键词扣 0.15 分
                    break

        return min(penalty, 0.5)  # 最高扣 0.5 分

    def _detect_with_scoring(
        self, ocr_results: list[str], ui_elements: dict, history: list[dict] = None
    ) -> DetectionResult:
        """使用打分制检测状态 - Phase 12 扩展：支持 6 种状态"""

        # Phase 12: 支持 6 种状态
        supported_states = [
            "home_screen",
            "settings_home",
            "settings_wifi",
            "settings_bluetooth",
            "browser_home",
            "search_page",
        ]

        # 计算每个状态的得分
        state_scores: dict[str, dict] = {}

        for state in supported_states:
            # 1. 关键词得分
            keyword_score, matched_keywords = self._calculate_keyword_score(ocr_results, state)

            # 2. 布局得分
            layout_score = self._calculate_layout_score(ui_elements, state)

            # 3. 历史动作得分
            history_score = self._calculate_history_score(history, state)

            # 4. OCR 密度得分
            ocr_density_score = self._calculate_ocr_density_score(ocr_results)

            # 5. Phase 12: 负向关键词惩罚
            negative_penalty = self._calculate_negative_penalty(ocr_results, state)

            # 总分（减去负向惩罚）
            total_score = (
                keyword_score + layout_score + history_score + ocr_density_score - negative_penalty
            )

            state_scores[state] = {
                "total": total_score,
                "keyword_score": keyword_score,
                "layout_score": layout_score,
                "history_score": history_score,
                "ocr_density_score": ocr_density_score,
                "negative_penalty": negative_penalty,
                "matched_keywords": matched_keywords,
            }

            logger.info(
                f"状态 {state} 打分: "
                f"keyword={keyword_score:.2f}, layout={layout_score:.2f}, "
                f"history={history_score:.2f}, density={ocr_density_score:.2f}, "
                f"penalty={negative_penalty:.2f}, total={total_score:.2f}"
            )

        # 选择得分最高的状态
        best_state = max(state_scores.keys(), key=lambda s: state_scores[s]["total"])
        best_score = state_scores[best_state]

        # 置信度 = 归一化的总分（最高 1.0）
        confidence = min(best_score["total"], 1.0)

        # 如果最高分低于阈值，返回 unknown
        if confidence < self.confidence_threshold:
            logger.info(
                f"置信度 {confidence:.2f} 低于阈值 {self.confidence_threshold}，返回 unknown"
            )
            return DetectionResult(
                state="unknown",
                confidence=confidence,
                signals=[],
                source="scoring",
                score_breakdown=ScoreBreakdown(
                    keyword_score=best_score["keyword_score"],
                    layout_score=best_score["layout_score"],
                    history_score=best_score["history_score"],
                    ocr_density_score=best_score["ocr_density_score"],
                ),
            )

        # 构建 score_breakdown
        score_breakdown = ScoreBreakdown(
            keyword_score=best_score["keyword_score"],
            layout_score=best_score["layout_score"],
            history_score=best_score["history_score"],
            ocr_density_score=best_score["ocr_density_score"],
        )

        logger.info(
            f"页面状态检测 (Phase 11.5): {best_state}, "
            f"置信度: {confidence:.2f}, 信号: {best_score['matched_keywords']}"
        )

        return DetectionResult(
            state=best_state,
            confidence=confidence,
            signals=best_score["matched_keywords"],
            source="scoring",
            score_breakdown=score_breakdown,
            details={"all_scores": {s: round(state_scores[s]["total"], 3) for s in state_scores}},
        )

    def detect_with_screen_analyzer(
        self, screen_analysis: dict, history: list[dict] = None
    ) -> DetectionResult:
        """使用 ScreenAnalyzer 的结果检测状态"""
        ocr_results = self._extract_from_screen_analysis(screen_analysis)
        ui_elements = self._extract_ui_elements(screen_analysis)
        return self._detect_with_scoring(ocr_results, ui_elements, history)


# 全局检测器
_detector: StateDetector | None = None


def detect_page_state(
    ocr_results: list[str] = None,
    image_path: str = None,
    screen_analysis: dict = None,
    history: list[dict] = None,
    confidence_threshold: float = 0.65,
) -> DetectionResult:
    """快速检测页面状态 (Phase 11.5)"""
    global _detector

    if _detector is None:
        _detector = StateDetector(confidence_threshold=confidence_threshold)

    if screen_analysis:
        return _detector.detect_with_screen_analyzer(screen_analysis, history)

    return _detector.detect_page_state(ocr_results, image_path, screen_analysis, history)


def reset_detector():
    """重置检测器"""
    global _detector
    _detector = None
