#!/usr/bin/env python3
"""
OpenHuman Router - OpenHuman 领域路由

负责从用户输入中识别 OpenHuman 领域阶段，修复歧义匹配问题。
从"第一个子字符串命中"升级为"有优先级的规则系统"。
"""

import re
from typing import Dict, List, Optional, Set, Tuple

# OpenHuman 阶段定义
OPENHUMAN_STAGES = {
    "distill": "提炼",
    "skill_design": "技能设计",
    "dispatch": "任务分发",
    "acceptance": "验收结算",
    "settlement": "结算分账",
    "audit": "审计追溯",
}

# 阶段优先级（数字越小优先级越高）
# 当多个阶段关键词同时命中时，优先级高的胜出
STAGE_PRIORITY = {
    "skill_design": 1,  # 技能设计优先级最高（常与"提炼"同时出现）
    "audit": 2,  # 审计次之（常与"dispatch"同时出现）
    "dispatch": 3,
    "acceptance": 4,
    "settlement": 5,
    "distill": 6,  # 提炼作为兜底
}

# 阶段关键词配置
# 每个阶段包含强关键词（必须）和弱关键词（加分）
STAGE_KEYWORDS = {
    "distill": {
        "strong": ["提炼", "总结", "归纳", "distill", "summarize", "extract"],
        "weak": ["经验", "知识", "lesson", "experience", "knowledge"],
    },
    "skill_design": {
        "strong": [
            "技能设计",
            "skill design",
            "设计技能",
            "create skill",
            "skill creation",
        ],
        "weak": ["skill", "技能", "模板", "template", "design", "设计"],
    },
    "dispatch": {
        "strong": ["发布任务", "任务分发", "dispatch", "assign task", "发布", "分发"],
        "weak": ["任务", "task", "分配", "assign", "招募", "recruit"],
    },
    "acceptance": {
        "strong": ["验收", "验收结算", "acceptance", "验收通过", "验收完成"],
        "weak": ["通过", "完成", "accept", "approve", "结算"],
    },
    "settlement": {
        "strong": ["结算", "结算分账", "settlement", "分账", "支付结算"],
        "weak": ["支付", "payment", "money", "金额", "账单", "bill"],
    },
    "audit": {
        "strong": ["审计", "审计追溯", "audit", "审计报告", "audit report"],
        "weak": ["检查", "追溯", "review", "check", "记录", "record"],
    },
}

# 组合意图规则
# 当特定关键词组合出现时，强制指定阶段
COMBINATION_RULES = [
    {
        "keywords": ["skill", "技能", "设计", "design"],  # 包含"skill"和"设计"
        "required": ["提炼"],  # 同时包含"提炼"
        "stage": "skill_design",  # 强制为 skill_design
        "reason": "同时出现'skill/技能'和'提炼'，优先识别为技能设计",
    },
    {
        "keywords": ["audit", "审计", "report", "报告"],  # 包含"audit"或"审计"
        "required": ["dispatch", "分发", "任务"],  # 同时包含"dispatch"或"任务"
        "stage": "audit",  # 强制为 audit
        "reason": "同时出现'审计'和'dispatch/任务'，优先识别为审计",
    },
]


