#!/usr/bin/env python3
"""
Next Step Prompt - 最小下一步提示

基于评分或反馈变化，给出具体的下一步动作建议。
不允许只有静态报表，必须有行动提示。
"""

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

RUNTIME_ROOT = Path(os.getenv("ATHENA_RUNTIME_ROOT", "/Volumes/1TB-M2/openclaw"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ActionRecommendation:
    """动作建议"""

    priority: str  # high/medium/low
    category: str  # feedback/technical/user/business/improvement
    title: str
    description: str
    action: str  # 具体动作
    expected_impact: str
    estimated_effort: str  # low/medium/high
    related_items: List[str]  # 关联的反馈ID、改进ID等


def analyze_feedback_backlog() -> List[ActionRecommendation]:
    """分析反馈积压"""
    recommendations = []

    try:
        from .feedback_intake import (
            FEEDBACK_STATE_ACCEPTED,
            FEEDBACK_STATE_NEW,
            FEEDBACK_STATE_TRIAGED,
            get_feedback_stats,
            list_feedback,
        )

        stats = get_feedback_stats()
        new_count = stats.get(FEEDBACK_STATE_NEW, 0)
        triaged_count = stats.get(FEEDBACK_STATE_TRIAGED, 0)
        accepted_count = stats.get(FEEDBACK_STATE_ACCEPTED, 0)

        total_backlog = new_count + triaged_count + accepted_count

        if total_backlog > 10:
            recommendations.append(
                ActionRecommendation(
                    priority="high",
                    category="feedback",
                    title="高优先级反馈积压",
                    description=f"当前有 {total_backlog} 个反馈待处理（新: {new_count}, 已分诊: {triaged_count}, 已接受: {accepted_count}）",
                    action="运行反馈分诊流程，优先处理高优先级反馈",
                    expected_impact="减少反馈积压，提高用户满意度",
                    estimated_effort="medium",
                    related_items=[],
                )
            )
        elif total_backlog > 5:
            recommendations.append(
                ActionRecommendation(
                    priority="medium",
                    category="feedback",
                    title="中等反馈积压",
                    description=f"当前有 {total_backlog} 个反馈待处理",
                    action="安排时间处理积压反馈",
                    expected_impact="维持反馈处理速度",
                    estimated_effort="low",
                    related_items=[],
                )
            )

        # 检查长时间未处理的反馈
        feedbacks = list_feedback(state_filter=FEEDBACK_STATE_NEW, limit=20)
        old_feedbacks = []
        for fb in feedbacks:
            try:
                created = datetime.fromisoformat(fb.created_at.replace("Z", "+00:00"))
                age_days = (datetime.now() - created).days
                if age_days > 7:
                    old_feedbacks.append(fb.feedback_id)
            except Exception:
                pass

        if old_feedbacks:
            recommendations.append(
                ActionRecommendation(
                    priority="high",
                    category="feedback",
                    title="陈旧反馈待处理",
                    description=f"有 {len(old_feedbacks)} 个反馈超过7天未处理",
                    action="立即审查并处理陈旧反馈",
                    expected_impact="防止反馈过期，维护反馈系统可信度",
                    estimated_effort="medium",
                    related_items=old_feedbacks[:5],  # 只列出前5个
                )
            )

    except ImportError as e:
        logger.warning(f"无法导入feedback模块: {e}")

    return recommendations


def analyze_improvement_progress() -> List[ActionRecommendation]:
    """分析改进进度"""
    recommendations = []

    try:
        from .improvement_loop import (
            IMPROVEMENT_PHASE_IDENTIFICATION,
            IMPROVEMENT_PHASE_IMPLEMENTATION,
            IMPROVEMENT_PHASE_PRIORITIZATION,
            IMPROVEMENT_STATUS_ACTIVE,
            get_improvement_stats,
            list_improvements,
        )

        stats = get_improvement_stats()
        identification_count = stats["by_phase"].get(IMPROVEMENT_PHASE_IDENTIFICATION, 0)
        prioritization_count = stats["by_phase"].get(IMPROVEMENT_PHASE_PRIORITIZATION, 0)
        implementation_count = stats["by_phase"].get(IMPROVEMENT_PHASE_IMPLEMENTATION, 0)

        # 检查识别阶段积压
        if identification_count > 5:
            recommendations.append(
                ActionRecommendation(
                    priority="medium",
                    category="improvement",
                    title="改进识别积压",
                    description=f"有 {identification_count} 个改进处于识别阶段",
                    action="运行改进回路优先级评估",
                    expected_impact="加速改进流程",
                    estimated_effort="low",
                    related_items=[],
                )
            )

        # 检查实施阶段停滞
        if implementation_count > 3:
            active_improvements = list_improvements(
                phase_filter=IMPROVEMENT_PHASE_IMPLEMENTATION,
                status_filter=IMPROVEMENT_STATUS_ACTIVE,
                limit=10,
            )
            stalled = []
            for imp in active_improvements:
                try:
                    updated = datetime.fromisoformat(imp.updated_at.replace("Z", "+00:00"))
                    if (datetime.now() - updated).days > 3:
                        stalled.append(imp.improvement_id)
                except Exception:
                    pass

            if stalled:
                recommendations.append(
                    ActionRecommendation(
                        priority="high",
                        category="improvement",
                        title="改进实施停滞",
                        description=f"有 {len(stalled)} 个改进实施超过3天无进展",
                        action="检查关联任务状态，重新分配资源",
                        expected_impact="恢复改进实施进度",
                        estimated_effort="medium",
                        related_items=stalled[:3],
                    )
                )

    except ImportError as e:
        logger.warning(f"无法导入improvement模块: {e}")

    return recommendations


def analyze_score_trends() -> List[ActionRecommendation]:
    """分析评分趋势"""
    recommendations = []

    try:
        from .scoreboard import get_score_trend, load_latest_score

        latest = load_latest_score()
        if not latest:
            # 生成新评分
            from .scoreboard import generate_scoreboard

            latest = generate_scoreboard()

        trend = get_score_trend()

        if trend.get("trend") == "calculated":
            deltas = trend["deltas"]
            directions = trend["directions"]

            # 技术得分下降
            if directions["technical"] == "down" and deltas["technical"] < -2:
                recommendations.append(
                    ActionRecommendation(
                        priority="medium",
                        category="technical",
                        title="技术得分下降",
                        description=f"技术得分下降 {abs(deltas['technical']):.1f} 分，当前 {latest.technical_score:.1f}",
                        action="检查系统稳定性和任务完成率",
                        expected_impact="阻止技术得分继续下降",
                        estimated_effort="medium",
                        related_items=[],
                    )
                )

            # 用户得分下降
            if directions["user"] == "down" and deltas["user"] < -2:
                recommendations.append(
                    ActionRecommendation(
                        priority="high",
                        category="user",
                        title="用户得分下降",
                        description=f"用户得分下降 {abs(deltas['user']):.1f} 分，当前 {latest.user_score:.1f}",
                        action="优先处理用户反馈，提高反馈解决速度",
                        expected_impact="提升用户满意度",
                        estimated_effort="high",
                        related_items=[],
                    )
                )

            # 业务得分下降
            if directions["business"] == "down" and deltas["business"] < -2:
                recommendations.append(
                    ActionRecommendation(
                        priority="medium",
                        category="business",
                        title="业务得分下降",
                        description=f"业务得分下降 {abs(deltas['business']):.1f} 分，当前 {latest.business_score:.1f}",
                        action="分析代谢盈余和改进效率",
                        expected_impact="改善业务指标",
                        estimated_effort="medium",
                        related_items=[],
                    )
                )

            # 综合得分低
            if latest.overall_score < 60:
                recommendations.append(
                    ActionRecommendation(
                        priority="high",
                        category="technical",
                        title="综合得分低于及格线",
                        description=f"综合得分仅 {latest.overall_score:.1f}，需全面提升",
                        action="全面审查技术、用户、业务三个维度",
                        expected_impact="提升整体表现",
                        estimated_effort="high",
                        related_items=[],
                    )
                )

            # 识别最弱维度
            scores = {
                "technical": latest.technical_score,
                "user": latest.user_score,
                "business": latest.business_score,
            }
            weakest_dimension = min(scores, key=scores.get)
            weakest_score = scores[weakest_dimension]

            if weakest_score < 65:
                dim_name = {"technical": "技术", "user": "用户", "business": "业务"}[
                    weakest_dimension
                ]
                recommendations.append(
                    ActionRecommendation(
                        priority="medium",
                        category=weakest_dimension,
                        title=f"{dim_name}维度需改进",
                        description=f"{dim_name}得分仅 {weakest_score:.1f}，是当前最弱维度",
                        action=f"制定{dim_name}维度改进计划",
                        expected_impact=f"提升{dim_name}得分",
                        estimated_effort="medium",
                        related_items=[],
                    )
                )

    except ImportError as e:
        logger.warning(f"无法导入scoreboard模块: {e}")

    return recommendations


def analyze_system_health() -> List[ActionRecommendation]:
    """分析系统健康度"""
    recommendations = []

    # 检查工作流状态
    try:
        from scripts.workflow_state import get_state, list_state_keys

        # 检查心跳
        heartbeats = get_state("heartbeats", {})
        stale_components = []
        for component, timestamp in heartbeats.items():
            try:
                last_heartbeat = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                if (datetime.now() - last_heartbeat).total_seconds() > 3600:  # 1小时
                    stale_components.append(component)
            except Exception:
                pass

        if stale_components:
            recommendations.append(
                ActionRecommendation(
                    priority="high",
                    category="technical",
                    title="组件心跳过期",
                    description=f"{len(stale_components)} 个组件超过1小时无心跳: {', '.join(stale_components[:3])}",
                    action="检查相关组件运行状态",
                    expected_impact="恢复系统监控",
                    estimated_effort="low",
                    related_items=stale_components,
                )
            )

    except ImportError:
        pass

    # 检查存储空间
    try:
        import shutil

        total, used, free = shutil.disk_usage(RUNTIME_ROOT)
        free_gb = free / (1024**3)

        if free_gb < 5:
            recommendations.append(
                ActionRecommendation(
                    priority="high",
                    category="technical",
                    title="存储空间不足",
                    description=f"剩余存储空间仅 {free_gb:.1f} GB",
                    action="清理临时文件或扩展存储",
                    expected_impact="防止系统因存储满而崩溃",
                    estimated_effort="medium",
                    related_items=[],
                )
            )
    except Exception:
        pass

    return recommendations


def generate_next_step_prompt() -> Tuple[str, List[ActionRecommendation]]:
    """生成下一步提示"""
    logger.info("生成下一步提示...")

    all_recommendations = []

    # 收集各维度建议
    all_recommendations.extend(analyze_feedback_backlog())
    all_recommendations.extend(analyze_improvement_progress())
    all_recommendations.extend(analyze_score_trends())
    all_recommendations.extend(analyze_system_health())

    # 去重（基于标题）
    unique_recommendations = []
    seen_titles = set()
    for rec in all_recommendations:
        if rec.title not in seen_titles:
            seen_titles.add(rec.title)
            unique_recommendations.append(rec)

    # 按优先级排序：high > medium > low
    priority_order = {"high": 0, "medium": 1, "low": 2}
    unique_recommendations.sort(key=lambda x: priority_order[x.priority])

    # 生成提示文本
    prompt = f"""# OpenHuman MVP 下一步动作建议

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**分析范围**: 反馈积压、改进进度、评分趋势、系统健康度

## 建议摘要

"""

    if not unique_recommendations:
        prompt += "✅ 当前状态良好，无需紧急动作。建议继续保持监测。\n"
    else:
        # 统计优先级
        high_count = sum(1 for r in unique_recommendations if r.priority == "high")
        medium_count = sum(1 for r in unique_recommendations if r.priority == "medium")
        low_count = sum(1 for r in unique_recommendations if r.priority == "low")

        prompt += f"共识别 {len(unique_recommendations)} 个建议动作：\n"
        prompt += f"- 🔴 高优先级: {high_count} 个\n"
        prompt += f"- 🟡 中优先级: {medium_count} 个\n"
        prompt += f"- 🟢 低优先级: {low_count} 个\n\n"

        # 按优先级分组
        for priority_level in ["high", "medium", "low"]:
            level_recs = [r for r in unique_recommendations if r.priority == priority_level]
            if not level_recs:
                continue

            emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}[priority_level]
            prompt += f"## {emoji} {priority_level.capitalize()} 优先级\n\n"

            for i, rec in enumerate(level_recs, 1):
                category_emoji = {
                    "feedback": "💬",
                    "technical": "⚙️",
                    "user": "👤",
                    "business": "💰",
                    "improvement": "🔄",
                }.get(rec.category, "📌")

                prompt += f"### {i}. {category_emoji} {rec.title}\n\n"
                prompt += f"**描述**: {rec.description}\n\n"
                prompt += f"**建议动作**: {rec.action}\n\n"
                prompt += f"**预期影响**: {rec.expected_impact}\n\n"
                prompt += f"**预估投入**: {rec.estimated_effort.capitalize()}\n\n"

                if rec.related_items:
                    prompt += f"**关联项**: {', '.join(rec.related_items[:3])}"
                    if len(rec.related_items) > 3:
                        prompt += f" 等 {len(rec.related_items)} 项"
                    prompt += "\n\n"

                prompt += "---\n\n"

    # 添加通用建议
    prompt += f"""
## 常规维护建议

1. **每日检查**: 运行反馈分诊和评分板更新
2. **每周回顾**: 审查改进回路完成情况和评分趋势
3. **每月优化**: 调整评分权重和改进策略

## 快速执行

如需立即执行建议动作，可运行以下命令：

```bash
# 运行反馈分诊
python3 -m mini-agent.agent.core.feedback_intake

# 生成最新评分板
python3 -m mini-agent.agent.core.scoreboard

# 运行改进回路
python3 -m mini-agent.agent.core.improvement_loop
```

---
*生成自 OpenHuman MVP 反馈闭环与持续改进系统*
"""

    logger.info(f"生成 {len(unique_recommendations)} 个下一步建议")
    return prompt, unique_recommendations


def save_next_step_prompt(prompt: str, recommendations: List[ActionRecommendation]) -> Path:
    """保存下一步提示"""
    try:
        workspace_dir = RUNTIME_ROOT / "workspace"
        workspace_dir.mkdir(exist_ok=True)

        # 保存提示
        prompt_file = workspace_dir / "next_step_prompt.md"
        prompt_file.write_text(prompt)

        # 保存结构化建议
        if recommendations:
            recs_data = [asdict(r) for r in recommendations]
            recs_file = workspace_dir / "next_step_recommendations.json"
            with open(recs_file, "w", encoding="utf-8") as f:
                json.dump(recs_data, f, ensure_ascii=False, indent=2)

        logger.info(f"下一步提示已保存: {prompt_file}")
        return prompt_file
    except Exception as e:
        logger.error(f"保存下一步提示失败: {e}")
        raise


def main() -> None:
    """主入口"""
    prompt, recommendations = generate_next_step_prompt()

    # 保存到文件
    prompt_file = save_next_step_prompt(prompt, recommendations)

    # 输出到控制台
    print(prompt)
    print(f"\n✅ 下一步提示已生成并保存到: {prompt_file}")

    # 如果有高优先级建议，突出显示
    high_priority = [r for r in recommendations if r.priority == "high"]
    if high_priority:
        print(f"\n⚠️  发现 {len(high_priority)} 个高优先级建议，请立即处理！")


if __name__ == "__main__":
    main()
