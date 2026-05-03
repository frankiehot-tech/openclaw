"""报告生成模块：生成结构化中文 Markdown 日报."""

import logging
import os
from datetime import UTC, datetime, timedelta

from . import config

logger = logging.getLogger(__name__)


def _truncate(text: str, max_len: int = 120) -> str:
    """截断文本并添加省略号."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _format_time(dt: datetime) -> str:
    """格式化为北京时间."""
    # RSS 时间是 UTC，转北京时间 +8
    bj = dt + timedelta(hours=8)
    now = datetime.now(UTC) + timedelta(hours=8)
    delta = now - bj

    if delta < timedelta(hours=1):
        return f"{int(delta.total_seconds() // 60)} 分钟前"
    if delta < timedelta(hours=24):
        return f"{int(delta.total_seconds() // 3600)} 小时前"
    return bj.strftime("%m-%d")


def _build_channel_section(
    channel_name: str,
    handle: str,
    videos: list,
    summaries: dict[str, str] = None,
    days_threshold: int = 7,
) -> str:
    """构建单个频道的报告段落."""
    lines = []
    now = datetime.now(UTC)

    if not videos:
        lines.append(f"  🟡 近 {days_threshold} 天无更新")
        return "\n".join(lines)

    for v in videos:
        _ = (now - v.published).days
        time_str = _format_time(v.published)
        title = v.title.strip()
        desc = _truncate(v.description.replace("\n", " ").strip(), 100) if v.description else ""

        lines.append(f"  - [{title}]({v.link}) — {time_str}")
        if desc:
            lines.append(f"    > {desc}")
        # AI 摘要
        if summaries and v.video_id in summaries:
            lines.append(f"    > 🤖 **AI摘要**: {summaries[v.video_id]}")

    return "\n".join(lines)


def generate_daily_report(
    all_videos: dict,
    new_videos: dict,
    errors: list = None,
    summaries: dict[str, str] = None,
) -> str:
    """生成每日中文 Markdown 报告.

    Args:
        all_videos: {频道名称: [VideoInfo, ...]} — 当前抓取的全部视频
        new_videos: {频道名称: [VideoInfo, ...]} — 本轮新出现的视频
        errors: [(频道名称, 错误信息), ...] — 抓取出错的频道

    Returns:
        Markdown 格式的完整报告
    """
    today = datetime.now(UTC) + timedelta(hours=8)
    date_str = today.strftime("%Y-%m-%d")
    total_new = sum(len(v) for v in new_videos.values())
    sum(len(v) for v in all_videos.values())
    active_channels = sum(1 for v in all_videos.values() if v)

    lines = [
        f"# YouTube AI 博主动态日报 {date_str}",
        "",
        "---",
        "",
    ]

    # ====== 摘要 ======
    lines.append("## 📊 今日摘要")
    lines.append("")
    lines.append(f"- **监测频道**: {len(config.CHANNELS)} 个")
    lines.append(f"- **活跃频道**: {active_channels} 个（近 7 天有更新）")
    lines.append(f"- **本次新增**: {total_new} 个视频")

    # 最近活跃时间
    latest = None
    for videos in all_videos.values():
        if videos:
            v = videos[0]
            if latest is None or v.published > latest.published:
                latest = v
    if latest:
        lines.append(f"- **最近更新**: {latest.channel_name} — {_format_time(latest.published)}")

    if errors:
        lines.append(f"- **抓取异常**: {len(errors)} 个频道")

    lines.append("")

    # ====== 各分类报告 ======
    categories = config.get_categories()

    for cat in categories:
        cat_channels = config.get_channels_by_category(cat)
        has_any_content = any(ch.name in all_videos or ch.name in new_videos for ch in cat_channels)
        if not has_any_content:
            continue

        lines.append("---")
        lines.append("")
        emoji = {"AI发展趋势类": "📈", "AI技术教程类": "🛠", "效率提升和一人公司类": "🚀"}
        lines.append(f"## {emoji.get(cat, '📌')} {cat}")
        lines.append("")

        for ch in cat_channels:
            all_ch = all_videos.get(ch.name, [])
            new_ch = new_videos.get(ch.name, [])
            new_count = len(new_ch)
            total_count = len(all_ch)

            badge = f" ({new_count} 新 / {total_count} 总)" if total_count > 0 else ""
            lines.append(f"### {ch.name}{badge}")

            # 取新视频 + 最近视频（优先展示新的，如果没有新视频则展示最近的）
            display_videos = new_ch if new_ch else all_ch
            section = _build_channel_section(
                ch.name, ch.handle, display_videos, summaries=summaries
            )
            lines.append(section)
            lines.append("")

    # ====== 错误报告 ======
    if errors:
        lines.append("---")
        lines.append("")
        lines.append("## ⚠️ 抓取异常")
        lines.append("")
        for name, err in errors:
            lines.append(f"- ❌ **{name}**: {err}")
        lines.append("")

    # ====== 页脚 ======
    now_str = today.strftime("%Y-%m-%d %H:%M")
    lines.append("---")
    lines.append("")
    lines.append(f"*🤖 自动生成 | 数据来源: YouTube RSS | 生成时间: {now_str}*")
    lines.append("")

    return "\n".join(lines)


def save_report(report: str) -> str:
    """将报告保存到 mailbox 目录.

    Returns:
        报告文件路径
    """
    today = datetime.now(UTC) + timedelta(hours=8)
    filename = f"youtube-daily-{today.strftime('%Y-%m-%d')}.md"
    filepath = os.path.join(config.MAILBOX_DIR, filename)

    os.makedirs(config.MAILBOX_DIR, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)

    logger.info("报告已保存: %s", filepath)
    return filepath
