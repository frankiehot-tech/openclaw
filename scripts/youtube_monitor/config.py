"""频道配置和目标路径."""

from dataclasses import dataclass, field
from typing import List
import os

# ============================================================
# 频道配置
# ============================================================


@dataclass
class YouTubeChannel:
    """单个 YouTube 频道配置."""

    name: str  # 博主名称
    category: str  # 分类
    handle: str  # YouTube @handle
    channel_id: str  # UC 开头的频道 ID
    description: str = ""  # 简短介绍


# fmt: off
CHANNELS = [
    # ========== AI发展趋势类 ==========
    YouTubeChannel(
        name="Y Combinator",
        category="AI发展趋势类",
        handle="@ycombinator",
        channel_id="UCcefcZRL2oaA_uBNeo5UOWg",
        description="硅谷顶尖创意加速器，孵化 OpenAI、Dropbox 等",
    ),
    YouTubeChannel(
        name="Dwarkesh Patel",
        category="AI发展趋势类",
        handle="@DwarkeshPatel",
        channel_id="UCZa18YV7qayTh-MRIrBhDpA",
        description="硅谷顶流 AI 深度访谈博主",
    ),
    YouTubeChannel(
        name="No Priors",
        category="AI发展趋势类",
        handle="@NoPriorsPodcast",
        channel_id="UCSI7h9hydQ40K5MJHnCrQvw",
        description="AI 创业和投资实战内部视角播客",
    ),
    # ========== AI技术教程类 ==========
    YouTubeChannel(
        name="Tina Huang",
        category="AI技术教程类",
        handle="@TinaHuang1",
        channel_id="UC2UXDak6o7rBm23k3Vv5dww",
        description="前 Meta 数据科学家，AI 工具实战",
    ),
    YouTubeChannel(
        name="Jeff Su",
        category="AI技术教程类",
        handle="@JeffSu",
        channel_id="UCwAnu01qlnVg1Ai2AbtTMaA",
        description="前 Google/字节市场经理，AI 办公实战",
    ),
    YouTubeChannel(
        name="Andrej Karpathy",
        category="AI技术教程类",
        handle="@AndrejKarpathy",
        channel_id="UCXUPKJO5MZQN11PqgIvyuvQ",
        description="前 Tesla AI 负责人，OpenAI 创始成员",
    ),
    # ========== 效率提升和一人公司类 ==========
    YouTubeChannel(
        name="Ali Abdaal",
        category="效率提升和一人公司类",
        handle="@AliAbdaal",
        channel_id="UCoOae5nYA7VqaXzerajD0lg",
        description="剑桥医学博士，《幸福生产力》作者",
    ),
    YouTubeChannel(
        name="Tiago Forte",
        category="效率提升和一人公司类",
        handle="@tiagoforte",
        channel_id="UCmvYCRYPDlzSHVNCI_ViJDQ",
        description="第二大脑理论创始人，PARA 分类法",
    ),
    YouTubeChannel(
        name="Dan Koe",
        category="效率提升和一人公司类",
        handle="@DanKoe",
        channel_id="UCWXYDYv5STLk-zoxMP2I1Lw",
        description="一人公司超级个体代表",
    ),
]
# fmt: on


def get_channels_by_category(category: str) -> List[YouTubeChannel]:
    """按分类获取频道列表."""
    return [c for c in CHANNELS if c.category == category]


def get_categories() -> List[str]:
    """获取所有不重复的分类."""
    seen: List[str] = []
    for c in CHANNELS:
        if c.category not in seen:
            seen.append(c.category)
    return seen


def get_incomplete_channels() -> List[YouTubeChannel]:
    """获取缺少 channel_id 的频道（需要手动补充）."""
    return [c for c in CHANNELS if not c.channel_id]


# ============================================================
# 路径配置
# ============================================================

# 报告输出目录
MAILBOX_DIR = os.path.join(
    os.path.sep, "Volumes", "1TB-M2",
    "Athena知识库", "执行项目", "2026",
    "003-open human（碳硅基共生）", "015-mailbox",
)

_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

# 数据持久化目录（跟踪已处理的视频）
DATA_DIR = os.path.join(_PROJECT_ROOT, "data")

# 日志目录
LOG_DIR = os.path.join(_PROJECT_ROOT, "logs", "youtube_monitor")

# RSS 基础 URL
RSS_BASE_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

# 每次抓取每个频道最多获取的视频数
MAX_VIDEOS_PER_CHANNEL = 15

# 用户代理（避免被 YouTube 屏蔽）
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# 代理配置（国内访问 YouTube 需要）
# 支持格式: "http://127.0.0.1:7890" 或 "socks5://127.0.0.1:1080"
# 也可以通过 HTTP_PROXY / HTTPS_PROXY 环境变量设置
PROXY = ""  # 填写你的代理地址，留空则直连
