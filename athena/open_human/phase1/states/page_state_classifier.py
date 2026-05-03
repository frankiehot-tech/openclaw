"""
Page State Classifier for Phase 1 - Phase 1 页面状态分类器

基于关键词和规则识别当前页面状态，用于 Athena Open Human Phase 1 发布流程。
仅做分类，不实现发布流程、不实现真实设备动作、不实现表单填写。
"""

from dataclasses import asdict, dataclass

from .page_state_schema import STATE_KEYWORDS, STATE_PRIORITIES, Phase1PageState


@dataclass
class PageStateResult:
    """页面状态分类结果"""

    page_state: str  # 字符串状态值
    confidence: float  # 置信度 0~1
    evidence: list[str]  # 证据列表（命中的关键词或锚点）

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "PageStateResult":
        """从字典创建"""
        return cls(**data)


class PageStateClassifier:
    """页面状态分类器"""

    def __init__(self):
        """初始化分类器"""
        self._state_priorities = STATE_PRIORITIES
        self._state_keywords = STATE_KEYWORDS

    def classify(
        self, app_package: str, current_package: str, vision_text: str, ui_anchors: list[str]
    ) -> PageStateResult:
        """
        分类当前页面状态

        Args:
            app_package: 目标 App 包名（如 "com.zhihu"）
            current_package: 当前页面所属 App 包名
            vision_text: 视觉识别到的文本（OCR 结果）
            ui_anchors: UI 锚点列表（如按钮文本、图标标签等）

        Returns:
            PageStateResult: 分类结果
        """
        # 规则1: 如果当前包名与目标包名不匹配，优先判定 OUT_OF_SCOPE
        if current_package != app_package:
            return PageStateResult(
                page_state=Phase1PageState.OUT_OF_SCOPE.value,
                confidence=1.0,
                evidence=[f"package_mismatch: current={current_package}, target={app_package}"],
            )

        # 合并所有文本信息用于匹配
        all_text = self._combine_text_sources(vision_text, ui_anchors)

        # 检测各种页面状态
        detected_states = self._detect_states(all_text)

        # 根据优先级选择最可能的状态
        final_state = self._select_state_by_priority(detected_states)

        # 计算置信度
        confidence = self._calculate_confidence(final_state, detected_states, all_text)

        # 收集证据
        evidence = self._collect_evidence(final_state, all_text)

        return PageStateResult(
            page_state=final_state.value, confidence=confidence, evidence=evidence
        )

    def _combine_text_sources(self, vision_text: str, ui_anchors: list[str]) -> str:
        """合并所有文本源"""
        # 将 vision_text 和 ui_anchors 合并为一个字符串，用于关键词匹配
        ui_text = " ".join(ui_anchors) if ui_anchors else ""
        combined = f"{vision_text} {ui_text}".strip()
        return combined

    def _detect_states(self, text: str) -> list[Phase1PageState]:
        """检测所有可能的状态"""
        detected = []
        text_lower = text.lower()

        # 检查每种状态的关键词
        for state, keywords in self._state_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    detected.append(state)
                    break  # 每个状态只要匹配到一个关键词即可

        # 如果没有检测到任何具体状态，返回 UNKNOWN 或 APP_HOME（基础状态）
        if not detected:
            # 如果有足够文本但没有匹配到具体状态，可能是 APP_HOME
            if len(text) > 10:  # 有足够文本内容
                detected.append(Phase1PageState.APP_HOME)
            else:
                detected.append(Phase1PageState.UNKNOWN)

        return detected

    def _select_state_by_priority(self, states: list[Phase1PageState]) -> Phase1PageState:
        """根据优先级选择状态（解决规则冲突）"""
        if not states:
            return Phase1PageState.UNKNOWN

        # 按优先级排序，优先级高的在前
        sorted_states = sorted(states, key=lambda s: self._state_priorities.get(s, 0), reverse=True)

        return sorted_states[0]

    def _calculate_confidence(
        self, selected_state: Phase1PageState, all_detected_states: list[Phase1PageState], text: str
    ) -> float:
        """计算置信度"""
        # 基础置信度规则
        base_confidence = 0.5

        # 规则1: 如果只有一个状态被检测到，置信度较高
        if len(all_detected_states) == 1:
            base_confidence += 0.3

        # 规则2: 如果文本长度足够，置信度增加
        text_length = len(text)
        if text_length > 50:
            base_confidence += 0.1
        elif text_length > 20:
            base_confidence += 0.05

        # 规则3: 根据状态优先级调整置信度
        state_priority = self._state_priorities.get(selected_state, 0)
        if state_priority >= 70:  # 高风险/高优先级状态
            base_confidence += 0.1

        # 规则4: 如果状态是 UNKNOWN，置信度较低
        if selected_state == Phase1PageState.UNKNOWN:
            base_confidence = max(0.2, base_confidence - 0.2)

        # 确保在 0~1 范围内
        confidence = max(0.0, min(1.0, base_confidence))

        return round(confidence, 2)

    def _collect_evidence(self, state: Phase1PageState, text: str) -> list[str]:
        """收集证据（命中的关键词）"""
        evidence = []
        text_lower = text.lower()

        # 查找状态对应的关键词
        keywords = self._state_keywords.get(state, [])
        for keyword in keywords:
            if keyword.lower() in text_lower:
                evidence.append(f"keyword: {keyword}")

        # 如果没有找到关键词，但状态不是 UNKNOWN，记录文本摘要
        if not evidence and state != Phase1PageState.UNKNOWN:
            # 取前50个字符作为证据
            text_preview = text[:50] + "..." if len(text) > 50 else text
            evidence.append(f"text_context: {text_preview}")

        # 如果状态是 UNKNOWN，记录文本长度作为证据
        if state == Phase1PageState.UNKNOWN:
            evidence.append(f"text_length: {len(text)} chars, no_keyword_match")

        return evidence


# 便捷函数
def classify_page_state(
    app_package: str, current_package: str, vision_text: str, ui_anchors: list[str]
) -> PageStateResult:
    """
    便捷函数：分类页面状态

    Args:
        app_package: 目标 App 包名
        current_package: 当前页面所属 App 包名
        vision_text: 视觉识别到的文本
        ui_anchors: UI 锚点列表

    Returns:
        PageStateResult: 分类结果
    """
    classifier = PageStateClassifier()
    return classifier.classify(app_package, current_package, vision_text, ui_anchors)


# 全局分类器实例（单例模式）
_classifier_instance: PageStateClassifier | None = None


def get_classifier() -> PageStateClassifier:
    """获取全局分类器实例"""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = PageStateClassifier()
    return _classifier_instance
