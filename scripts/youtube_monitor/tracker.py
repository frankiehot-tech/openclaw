"""增量跟踪模块：记录已处理的视频 ID，确保只报告新视频."""

import json
import logging
import os
from datetime import UTC, datetime

from . import config

logger = logging.getLogger(__name__)

# JSON 持久化文件
TRACKER_FILE = os.path.join(config.DATA_DIR, "youtube_tracker.json")


def _load() -> dict:
    """加载跟踪数据."""
    if not os.path.exists(TRACKER_FILE):
        return {"videos": {}, "last_run": None}
    try:
        with open(TRACKER_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("跟踪文件损坏，重置: %s", e)
        return {"videos": {}, "last_run": None}


def _save(data: dict):
    """保存跟踪数据."""
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(TRACKER_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def is_new(video_id: str) -> bool:
    """检查视频是否未处理过."""
    data = _load()
    return video_id not in data.get("videos", {})


def mark_processed(video_id: str):
    """将视频标记为已处理."""
    data = _load()
    data.setdefault("videos", {})[video_id] = datetime.now(UTC).isoformat()
    _save(data)


def mark_all_processed(video_ids: set[str]):
    """批量标记多个视频为已处理."""
    data = _load()
    now = datetime.now(UTC).isoformat()
    for vid in video_ids:
        if vid not in data.get("videos", {}):
            data.setdefault("videos", {})[vid] = now
    _save(data)


def get_new_videos(all_videos: dict[str, list]) -> dict[str, list]:
    """从所有频道视频中筛选出未处理的新视频.

    Args:
        all_videos: {频道名称: [VideoInfo, ...]} 字典

    Returns:
        仅包含新视频的 {频道名称: [VideoInfo, ...]} 字典
    """
    result = {}
    total_new = 0

    for channel_name, videos in all_videos.items():
        new = [v for v in videos if is_new(v.video_id)]
        if new:
            result[channel_name] = new
            total_new += len(new)
            # 立即标记为已处理，避免重复
            for v in new:
                mark_processed(v.video_id)

    logger.info("增量统计: 共 %d 个新视频", total_new)
    return result


def mark_current_as_seen(all_videos: dict[str, list]):
    """将当前所有视频标记为已处理（首次运行时调用，避免报告历史视频）."""
    all_ids = set()
    for videos in all_videos.values():
        for v in videos:
            all_ids.add(v.video_id)
    mark_all_processed(all_ids)
    logger.info("首次初始化: 已标记 %d 个现有视频为已处理", len(all_ids))


def is_first_run() -> bool:
    """判断是否为首次运行（跟踪文件为空或无数据）."""
    data = _load()
    return not data.get("videos")


def record_run():
    """记录本次运行时间."""
    data = _load()
    data["last_run"] = datetime.now(UTC).isoformat()
    _save(data)


def get_last_run() -> str:
    """获取上次运行时间."""
    data = _load()
    return data.get("last_run", "从未运行")


# ====== AI 摘要缓存接口 ======


def get_summaries() -> dict[str, str]:
    """获取所有缓存的视频摘要."""
    data = _load()
    return data.get("summaries", {})


def save_summaries(summaries: dict[str, str]):
    """保存视频摘要到缓存."""
    data = _load()
    existing = data.get("summaries", {})
    existing.update(summaries)
    data["summaries"] = existing
    _save(data)
