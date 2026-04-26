"""YouTube RSS 抓取和解析模块.

使用 YouTube 公开的 RSS Feed 获取频道最新视频，无需 API Key。
"""

import logging
import os
import re
import ssl
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from urllib import request
from urllib.error import URLError

from . import config

logger = logging.getLogger(__name__)

# RSS XML 命名空间
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}


@dataclass
class VideoInfo:
    """单个视频信息."""

    video_id: str  # YouTube 视频 ID
    title: str  # 视频标题
    link: str  # 视频链接
    published: datetime  # 发布时间（UTC）
    updated: Optional[datetime] = None  # 更新时间
    description: str = ""  # 简介摘要
    thumbnail: str = ""  # 缩略图 URL
    channel_name: str = ""  # 频道名称
    channel_id: str = ""  # 频道 ID

    @property
    def age_hours(self) -> float:
        """视频发布至今的小时数."""
        return (datetime.now(timezone.utc) - self.published).total_seconds() / 3600

    @property
    def is_recent(self, hours: int = 48) -> bool:
        """是否在指定小时内发布."""
        return self.age_hours <= hours


def _build_rss_url(channel_id: str) -> str:
    """构建 YouTube RSS Feed URL."""
    return config.RSS_BASE_URL.format(channel_id=channel_id)


def _build_opener() -> request.OpenerDirector:
    """构建 urllib opener，支持代理和宽松 SSL.

    优先级: config.PROXY > HTTP_PROXY 环境变量 > 直连
    """
    # 宽松 SSL：兼容某些代理的 SNI/SSL 问题
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    handlers = [request.HTTPSHandler(context=ctx)]

    proxy = config.PROXY or os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")
    if proxy:
        logger.info("使用代理: %s", proxy)
        handlers.append(
            request.ProxyHandler({
                "http": proxy,
                "https": proxy,
            })
        )

    return request.build_opener(*handlers)


def _parse_datetime(text: Optional[str]) -> Optional[datetime]:
    """解析 ISO 8601 时间字符串."""
    if not text:
        return None
    try:
        # Python 3.7+ 支持从 isoformat 解析
        # 处理末尾可能缺少的 Z
        text = text.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text)
    except (ValueError, TypeError):
        logger.warning("无法解析时间: %s", text)
        return None


def _extract_video_id_from_link(link: str) -> str:
    """从视频链接中提取 video_id."""
    match = re.search(r"(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})", link)
    return match.group(1) if match else ""


def fetch_channel_feed(channel_id: str, max_results: int = 15) -> List[VideoInfo]:
    """抓取单个频道的 RSS Feed, 返回最新视频列表.

    Args:
        channel_id: YouTube 频道 ID (UC 开头)
        max_results: 最多返回的视频数

    Returns:
        VideoInfo 列表，按发布时间降序

    Raises:
        ValueError: 频道 ID 为空
        URLError: 网络请求失败
    """
    if not channel_id:
        raise ValueError(f"无效的 channel_id: '{channel_id}'，请在 config.py 中补充")

    url = _build_rss_url(channel_id)
    logger.info("正在抓取 RSS: %s", url)

    req = request.Request(
        url,
        headers={
            "User-Agent": config.USER_AGENT,
        },
    )

    opener = _build_opener()
    # 重试机制：某些代理节点路由会导致偶发 SSL 错误
    last_error = None
    for attempt in range(3):
        try:
            with opener.open(req, timeout=15) as resp:
                raw = resp.read()
            break
        except URLError as e:
            last_error = e
            logger.warning("第 %d 次重试失败: %s", attempt + 1, e)
            time.sleep(1)
    else:
        raise last_error  # type: ignore

    root = ET.fromstring(raw)
    videos: List[VideoInfo] = []

    # RSS 中的每个 <entry> 对应一个视频
    for entry in root.findall("atom:entry", NS):
        video_id_el = entry.find("yt:videoId", NS)
        video_id = video_id_el.text if video_id_el is not None else ""

        title_el = entry.find("atom:title", NS)
        title = title_el.text.strip() if title_el is not None and title_el.text else ""

        link_el = entry.find("atom:link", NS)
        link = link_el.get("href", "") if link_el is not None else ""

        published_el = entry.find("atom:published", NS)
        published = _parse_datetime(
            published_el.text if published_el is not None else None
        ) or datetime.now(timezone.utc)

        updated_el = entry.find("atom:updated", NS)
        updated = _parse_datetime(
            updated_el.text if updated_el is not None else None
        )

        # 简介可能在 <media:group><media:description> 或 <media:description> 中
        description = ""
        media_group = entry.find("media:group", NS)
        if media_group is not None:
            desc_el = media_group.find("media:description", NS)
            if desc_el is not None and desc_el.text:
                description = desc_el.text.strip()

            thumbnail_el = media_group.find("media:thumbnail", NS)
            thumbnail = thumbnail_el.get("url", "") if thumbnail_el is not None else ""
        else:
            thumbnail = ""

        # 如果没有 video_id，从链接提取
        if not video_id:
            video_id = _extract_video_id_from_link(link)

        if not video_id:
            logger.warning("跳过无法解析 video_id 的条目: %s", title)
            continue

        videos.append(
            VideoInfo(
                video_id=video_id,
                title=title,
                link=link,
                published=published,
                updated=updated,
                description=description,
                thumbnail=thumbnail,
                channel_name=entry.find("atom:author/*", NS).text if entry.find("atom:author/*", NS) is not None else "",
                channel_id=channel_id,
            )
        )

    # 按发布时间降序排列
    videos.sort(key=lambda v: v.published, reverse=True)

    return videos[:max_results]


def fetch_all_channels(
    max_per_channel: int = None,
    skip_empty_id: bool = True,
) -> Tuple[dict, list]:
    """抓取所有已配置频道的视频.

    Args:
        max_per_channel: 每个频道最多获取数，默认使用 config 值
        skip_empty_id: 是否跳过缺少 channel_id 的频道

    Returns:
        {频道名称: [VideoInfo, ...]} 的字典
    """
    if max_per_channel is None:
        max_per_channel = config.MAX_VIDEOS_PER_CHANNEL

    results = {}
    errors = []

    for channel in config.CHANNELS:
        if skip_empty_id and not channel.channel_id:
            logger.warning("跳过 %s（channel_id 为空，请在 config.py 中补充）", channel.name)
            errors.append((channel.name, ValueError("channel_id 为空")))
            continue

        try:
            videos = fetch_channel_feed(channel.channel_id, max_per_channel)
            results[channel.name] = videos
            logger.info(
                "%s: 获取到 %d 个视频",
                channel.name,
                len(videos),
            )
        except URLError as e:
            logger.error("%s: 网络错误: %s", channel.name, e)
            errors.append((channel.name, e))
        except Exception as e:
            logger.error("%s: 未知错误: %s", channel.name, e)
            errors.append((channel.name, e))

        # 礼貌间隔，避免被限流
        time.sleep(0.5)

    return results, errors
