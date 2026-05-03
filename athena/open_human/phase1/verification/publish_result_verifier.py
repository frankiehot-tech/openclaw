"""
Publish Result Verifier for Phase 1 - Phase 1 发布结果核验器

定义发布后页面状态的判定逻辑，输出标准化判定结果。
仅负责判定，不涉及真实发布执行。
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from athena.open_human.phase1.states.page_state_schema import Phase1PageState


class VerificationResult(StrEnum):
    """核验结果枚举"""

    SUCCESS = "success"
    FAIL = "fail"
    SAFE_STOP = "safe_stop"


@dataclass
class PublishVerificationResult:
    """
    发布核验结果数据类

    Attributes:
        result (str): 核验结果 - success / fail / safe_stop
        page_state (str): 页面状态值（来自 Phase1PageState）
        evidence (list[str]): 判定证据列表
        taxonomy_class (str | None): 分类标识（用于 fail / safe_stop）
        sub_reason (str | None): 子原因（用于 fail / safe_stop）
        metadata (dict[str, Any]): 额外元数据
    """

    result: str  # success / fail / safe_stop
    page_state: str
    evidence: list[str]
    taxonomy_class: str | None = None
    sub_reason: str | None = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        """初始化后处理"""
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "result": self.result,
            "page_state": self.page_state,
            "evidence": self.evidence,
            "taxonomy_class": self.taxonomy_class,
            "sub_reason": self.sub_reason,
            "metadata": self.metadata,
        }


class PublishResultVerifier:
    """
    发布结果核验器

    根据页面状态、视觉文本和UI锚点判定发布结果。
    判定规则写死，不依赖外部服务。
    """

    # 高风险敏感词列表（用于 UNKNOWN 状态判定）
    HIGH_RISK_KEYWORDS = [
        "风险提示",
        "异常操作",
        "安全验证",
        "稍后再试",
        "验证",
        "risk",
        "security",
        "verification",
        "blocked",
        "禁止",
        "警告",
        "warning",
        "suspicious",
        "可疑",
        "封禁",
        "限制",
    ]

    # 成功信号关键词（用于 UNKNOWN 状态避免误判为 success）
    SUCCESS_KEYWORDS = [
        "发布成功",
        "已发布",
        "发送成功",
        "发表成功",
        "publish success",
        "posted",
        "成功",
        "success",
        "完成",
        "done",
    ]

    def verify(
        self, page_state: str, vision_text: str, ui_anchors: list[str]
    ) -> PublishVerificationResult:
        """
        核验发布结果

        Args:
            page_state: 页面状态字符串（Phase1PageState.value）
            vision_text: 视觉分析得到的文本内容
            ui_anchors: UI锚点文本列表

        Returns:
            PublishVerificationResult: 核验结果

        Raises:
            ValueError: 当 page_state 无效时
        """
        # 验证页面状态有效性 - 直接检查是否为有效状态
        valid_states = Phase1PageState.all_states()
        if page_state not in valid_states:
            raise ValueError(f"无效的页面状态: {page_state} (有效状态: {valid_states})")

        state_enum = Phase1PageState.from_string(page_state)

        # 收集所有文本用于关键词检测
        all_text = vision_text.lower()
        for anchor in ui_anchors:
            all_text += " " + anchor.lower()

        # 判定规则写死（按优先级顺序）
        # 1. PUBLISH_SUCCESS -> success
        if state_enum == Phase1PageState.PUBLISH_SUCCESS:
            return self._create_success_result(
                state_enum.value, evidence=[f"页面状态为 {state_enum.value}"]
            )

        # 2. PUBLISH_FAILURE -> fail
        if state_enum == Phase1PageState.PUBLISH_FAILURE:
            return self._create_fail_result(
                state_enum.value,
                evidence=[f"页面状态为 {state_enum.value}"],
                taxonomy_class="action_failed",
                sub_reason="publish_failure_page",
            )

        # 3. RISK_PROMPT -> safe_stop
        if state_enum == Phase1PageState.RISK_PROMPT:
            return self._create_safe_stop_result(
                state_enum.value,
                evidence=[f"页面状态为 {state_enum.value}"],
                taxonomy_class="unsafe_to_continue",
                sub_reason="risk_prompt_detected",
            )

        # 4. UNKNOWN + 高风险/敏感提示词 -> safe_stop
        if state_enum == Phase1PageState.UNKNOWN:
            # 检查是否有高风险关键词
            risk_hits = self._find_keyword_hits(all_text, self.HIGH_RISK_KEYWORDS)
            if risk_hits:
                evidence = [f"UNKNOWN 状态检测到高风险关键词: {', '.join(risk_hits)}"]
                return self._create_safe_stop_result(
                    state_enum.value,
                    evidence=evidence,
                    taxonomy_class="unsafe_to_continue",
                    sub_reason="unknown_sensitive_page",
                )

            # 检查是否有明显成功信号（避免误判）
            success_hits = self._find_keyword_hits(all_text, self.SUCCESS_KEYWORDS)
            if success_hits:
                evidence = [
                    f"UNKNOWN 状态检测到成功关键词，但不允许判为 success: {', '.join(success_hits)}"
                ]
                # 即使有成功信号，UNKNOWN 也不判为 success
                return self._create_safe_stop_result(
                    state_enum.value,
                    evidence=evidence,
                    taxonomy_class="unsafe_to_continue",
                    sub_reason="unknown_state_with_success_hints",
                )

            # 纯 UNKNOWN，无关键词命中 -> safe_stop（保守策略）
            evidence = ["UNKNOWN 状态且未检测到任何关键词"]
            return self._create_safe_stop_result(
                state_enum.value,
                evidence=evidence,
                taxonomy_class="unsafe_to_continue",
                sub_reason="UNKNOWN_state_no_keywords",
            )

        # 5. 其他状态 -> safe_stop（保守策略）
        evidence = [f"非发布结果页面状态: {state_enum.value}"]
        return self._create_safe_stop_result(
            state_enum.value,
            evidence=evidence,
            taxonomy_class="unsafe_to_continue",
            sub_reason="non_result_page_state",
        )

    def _find_keyword_hits(self, text: str, keywords: list[str]) -> list[str]:
        """在文本中查找关键词命中"""
        hits = []
        lower_text = text.lower()
        for keyword in keywords:
            lower_keyword = keyword.lower()
            if lower_keyword in lower_text:
                hits.append(keyword)
        return hits

    def _create_success_result(
        self, page_state: str, evidence: list[str]
    ) -> PublishVerificationResult:
        """创建成功结果"""
        return PublishVerificationResult(
            result=VerificationResult.SUCCESS.value,
            page_state=page_state,
            evidence=evidence,
            taxonomy_class=None,
            sub_reason=None,
        )

    def _create_fail_result(
        self, page_state: str, evidence: list[str], taxonomy_class: str, sub_reason: str
    ) -> PublishVerificationResult:
        """创建失败结果"""
        return PublishVerificationResult(
            result=VerificationResult.FAIL.value,
            page_state=page_state,
            evidence=evidence,
            taxonomy_class=taxonomy_class,
            sub_reason=sub_reason,
        )

    def _create_safe_stop_result(
        self, page_state: str, evidence: list[str], taxonomy_class: str, sub_reason: str
    ) -> PublishVerificationResult:
        """创建安全停止结果"""
        return PublishVerificationResult(
            result=VerificationResult.SAFE_STOP.value,
            page_state=page_state,
            evidence=evidence,
            taxonomy_class=taxonomy_class,
            sub_reason=sub_reason,
        )


# 便捷函数
def verify_publish_result(
    page_state: str, vision_text: str, ui_anchors: list[str]
) -> PublishVerificationResult:
    """
    核验发布结果的便捷函数

    Args:
        page_state: 页面状态字符串
        vision_text: 视觉分析文本
        ui_anchors: UI锚点列表

    Returns:
        PublishVerificationResult: 核验结果
    """
    verifier = PublishResultVerifier()
    return verifier.verify(page_state, vision_text, ui_anchors)
