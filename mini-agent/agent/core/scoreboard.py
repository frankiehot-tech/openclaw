#!/usr/bin/env python3
"""
Scoreboard - 最小评分板

提供技术、用户、业务三类得分，基于现有数据近似计算。
"""

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

RUNTIME_ROOT = Path(os.getenv("ATHENA_RUNTIME_ROOT", "/Volumes/1TB-M2/openclaw"))
SCOREBOARD_DIR = RUNTIME_ROOT / ".openclaw" / "scoreboard"
SCOREBOARD_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ScoreEntry:
    """得分条目"""

    timestamp: str
    technical_score: float  # 技术得分 (0-100)
    user_score: float  # 用户得分 (0-100)
    business_score: float  # 业务得分 (0-100)
    overall_score: float  # 综合得分 (0-100)
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScoreEntry":
        return cls(**data)


# 得分权重配置
SCORE_WEIGHTS = {
    "technical": 0.4,
    "user": 0.3,
    "business": 0.3,
}


def calculate_technical_score() -> Tuple[float, Dict[str, Any]]:
    """计算技术得分"""
    # 基于系统稳定性、代码质量、自动化程度等
    # 这里使用简化计算，实际应集成现有指标

    score = 70.0  # 基线
    factors = []

    # 1. 检查工作流状态
    try:
        from scripts.workflow_state import get_state, list_state_keys

        incident_states = get_state("incident_states", {})
        if incident_states:
            # 计算已解决事件比例
            total = len(incident_states)
            resolved = sum(
                1 for v in incident_states.values() if v.get("state") in ["completed", "failed"]
            )
            resolution_rate = resolved / total if total > 0 else 1.0
            score += resolution_rate * 10
            factors.append(f"事件解决率: {resolution_rate:.1%}")
    except ImportError:
        pass

    # 2. 检查任务完成率
    try:
        tasks_path = RUNTIME_ROOT / ".openclaw" / "orchestrator" / "tasks.json"
        if tasks_path.exists():
            with open(tasks_path, "r", encoding="utf-8") as f:
                tasks_data = json.load(f)
            tasks = tasks_data.get("tasks", [])
            if tasks:
                completed = sum(1 for t in tasks if t.get("status") == "completed")
                completion_rate = completed / len(tasks)
                score += completion_rate * 10
                factors.append(f"任务完成率: {completion_rate:.1%}")
    except Exception:
        pass

    # 3. 检查自动化程度（改进回路）
    try:
        from .improvement_loop import get_improvement_stats

        stats = get_improvement_stats()
        total = stats.get("total", 0)
        completed = stats.get("by_status", {}).get("completed", 0)
        if total > 0:
            automation_rate = completed / total
            score += automation_rate * 10
            factors.append(f"改进自动化率: {automation_rate:.1%}")
    except ImportError:
        pass

    # 限制在0-100之间
    score = max(0, min(100, score))

    metadata = {
        "factors": factors,
        "calculation_time": datetime.now().isoformat(),
        "baseline": 70.0,
    }

    return score, metadata


def calculate_user_score() -> Tuple[float, Dict[str, Any]]:
    """计算用户得分"""
    # 基于反馈处理速度、用户满意度等

    score = 65.0  # 基线
    factors = []

    # 1. 反馈处理速度
    try:
        from .feedback_intake import FEEDBACK_STATE_VERIFIED, get_feedback_stats

        stats = get_feedback_stats()
        total = stats.get("total", 0)
        verified = stats.get(FEEDBACK_STATE_VERIFIED, 0)

        if total > 0:
            feedback_resolution_rate = verified / total
            score += feedback_resolution_rate * 20
            factors.append(f"反馈解决率: {feedback_resolution_rate:.1%}")

        # 计算平均处理时间（简化）
        if verified > 0:
            score += min(10, verified * 2)  # 每解决一个反馈+2分，最多+10分
            factors.append(f"已验证反馈数: {verified}")
    except ImportError:
        pass

    # 2. 反馈状态分布
    try:
        from .feedback_intake import (
            FEEDBACK_STATE_ACCEPTED,
            FEEDBACK_STATE_FIXED,
            FEEDBACK_STATE_NEW,
            FEEDBACK_STATE_TRIAGED,
        )

        stats = get_feedback_stats()
        new = stats.get(FEEDBACK_STATE_NEW, 0)
        triaged = stats.get(FEEDBACK_STATE_TRIAGED, 0)
        accepted = stats.get(FEEDBACK_STATE_ACCEPTED, 0)
        fixed = stats.get(FEEDBACK_STATE_FIXED, 0)

        # 积压惩罚
        backlog = new + triaged + accepted
        if backlog > 5:
            score -= min(15, backlog * 2)  # 每个积压项-2分，最多-15分
            factors.append(f"积压反馈: {backlog}")
    except ImportError:
        pass

    # 限制在0-100之间
    score = max(0, min(100, score))

    metadata = {
        "factors": factors,
        "calculation_time": datetime.now().isoformat(),
        "baseline": 65.0,
    }

    return score, metadata


