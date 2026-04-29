"""DeepSeek AI 视频摘要模块：为新视频生成中文内容提炼."""

import json
import logging
import os

import requests

from .fetcher import VideoInfo

logger = logging.getLogger(__name__)

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"


def _load_summaries() -> dict[str, str]:
    """从 tracker 加载已缓存的摘要."""
    from .tracker import get_summaries

    return get_summaries()


def _save_summaries(summaries: dict[str, str]):
    """保存摘要到 tracker."""
    from .tracker import save_summaries

    save_summaries(summaries)


def _call_deepseek(prompt: str) -> str:
    """调用 DeepSeek 聊天补全 API."""
    if not DEEPSEEK_API_KEY:
        logger.warning("DEEPSEEK_API_KEY 未设置")
        return ""

    try:
        resp = requests.post(
            DEEPSEEK_API_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": DEEPSEEK_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 300,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except requests.exceptions.Timeout:
        logger.warning("DeepSeek 请求超时")
    except requests.exceptions.HTTPError as e:
        logger.warning("DeepSeek HTTP 错误: %s", e)
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        logger.warning("DeepSeek 响应解析失败: %s", e)
    except requests.exceptions.RequestException as e:
        logger.warning("DeepSeek 请求失败: %s", e)
    return ""


def _build_prompt(video: VideoInfo) -> str:
    """构建摘要提示词."""
    desc = video.description[:500] if video.description else "（无简介）"
    return (
        f"你是一个AI内容分析师。请用中文总结以下YouTube视频的核心内容。\n\n"
        f"标题：{video.title}\n"
        f"简介：{desc}\n\n"
        f"请用2-4句话概括这个视频的主要内容、关键观点和实用价值。保持简洁直接，不要使用markdown格式。"
    )


def summarize_video(video: VideoInfo) -> str:
    """为单个视频生成中文摘要（无缓存，直接调用 API）."""
    prompt = _build_prompt(video)
    logger.info("正在摘要: %s", video.title[:50])
    return _call_deepseek(prompt)


def summarize_new_videos(
    all_videos: dict[str, list],
    new_videos: dict[str, list],
) -> dict[str, str]:
    """为所有新视频生成中文摘要，已缓存的跳过.

    Args:
        all_videos: {频道名称: [VideoInfo, ...]} — 全部视频
        new_videos: {频道名称: [VideoInfo, ...]} — 本轮新视频

    Returns:
        {video_id: summary_text} 字典（含缓存）
    """
    if not DEEPSEEK_API_KEY:
        logger.info("DEEPSEEK_API_KEY 未设置，跳过 AI 摘要")
        return {}

    cached = _load_summaries()
    result = dict(cached)

    # 收集需要摘要的新视频（排除已缓存）
    to_summarize = []
    for _channel_name, videos in new_videos.items():
        for v in videos:
            if v.video_id not in cached:
                to_summarize.append(v)

    if not to_summarize:
        logger.info("所有新视频已有缓存摘要，跳过 API 调用")
        return result

    logger.info("正在为 %d 个新视频生成 AI 摘要...", len(to_summarize))

    new_summaries = {}
    for v in to_summarize:
        summary = summarize_video(v)
        if summary:
            new_summaries[v.video_id] = summary
            result[v.video_id] = summary

    # 缓存到 tracker
    if new_summaries:
        _save_summaries(new_summaries)

    logger.info(
        "AI 摘要完成: %d / %d 成功",
        len(new_summaries),
        len(to_summarize),
    )
    return result