class OpenHumanRouter:
    """OpenHuman 路由器"""

    def __init__(self):
        self.stage_priority = STAGE_PRIORITY
        self.stage_keywords = STAGE_KEYWORDS
        self.combination_rules = COMBINATION_RULES

    def detect_stage(self, text: str) -> Tuple[str, str, Dict]:
        """
        检测 OpenHuman 阶段

        Args:
            text: 用户输入的文本

        Returns:
            (stage_id, stage_label, detection_details)
        """
        text_lower = text.lower()
        text_original = text

        # 1. 检查组合意图规则
        combined_stage = self._check_combination_rules(text_lower, text_original)
        if combined_stage:
            return combined_stage

        # 2. 计算每个阶段的得分
        stage_scores = {}
        stage_details = {}

        for stage_id, config in self.stage_keywords.items():
            score, details = self._calculate_stage_score(stage_id, text_lower, text_original)
            stage_scores[stage_id] = score
            stage_details[stage_id] = details

        # 3. 选择得分最高的阶段
        max_score = max(stage_scores.values())
        candidates = [stage_id for stage_id, score in stage_scores.items() if score == max_score]

        # 4. 如果平局，使用优先级决定
        if len(candidates) > 1:
            candidates.sort(key=lambda x: self.stage_priority.get(x, 999))

        selected_stage = candidates[0]

        # 5. 如果最高分为0，返回未知
        if max_score == 0:
            return "unknown", "未知", {"reason": "未检测到 OpenHuman 阶段关键词"}

        # 6. 返回结果
        # selected_stage 保证是 OPENHUMAN_STAGES 的键
        label = OPENHUMAN_STAGES.get(selected_stage, selected_stage)
        # 类型断言：label 不会是 None
        label = str(label)
        details = stage_details[selected_stage]
        details["candidates"] = {
            stage: stage_scores[stage] for stage in stage_scores if stage_scores[stage] > 0
        }

        return selected_stage, label, details

    def _check_combination_rules(
        self, text_lower: str, text_original: str
    ) -> Optional[Tuple[str, str, Dict]]:
        """检查组合意图规则"""
        for rule in self.combination_rules:
            # 检查 keywords 中是否至少有一个出现
            keywords_match = any(
                keyword.lower() in text_lower or keyword in text_original
                for keyword in rule["keywords"]
            )

            # 检查 required 中是否至少一个出现
            if isinstance(rule["required"], list):
                # 列表：至少一个required关键词出现
                required_match = any(
                    req.lower() in text_lower or req in text_original for req in rule["required"]
                )
            else:
                # 单个字符串：该字符串必须出现
                required_match = (
                    rule["required"].lower() in text_lower or rule["required"] in text_original
                )

            if keywords_match and required_match:
                stage_id = rule["stage"]
                label = OPENHUMAN_STAGES[stage_id]  # stage_id 保证在字典中
                return (
                    stage_id,
                    label,
                    {
                        "reason": rule["reason"],
                        "rule_matched": True,
                        "keywords_found": [
                            k
                            for k in rule["keywords"]
                            if k.lower() in text_lower or k in text_original
                        ],
                        "required_found": [
                            r
                            for r in rule["required"]
                            if r.lower() in text_lower or r in text_original
                        ],
                    },
                )

        return None

    def _calculate_stage_score(
        self, stage_id: str, text_lower: str, text_original: str
    ) -> Tuple[float, Dict]:
        """计算阶段得分"""
        config = self.stage_keywords[stage_id]
        score = 0.0
        details = {
            "strong_matches": [],
            "weak_matches": [],
            "strong_count": 0,
            "weak_count": 0,
        }

        # 强关键词匹配（每个+2分）
        for keyword in config["strong"]:
            if keyword.lower() in text_lower or keyword in text_original:
                score += 2.0
                details["strong_matches"].append(keyword)
                details["strong_count"] += 1

        # 弱关键词匹配（每个+1分）
        for keyword in config["weak"]:
            if keyword.lower() in text_lower or keyword in text_original:
                score += 1.0
                details["weak_matches"].append(keyword)
                details["weak_count"] += 1

        # 如果强关键词匹配数>0，额外加分
        if details["strong_count"] > 0:
            score += 1.0

        # 如果同时有强关键词和弱关键词，额外加分
        if details["strong_count"] > 0 and details["weak_count"] > 0:
            score += 0.5

        details["total_score"] = score
        return score, details

    def get_stage_info(self, stage_id: str) -> Dict:
        """获取阶段信息"""
        return {
            "id": stage_id,
            "label": OPENHUMAN_STAGES.get(stage_id, stage_id),
            "keywords": self.stage_keywords.get(stage_id, {}),
            "priority": self.stage_priority.get(stage_id, 999),
        }


# 全局路由器实例
_router_instance: Optional[OpenHumanRouter] = None


def get_router() -> OpenHumanRouter:
    """获取全局路由器实例"""
    global _router_instance
    if _router_instance is None:
        _router_instance = OpenHumanRouter()
    return _router_instance


def detect_openhuman_stage(text: str) -> Tuple[str, str, Dict]:
    """
    检测 OpenHuman 阶段（便捷函数）

    Returns:
        (stage_id, stage_label, detection_details)
    """
    router = get_router()
    return router.detect_stage(text)


if __name__ == "__main__":
    # 测试代码
    print("=== OpenHuman Router 测试 ===")

    router = OpenHumanRouter()

    # 测试用例（来自任务说明）
    test_cases = [
        "把这个经验提炼成 Skill",
        "audit the dispatch records",
        "生成审计报告",
        "为 offline_survey 发布任务并筛人",
        "设计一个新技能模板",
        "结算上个月的任务费用",
        "验收已完成的任务",
        "分发新的调研任务",
        "这是一个普通请求，不包含 OpenHuman 关键词",
    ]

    print("\n1. 路由测试:")
    for text in test_cases:
        stage_id, label, details = router.detect_stage(text)
        print(f"\n  输入: {text}")
        print(f"  结果: {stage_id} ({label})")
        if details.get("candidates"):
            print(f"  候选: {details['candidates']}")
        if details.get("reason"):
            print(f"  原因: {details['reason']}")
        if details.get("strong_matches"):
            print(f"  强关键词: {details['strong_matches']}")
        if details.get("weak_matches"):
            print(f"  弱关键词: {details['weak_matches']}")

    # 测试阶段信息
    print("\n2. 阶段信息:")
    for stage_id in OPENHUMAN_STAGES:
        info = router.get_stage_info(stage_id)
        print(f"  {stage_id}: {info['label']}, 优先级: {info['priority']}")

    # 验证已知误判样例
    print("\n3. 验证已知误判样例:")
    validation_cases = [
        ("把这个经验提炼成 Skill", "skill_design", "应偏向 skill_design 而非 distill"),
        ("audit the dispatch records", "audit", "应偏向 audit 而非 dispatch"),
        ("生成审计报告", "audit", "应识别为 audit"),
        ("为 offline_survey 发布任务并筛人", "dispatch", "应识别为 dispatch"),
    ]

    all_passed = True
    for text, expected_stage, description in validation_cases:
        stage_id, label, _ = router.detect_stage(text)
        passed = stage_id == expected_stage
        all_passed = all_passed and passed
        status = "✓" if passed else "✗"
        print(f"  {status} {description}")
        print(f"    输入: {text}")
        print(f"    预期: {expected_stage}, 实际: {stage_id}")

    if all_passed:
        print("\n✅ 所有验证用例通过")
    else:
        print("\n❌ 部分验证用例失败")
