#!/usr/bin/env python3
"""
Codex缓存指标收集器

将Codex缓存统计集成到现有artifacts/metrics系统。
定期收集缓存命中率、节省时间等指标，并写入workspace/artifacts目录。
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# 导入根目录助手
try:
    from openclaw_roots import RUNTIME_ROOT
except ImportError:
    # 如果无法导入，使用当前脚本的父目录的父目录
    RUNTIME_ROOT = Path(__file__).parent.parent

# 添加项目根目录到路径
project_root = RUNTIME_ROOT
sys.path.insert(0, str(project_root))

# 添加 mini-agent 目录到路径
mini_agent_dir = project_root / "mini_agent"
if str(mini_agent_dir) not in sys.path:
    sys.path.insert(0, str(mini_agent_dir))

# 也添加实际的 mini-agent 目录
mini_agent_actual = project_root / "mini-agent"
if str(mini_agent_actual) not in sys.path:
    sys.path.insert(0, str(mini_agent_actual))

try:
    from mini_agent.agent.core.codex_cache import CodexCache, get_cache
except ImportError as e:
    # 尝试使用绝对导入
    import sys

    sys.path.insert(0, "/Volumes/1TB-M2/openclaw/mini-agent")
    sys.path.insert(0, "/Volumes/1TB-M2/openclaw")
    from mini_agent.agent.core.codex_cache import CodexCache, get_cache

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class CodexCacheMetricsCollector:
    """Codex缓存指标收集器"""

    def __init__(self, artifacts_dir: Optional[Path] = None):
        """
        初始化收集器

        Args:
            artifacts_dir: artifacts目录，默认在workspace/artifacts/
        """
        if artifacts_dir is None:
            artifacts_dir = project_root / "workspace" / "artifacts"

        self.artifacts_dir = artifacts_dir
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        self.cache = get_cache()

        logger.info(f"Codex缓存指标收集器初始化完成，artifacts目录: {self.artifacts_dir}")

    def collect_metrics(self) -> Dict[str, Any]:
        """
        收集缓存指标

        Returns:
            指标数据字典
        """
        # 获取缓存报告
        report = self.cache.generate_report()

        # 获取详细统计
        stats = self.cache.get_stats()

        # 构建指标数据
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "metric_source": "codex_cache",
            "metric_version": "1.0",
            # 核心指标
            "cache_hit_rate": stats["hit_rate"],
            "cache_total_hits": stats["total_hits"],
            "cache_total_misses": stats["total_misses"],
            "cache_total_entries": stats["total_entries"],
            # 节省估算
            "estimated_time_saved_seconds": stats["total_save_seconds"],
            "estimated_tokens_saved": stats["total_save_tokens"],
            "avg_time_saved_per_hit": stats.get("avg_save_seconds_per_hit", 0.0),
            # 缓存健康状态
            "cache_health_status": report["health"]["status"],
            "cache_memory_entries": report["memory_entries"],
            # 按来源分布
            "sources_distribution": stats.get("by_source", {}),
            # 过期/陈旧状态
            "expired_entries": stats.get("total_expired", 0),
            "stale_entries": stats.get("total_stale", 0),
        }

        logger.info(
            f"收集到缓存指标: 命中率={stats['hit_rate']:.2%}, "
            f"节省时间={stats['total_save_seconds']:.1f}秒"
        )

        return metrics

    def save_metrics(self, metrics: Dict[str, Any], filename: Optional[str] = None) -> Path:
        """
        保存指标到文件

        Args:
            metrics: 指标数据
            filename: 文件名，默认为codex_cache_metrics_YYYYMMDD_HHMMSS.json

        Returns:
            保存的文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"codex_cache_metrics_{timestamp}.json"

        filepath = self.artifacts_dir / filename

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(metrics, f, indent=2, ensure_ascii=False)

            logger.info(f"缓存指标已保存到: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"保存缓存指标失败: {e}")
            raise

    def collect_and_save(self) -> Path:
        """收集并保存指标（一步完成）"""
        metrics = self.collect_metrics()
        return self.save_metrics(metrics)

    def generate_daily_summary(self) -> Optional[Dict[str, Any]]:
        """
        生成每日摘要

        从当日所有指标文件中生成摘要报告
        """
        try:
            # 查找当日的指标文件
            today_prefix = datetime.now().strftime("%Y%m%d")
            pattern = f"codex_cache_metrics_{today_prefix}_*.json"

            metric_files = list(self.artifacts_dir.glob(pattern))

            if not metric_files:
                logger.warning("未找到当日的缓存指标文件")
                return None

            # 读取所有指标
            all_metrics = []
            for filepath in metric_files:
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        metrics = json.load(f)
                        all_metrics.append(metrics)
                except Exception as e:
                    logger.warning(f"读取指标文件失败 {filepath}: {e}")
                    continue

            if not all_metrics:
                return None

            # 计算摘要
            hit_rates = [m.get("cache_hit_rate", 0) for m in all_metrics]
            total_hits = [m.get("cache_total_hits", 0) for m in all_metrics]
            time_saved = [m.get("estimated_time_saved_seconds", 0) for m in all_metrics]

            summary = {
                "timestamp": datetime.now().isoformat(),
                "summary_type": "codex_cache_daily",
                "date": today_prefix,
                # 统计信息
                "metric_count": len(all_metrics),
                "time_period_hours": 24,
                # 性能指标
                "avg_hit_rate": sum(hit_rates) / len(hit_rates) if hit_rates else 0,
                "max_hit_rate": max(hit_rates) if hit_rates else 0,
                "min_hit_rate": min(hit_rates) if hit_rates else 0,
                "total_hits_today": sum(total_hits),
                "total_time_saved_today": sum(time_saved),
                # 趋势分析
                "trend": self._analyze_trend(all_metrics),
                # 建议
                "recommendations": self._generate_recommendations(all_metrics),
            }

            # 保存摘要
            summary_file = self.artifacts_dir / f"codex_cache_summary_{today_prefix}.json"
            with open(summary_file, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)

            logger.info(f"每日摘要已生成: {summary_file}")
            return summary

        except Exception as e:
            logger.error(f"生成每日摘要失败: {e}")
            return None

    def _analyze_trend(self, metrics: list) -> Dict[str, Any]:
        """分析趋势"""
        if len(metrics) < 2:
            return {"status": "insufficient_data", "message": "需要至少2个数据点"}

        # 按时间排序
        sorted_metrics = sorted(metrics, key=lambda x: x.get("timestamp", ""))

        # 计算命中率趋势
        first_hit_rate = sorted_metrics[0].get("cache_hit_rate", 0)
        last_hit_rate = sorted_metrics[-1].get("cache_hit_rate", 0)

        hit_rate_trend = (
            "improving"
            if last_hit_rate > first_hit_rate
            else "declining" if last_hit_rate < first_hit_rate else "stable"
        )

        return {
            "hit_rate_trend": hit_rate_trend,
            "hit_rate_change": last_hit_rate - first_hit_rate,
            "data_points": len(metrics),
            "analysis_period_hours": 24,
        }

    def _generate_recommendations(self, metrics: list) -> list:
        """生成建议"""
        recommendations = []

        if not metrics:
            return ["没有足够的数据生成建议"]

        # 计算平均命中率
        avg_hit_rate = sum(m.get("cache_hit_rate", 0) for m in metrics) / len(metrics)

        if avg_hit_rate < 0.1:
            recommendations.append("缓存命中率低 (<10%)，考虑调整相似性阈值或增加缓存多样性")

        if avg_hit_rate > 0.7:
            recommendations.append("缓存命中率高 (>70%)，缓存效果良好，可以考虑扩大缓存容量")

        # 检查过期条目
        expired_total = sum(m.get("expired_entries", 0) for m in metrics)
        if expired_total > 10:
            recommendations.append(f"过期条目较多 ({expired_total})，考虑增加TTL或改进缓存更新策略")

        # 检查缓存大小
        entries_total = sum(m.get("cache_total_entries", 0) for m in metrics)
        avg_entries = entries_total / len(metrics)

        if avg_entries < 5:
            recommendations.append("缓存条目较少，考虑增加缓存填充或降低相似性匹配阈值")

        if avg_entries > 100:
            recommendations.append("缓存条目较多 (>100)，考虑实施LRU清理策略")

        return recommendations

    def cleanup_old_files(self, days_to_keep: int = 7):
        """
        清理旧指标文件

        Args:
            days_to_keep: 保留天数
        """
        import time
        from datetime import datetime, timedelta

        cutoff_time = time.time() - (days_to_keep * 86400)

        deleted_count = 0
        for filepath in self.artifacts_dir.glob("codex_cache_*.json"):
            if filepath.stat().st_mtime < cutoff_time:
                try:
                    filepath.unlink()
                    deleted_count += 1
                    logger.debug(f"删除旧文件: {filepath}")
                except Exception as e:
                    logger.warning(f"删除文件失败 {filepath}: {e}")

        if deleted_count > 0:
            logger.info(f"清理完成: 删除 {deleted_count} 个旧缓存指标文件")

        return deleted_count


def main() -> int:
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Codex缓存指标收集器")
    parser.add_argument(
        "action",
        nargs="?",
        default="collect",
        choices=["collect", "summary", "cleanup", "all"],
        help="执行的操作: collect (收集指标, 默认), summary (生成摘要), cleanup (清理旧文件), all (全部执行)",
    )
    parser.add_argument(
        "--artifacts-dir",
        help="artifacts目录路径 (默认: workspace/artifacts)",
    )
    parser.add_argument(
        "--keep-days",
        type=int,
        default=7,
        help="清理时保留的天数 (默认: 7)",
    )

    args = parser.parse_args()

    try:
        # 初始化收集器
        artifacts_dir = Path(args.artifacts_dir) if args.artifacts_dir else None
        collector = CodexCacheMetricsCollector(artifacts_dir)

        if args.action in ["collect", "all"]:
            print("收集缓存指标...")
            filepath = collector.collect_and_save()
            print(f"✅ 指标已保存到: {filepath}")

        if args.action in ["summary", "all"]:
            print("生成每日摘要...")
            summary = collector.generate_daily_summary()
            if summary:
                print(f"✅ 每日摘要已生成")
                print(f"   平均命中率: {summary['avg_hit_rate']:.2%}")
                print(f"   今日总命中数: {summary['total_hits_today']}")
                print(f"   今日总节省时间: {summary['total_time_saved_today']:.1f}秒")
            else:
                print("⚠️  无法生成摘要 (数据不足)")

        if args.action in ["cleanup", "all"]:
            print(f"清理 {args.keep_days} 天前的旧文件...")
            deleted = collector.cleanup_old_files(days_to_keep=args.keep_days)
            print(f"✅ 清理完成: 删除 {deleted} 个文件")

        return 0

    except Exception as e:
        logger.error(f"执行失败: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