def calculate_business_score() -> Tuple[float, Dict[str, Any]]:
    """计算业务得分"""
    # 基于代谢盈余、改进效率、成本效益等

    score = 60.0  # 基线
    factors = []

    # 1. 代谢盈余（基于周报数据）
    try:
        from scripts.weekly_trend_report import calculate_surplus

        surplus_data = calculate_surplus()
        surplus_ratio = surplus_data.get("surplus_ratio", 0)
        surplus_positive = surplus_data.get("surplus_positive", False)

        if surplus_positive:
            score += min(20, surplus_ratio * 5)  # 每个盈余单位+5分，最多+20分
            factors.append(f"代谢盈余比例: {surplus_ratio:.2f}")
        else:
            score -= 15
            factors.append("代谢盈余为负")
    except ImportError:
        # 使用模拟数据
        score += 10
        factors.append("代谢盈余: 模拟+10分")

    # 2. 改进效率
    try:
        from .improvement_loop import get_improvement_stats

        stats = get_improvement_stats()
        total = stats.get("total", 0)
        completed = stats.get("by_status", {}).get("completed", 0)

        if total > 0:
            efficiency = completed / total
            score += efficiency * 15
            factors.append(f"改进完成率: {efficiency:.1%}")

        # 近期完成数
        recent = len(stats.get("recent_completed", []))
        score += min(10, recent * 2)  # 每个近期完成+2分，最多+10分
        factors.append(f"近期完成改进: {recent}")
    except ImportError:
        pass

    # 3. 成本效益（简化）
    try:
        cost_state_path = RUNTIME_ROOT / ".cost_state"
        if cost_state_path.exists():
            with open(cost_state_path, "r", encoding="utf-8") as f:
                cost_data = json.load(f)
            total_spent = cost_data.get("total_spent", 0)
            # 成本越低得分越高（简化）
            if total_spent < 50:
                score += 10
                factors.append(f"累计成本低: ¥{total_spent}")
            elif total_spent > 100:
                score -= 10
                factors.append(f"累计成本高: ¥{total_spent}")
    except Exception:
        pass

    # 限制在0-100之间
    score = max(0, min(100, score))

    metadata = {
        "factors": factors,
        "calculation_time": datetime.now().isoformat(),
        "baseline": 60.0,
    }

    return score, metadata


def calculate_overall_score(technical: float, user: float, business: float) -> float:
    """计算综合得分"""
    overall = (
        technical * SCORE_WEIGHTS["technical"]
        + user * SCORE_WEIGHTS["user"]
        + business * SCORE_WEIGHTS["business"]
    )
    return round(overall, 1)


def generate_scoreboard() -> ScoreEntry:
    """生成评分板"""
    logger.info("生成评分板...")

    technical_score, technical_meta = calculate_technical_score()
    user_score, user_meta = calculate_user_score()
    business_score, business_meta = calculate_business_score()

    overall_score = calculate_overall_score(technical_score, user_score, business_score)

    entry = ScoreEntry(
        timestamp=datetime.now().isoformat(),
        technical_score=round(technical_score, 1),
        user_score=round(user_score, 1),
        business_score=round(business_score, 1),
        overall_score=overall_score,
        metadata={
            "technical": technical_meta,
            "user": user_meta,
            "business": business_meta,
            "weights": SCORE_WEIGHTS,
        },
    )

    # 保存评分条目
    save_score_entry(entry)

    logger.info(
        f"评分板生成完成: T={entry.technical_score}, U={entry.user_score}, B={entry.business_score}, O={entry.overall_score}"
    )
    return entry


