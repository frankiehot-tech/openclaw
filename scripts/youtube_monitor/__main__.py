"""CLI 入口：测试 RSS 抓取、增量跟踪、报告生成."""

import logging
import sys

from . import config
from .fetcher import fetch_all_channels, fetch_channel_feed
from .reporter import generate_daily_report, save_report
from .tracker import get_last_run, get_new_videos, is_first_run, mark_current_as_seen, record_run

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("youtube_monitor")


def cmd_check_ids():
    """检查哪些频道缺少 channel_id."""
    incomplete = config.get_incomplete_channels()
    if not incomplete:
        print("✅ 所有 channel_id 已配置")
        return

    print(f"⚠️  以下 {len(incomplete)} 个频道缺少 channel_id：")
    for ch in incomplete:
        print(f"\n  {ch.name} ({ch.handle})")
        print("  获取方法：")
        print(f"    1. 浏览器打开 https://www.youtube.com/{ch.handle}")
        print("    2. 查看页面源码（右键 → 查看网页源代码）")
        print("    3. 搜索 channelId 或 externalId")
        print("    4. 复制 UC 开头的 24 位 ID 到 config.py 的 channel_id 字段")


def cmd_fetch_one(channel_name: str):
    """测试抓取单个频道."""
    matches = [c for c in config.CHANNELS if c.name.lower() == channel_name.lower()]
    if not matches:
        print(f"❌ 未找到频道: {channel_name}")
        print(f"可选: {[c.name for c in config.CHANNELS]}")
        return

    ch = matches[0]
    if not ch.channel_id:
        print(f"⚠️  {ch.name} 缺少 channel_id，请先补充")
        return

    try:
        videos = fetch_channel_feed(ch.channel_id)
        print(f"\n✅ {ch.name} - 获取到 {len(videos)} 个视频：")
        for v in videos:
            pub = v.published.strftime("%m-%d %H:%M")
            print(f"  [{pub}] {v.title[:70]}")
            print(f"         {v.link}")
    except Exception as e:
        print(f"❌ 抓取失败: {e}")


def cmd_fetch_all():
    """测试抓取所有已配置的频道."""
    results, errors = fetch_all_channels()
    total = sum(len(v) for v in results.values())
    print(f"\n📊 共 {len(results)} 个频道，{total} 个视频：")
    for name, videos in results.items():
        print(f"  ✅ {name}: {len(videos)} 个视频")
    if errors:
        print("\n⚠️  以下频道抓取出错：")
        for name, err in errors:
            print(f"  ❌ {name}: {err}")


def cmd_init():
    """首次初始化：标记当前所有视频为已处理，下次只报告新视频."""
    if not is_first_run():
        print("⚠️  已经初始化过，如需重置请删除 data/youtube_tracker.json")
        return

    print("🔄 首次初始化：抓取所有频道，标记现有视频为已处理...")
    print("   （之后每天运行只会报告新出现的视频）")
    results, errors = fetch_all_channels()

    total = sum(len(v) for v in results.values())
    mark_current_as_seen(results)
    record_run()

    print(f"\n✅ 初始化完成！已标记 {total} 个现有视频")
    if errors:
        print(f"⚠️  {len(errors)} 个频道有错误（已在日志中记录）")
    print("   明天开始每天运行就会只报告新视频了。")


def cmd_report():
    """执行完整流程：抓取 → 增量跟踪 → 生成报告 → 保存."""
    print("🔄 正在抓取所有频道...")
    all_videos, errors = fetch_all_channels()

    if is_first_run():
        print("📌 首次运行，初始化所有视频...")
        mark_current_as_seen(all_videos)
        record_run()
        print("✅ 初始化完成，明天起开始生成报告")
        return

    # 筛选新视频
    new_videos = get_new_videos(all_videos)
    total_new = sum(len(v) for v in new_videos.values())

    print(f"\n📊 新视频: {total_new} 个")

    # AI 摘要（DeepSeek）
    summaries = None
    if total_new > 0:
        print("🤖 正在生成 AI 摘要...")
        from .summarizer import summarize_new_videos

        summaries = summarize_new_videos(all_videos, new_videos)
        if summaries:
            print(f"✅ AI 摘要: {len(summaries)} 条\n")

    # 生成报告（含 AI 摘要）
    report = generate_daily_report(all_videos, new_videos, errors, summaries=summaries)

    # 保存并打印摘要
    filepath = save_report(report)
    record_run()

    print(f"\n✅ 报告已保存: {filepath}")

    # 打印简短摘要
    for cat in config.get_categories():
        channels = config.get_channels_by_category(cat)
        for ch in channels:
            n = len(new_videos.get(ch.name, []))
            if n > 0:
                print(f"  {ch.name}: {n} 个新视频")

    return filepath


def cmd_status():
    """查看当前状态."""
    print(f"上次运行: {get_last_run()}")
    print(f"目标路径: {config.MAILBOX_DIR}")
    print(f"数据文件: {config.DATA_DIR}")
    print()

    incomplete = config.get_incomplete_channels()
    if incomplete:
        print(f"⚠️  待补充 channel_id: {[c.name for c in incomplete]}")
    else:
        print("✅ 所有 channel_id 已配置")

    from .tracker import _load

    data = _load()
    count = len(data.get("videos", {}))
    summaries = len(data.get("summaries", {}))
    print(f"已跟踪视频: {count} 个")
    print(f"AI 摘要缓存: {summaries} 条")


def main():
    if len(sys.argv) < 2:
        print("用法: python -m scripts.youtube_monitor <command> [args]")
        print("")
        print("命令:")
        print("  check        检查 channel_id 配置")
        print('  fetch-one "频道名"  测试抓取单个频道')
        print("  fetch-all    测试抓取所有频道")
        print("  init         首次初始化（标记现有视频为已处理）")
        print("  report       执行完整流程：抓取 → 报告 → 保存（含 AI 摘要）")
        print("  status       查看当前状态")
        return

    cmd = sys.argv[1]
    if cmd == "check":
        cmd_check_ids()
    elif cmd == "fetch-one" and len(sys.argv) > 2:
        cmd_fetch_one(sys.argv[2])
    elif cmd == "fetch-all":
        cmd_fetch_all()
    elif cmd == "init":
        cmd_init()
    elif cmd == "report":
        cmd_report()
    elif cmd == "status":
        cmd_status()
    else:
        print(f"未知命令: {cmd}")
        print("可用命令: check, fetch-one, fetch-all, init, report, status")


if __name__ == "__main__":
    main()