def save_score_entry(entry: ScoreEntry) -> bool:
    """保存评分条目"""
    try:
        # 按日期保存
        date_str = datetime.now().strftime("%Y%m%d")
        score_file = SCOREBOARD_DIR / f"scores_{date_str}.json"

        # 加载现有数据或创建新列表
        scores = []
        if score_file.exists():
            with open(score_file, "r", encoding="utf-8") as f:
                scores = json.load(f)

        scores.append(entry.to_dict())

        # 只保留最近100个条目
        if len(scores) > 100:
            scores = scores[-100:]

        with open(score_file, "w", encoding="utf-8") as f:
            json.dump(scores, f, ensure_ascii=False, indent=2)

        # 同时保存最新评分供快速访问
        latest_file = SCOREBOARD_DIR / "latest_score.json"
        with open(latest_file, "w", encoding="utf-8") as f:
            json.dump(entry.to_dict(), f, ensure_ascii=False, indent=2)

        return True
    except Exception as e:
        logger.error(f"保存评分条目失败: {e}")
        return False


def load_latest_score() -> Optional[ScoreEntry]:
    """加载最新评分"""
    try:
        latest_file = SCOREBOARD_DIR / "latest_score.json"
        if not latest_file.exists():
            return None

        with open(latest_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return ScoreEntry.from_dict(data)
    except Exception as e:
        logger.error(f"加载最新评分失败: {e}")
        return None


def load_score_history(days: int = 7) -> List[ScoreEntry]:
    """加载评分历史"""
    entries = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime("%Y%m%d")
        score_file = SCOREBOARD_DIR / f"scores_{date_str}.json"

        if score_file.exists():
            try:
                with open(score_file, "r", encoding="utf-8") as f:
                    daily_scores = json.load(f)
                for score_data in daily_scores:
                    entries.append(ScoreEntry.from_dict(score_data))
            except Exception as e:
                logger.warning(f"加载评分文件失败 {score_file}: {e}")

        current_date += timedelta(days=1)

    # 按时间戳排序
    entries.sort(key=lambda x: x.timestamp)
    return entries


def get_score_trend() -> Dict[str, Any]:
    """获取评分趋势"""
    history = load_score_history(days=14)
    if not history:
        return {"trend": "insufficient_data", "message": "数据不足"}

    latest = history[-1]
    if len(history) >= 2:
        previous = history[-2]

        tech_trend = latest.technical_score - previous.technical_score
        user_trend = latest.user_score - previous.user_score
        business_trend = latest.business_score - previous.business_score
        overall_trend = latest.overall_score - previous.overall_score

        trend_direction = {
            "technical": "up" if tech_trend > 0 else "down" if tech_trend < 0 else "stable",
            "user": "up" if user_trend > 0 else "down" if user_trend < 0 else "stable",
            "business": "up" if business_trend > 0 else "down" if business_trend < 0 else "stable",
            "overall": "up" if overall_trend > 0 else "down" if overall_trend < 0 else "stable",
        }

        return {
            "trend": "calculated",
            "latest": latest.to_dict(),
            "previous": previous.to_dict(),
            "deltas": {
                "technical": round(tech_trend, 1),
                "user": round(user_trend, 1),
                "business": round(business_trend, 1),
                "overall": round(overall_trend, 1),
            },
            "directions": trend_direction,
            "period_days": 14,
        }
    else:
        return {
            "trend": "single_data_point",
            "latest": latest.to_dict(),
            "message": "只有一个数据点，无法计算趋势",
        }


def generate_scoreboard_report() -> str:
    """生成评分板报告"""
    latest = load_latest_score()
    trend = get_score_trend()

    if not latest:
        latest_score = generate_scoreboard()
    else:
        latest_score = latest

    report = f"""# OpenHuman MVP 评分板报告

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**数据周期**: 最近14天

## 当前得分

| 维度 | 得分 (0-100) | 状态 |
|------|--------------|------|
| **技术得分** | {latest_score.technical_score:.1f} | {"🟢 良好" if latest_score.technical_score >= 70 else "🟡 中等" if latest_score.technical_score >= 50 else "🔴 需改进"} |
| **用户得分** | {latest_score.user_score:.1f} | {"🟢 良好" if latest_score.user_score >= 70 else "🟡 中等" if latest_score.user_score >= 50 else "🔴 需改进"} |
| **业务得分** | {latest_score.business_score:.1f} | {"🟢 良好" if latest_score.business_score >= 70 else "🟡 中等" if latest_score.business_score >= 50 else "🔴 需改进"} |
| **综合得分** | **{latest_score.overall_score:.1f}** | {"🟢 良好" if latest_score.overall_score >= 70 else "🟡 中等" if latest_score.overall_score >= 50 else "🔴 需改进"} |

## 趋势分析
"""

    if trend.get("trend") == "calculated":
        deltas = trend["deltas"]
        directions = trend["directions"]

        report += f"""
| 维度 | 变化 | 趋势 |
|------|------|------|
| 技术得分 | {f"+{deltas["technical"]:.1f}" if deltas["technical"] > 0 else f"{deltas["technical"]:.1f}"} | {"📈 上升" if directions["technical"] == "up" else "📉 下降" if directions["technical"] == "down" else "➡️ 平稳"} |
| 用户得分 | {f"+{deltas["user"]:.1f}" if deltas["user"] > 0 else f"{deltas["user"]:.1f}"} | {"📈 上升" if directions["user"] == "up" else "📉 下降" if directions["user"] == "down" else "➡️ 平稳"} |
| 业务得分 | {f"+{deltas["business"]:.1f}" if deltas["business"] > 0 else f"{deltas["business"]:.1f}"} | {"📈 上升" if directions["business"] == "up" else "📉 下降" if directions["business"] == "down" else "➡️ 平稳"} |
| 综合得分 | {f"+{deltas["overall"]:.1f}" if deltas["overall"] > 0 else f"{deltas["overall"]:.1f}"} | {"📈 上升" if directions["overall"] == "up" else "📉 下降" if directions["overall"] == "down" else "➡️ 平稳"} |
"""
    else:
        report += f"\n{trend.get('message', '趋势数据不足')}\n"

    # 添加影响因素
    report += f"""
## 影响因素

### 技术得分
"""
    for factor in latest_score.metadata.get("technical", {}).get("factors", []):
        report += f"- {factor}\n"

    report += f"""
### 用户得分
"""
    for factor in latest_score.metadata.get("user", {}).get("factors", []):
        report += f"- {factor}\n"

    report += f"""
### 业务得分
"""
    for factor in latest_score.metadata.get("business", {}).get("factors", []):
        report += f"- {factor}\n"

    report += f"""
## 权重配置
- 技术得分: {SCORE_WEIGHTS["technical"] * 100:.0f}%
- 用户得分: {SCORE_WEIGHTS["user"] * 100:.0f}%
- 业务得分: {SCORE_WEIGHTS["business"] * 100:.0f}%

---
*生成自 OpenHuman MVP 反馈闭环与持续改进评分板*
"""

    return report


if __name__ == "__main__":
    # 模块自测
    print("=== Scoreboard 自测 ===")

    # 生成评分板
    score = generate_scoreboard()
    print(f"技术得分: {score.technical_score:.1f}")
    print(f"用户得分: {score.user_score:.1f}")
    print(f"业务得分: {score.business_score:.1f}")
    print(f"综合得分: {score.overall_score:.1f}")

    # 测试趋势
    trend = get_score_trend()
    print(f"趋势分析: {trend.get('trend', 'unknown')}")

    # 生成报告
    report = generate_scoreboard_report()
    print("\n=== 报告预览（前500字符）===")
    print(report[:500])

    # 保存报告
    report_dir = RUNTIME_ROOT / "workspace"
    report_dir.mkdir(exist_ok=True)
    report_file = report_dir / "scoreboard_report.md"
    report_file.write_text(report)
    print(f"\n报告已保存: {report_file}")

    print("=== 自测完成 ===")
