#!/usr/bin/env python3
"""
Performance metrics collection for AutoResearch baseline.

Collects minimal metrics:
- queue throughput
- failure reason distribution
- stale rate
- execution latency

Outputs JSON baseline file for AutoResearch engine consumption.
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class QueueMetrics:
    """Metrics for a single queue."""

    queue_id: str
    total_items: int
    pending_items: int
    completed_items: int
    failed_items: int
    running_items: int
    stale_items: int  # pending > 24h
    throughput_last_24h: float  # tasks completed per hour
    avg_execution_latency: float | None  # hours
    failure_reasons: dict[str, int]  # error type -> count


@dataclass
class SystemMetrics:
    """Aggregated system performance metrics."""

    timestamp: str
    total_tasks: int
    total_completed: int
    total_failed: int
    total_pending: int
    total_stale: int
    overall_success_rate: float
    overall_throughput_24h: float
    avg_latency_all: float | None
    failure_reason_distribution: dict[str, int]
    queue_metrics: list[QueueMetrics]
    # Defensive metrics
    missing_artifacts_count: int
    duplicate_tasks_count: int
    data_quality_issues: list[str]
    metadata: dict[str, Any]


def _parse_datetime(dt_str: str) -> datetime:
    """Parse ISO datetime string, removing timezone info if present."""
    if not dt_str:
        raise ValueError("Empty datetime string")

    # Replace Z with +00:00 for consistent parsing
    if dt_str.endswith("Z"):
        dt_str = dt_str.replace("Z", "+00:00")

    try:
        dt = datetime.fromisoformat(dt_str)
    except ValueError:
        # Try alternative formats
        for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]:
            try:
                dt = datetime.strptime(dt_str, fmt)
                return dt.replace(tzinfo=None)
            except ValueError:
                pass
        raise

    # Convert to naive datetime (remove timezone)
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)

    return dt


class MetricsCollector:
    """Collect performance metrics from tasks and queues."""

    def __init__(self, runtime_root: Path):
        self.runtime_root = Path(runtime_root)
        self.tasks_path = self.runtime_root / ".openclaw" / "orchestrator" / "tasks.json"
        self.plan_queue_dir = self.runtime_root / ".openclaw" / "plan_queue"

    def collect(self) -> SystemMetrics:
        """Collect all metrics."""
        logger.info("Starting metrics collection...")

        # Load tasks data
        tasks_data = self._load_tasks_data()
        if not tasks_data:
            logger.warning("No tasks data found")
            tasks_data = {"tasks": []}

        tasks = tasks_data.get("tasks", [])

        # Calculate basic metrics
        now = datetime.now()
        twenty_four_hours_ago = now - timedelta(hours=24)

        completed_tasks = [t for t in tasks if t.get("status") == "completed"]
        failed_tasks = [t for t in tasks if t.get("status") == "failed"]
        pending_tasks = [t for t in tasks if t.get("status") == "pending"]
        [t for t in tasks if t.get("status") == "running"]

        # Calculate stale tasks (pending > 24h)
        stale_tasks = []
        for task in pending_tasks:
            created_str = task.get("created_at")
            if not created_str:
                continue
            try:
                created = _parse_datetime(created_str)
                if created < twenty_four_hours_ago:
                    stale_tasks.append(task)
            except ValueError:
                continue

        # Calculate throughput (tasks completed per hour in last 24h)
        recent_completed = []
        for task in completed_tasks:
            finished_str = task.get("finished_at")
            if not finished_str:
                continue
            try:
                finished = _parse_datetime(finished_str)
                if finished > twenty_four_hours_ago:
                    recent_completed.append(task)
            except ValueError:
                continue

        throughput = len(recent_completed) / 24.0 if recent_completed else 0.0

        # Calculate execution latency for completed tasks
        latencies = []
        for task in completed_tasks:
            started_str = task.get("started_at")
            finished_str = task.get("finished_at")
            if not started_str or not finished_str:
                continue
            try:
                started = _parse_datetime(started_str)
                finished = _parse_datetime(finished_str)
                latency = (finished - started).total_seconds() / 3600.0  # hours
                if latency >= 0:
                    latencies.append(latency)
            except ValueError:
                continue

        avg_latency = sum(latencies) / len(latencies) if latencies else None

        # Analyze failure reasons
        failure_reasons = {}
        for task in failed_tasks:
            error = task.get("error", "").strip()
            if error:
                # Simplify error message (first line or key phrase)
                if "error:" in error.lower():
                    # Extract after "error:"
                    parts = error.split(":", 1)
                    if len(parts) > 1:
                        key = parts[1].strip()[:50]
                    else:
                        key = error[:50]
                else:
                    key = error[:50]
                failure_reasons[key] = failure_reasons.get(key, 0) + 1
            else:
                failure_reasons["unknown"] = failure_reasons.get("unknown", 0) + 1

        # Collect queue metrics
        queue_metrics = self._collect_queue_metrics(tasks)

        # Overall success rate
        total_executed = len(completed_tasks) + len(failed_tasks)
        success_rate = len(completed_tasks) / total_executed if total_executed > 0 else 0.0

        # Defensive checks
        missing_artifacts = 0
        for task in completed_tasks:
            artifact_path = task.get("artifact_path", "").strip()
            if artifact_path:
                # Check if file exists
                if not Path(artifact_path).exists():
                    missing_artifacts += 1
            else:
                missing_artifacts += 1

        # Detect duplicate pending tasks (same queue_item_id)
        pending_by_queue_item = {}
        duplicate_count = 0
        for task in pending_tasks:
            queue_item_id = task.get("queue_item_id")
            if queue_item_id:
                if queue_item_id in pending_by_queue_item:
                    duplicate_count += 1
                else:
                    pending_by_queue_item[queue_item_id] = task

        # Data quality issues
        data_quality_issues = []
        # Check for tasks with missing timestamps
        for task in tasks:
            if not task.get("created_at"):
                data_quality_issues.append(f"Task {task.get('id', 'unknown')} missing created_at")
            if task.get("status") == "completed" and not task.get("finished_at"):
                data_quality_issues.append(
                    f"Completed task {task.get('id', 'unknown')} missing finished_at"
                )

        metrics = SystemMetrics(
            timestamp=now.isoformat(),
            total_tasks=len(tasks),
            total_completed=len(completed_tasks),
            total_failed=len(failed_tasks),
            total_pending=len(pending_tasks),
            total_stale=len(stale_tasks),
            overall_success_rate=success_rate,
            overall_throughput_24h=throughput,
            avg_latency_all=avg_latency,
            failure_reason_distribution=failure_reasons,
            queue_metrics=queue_metrics,
            missing_artifacts_count=missing_artifacts,
            duplicate_tasks_count=duplicate_count,
            data_quality_issues=data_quality_issues,
            metadata={
                "runtime_root": str(self.runtime_root),
                "tasks_file": str(self.tasks_path),
                "collection_version": "1.0",
            },
        )

        logger.info(
            f"Collected metrics: {len(tasks)} tasks, {len(completed_tasks)} completed, {len(failed_tasks)} failed"
        )
        return metrics

    def _load_tasks_data(self) -> dict[str, Any]:
        """Load tasks.json with error handling."""
        if not self.tasks_path.exists():
            logger.warning(f"Tasks file not found: {self.tasks_path}")
            return {}

        try:
            with open(self.tasks_path) as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse tasks.json: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error reading tasks.json: {e}")
            return {}

    def _collect_queue_metrics(self, tasks: list[dict[str, Any]]) -> list[QueueMetrics]:
        """Collect metrics per queue from plan_queue files."""
        queue_metrics = []

        if not self.plan_queue_dir.exists():
            logger.warning(f"Plan queue directory not found: {self.plan_queue_dir}")
            return queue_metrics

        # Group tasks by queue (from queue_config.queue_id or infer)
        queue_to_tasks: dict[str, list[dict[str, Any]]] = {}
        for task in tasks:
            queue_config = task.get("queue_config", {})
            queue_id = queue_config.get("queue_id")
            if not queue_id:
                # Try to infer from task ID or other fields
                continue
            if queue_id not in queue_to_tasks:
                queue_to_tasks[queue_id] = []
            queue_to_tasks[queue_id].append(task)

        # Also load queue files to get current state
        for queue_file in self.plan_queue_dir.glob("*.json"):
            if queue_file.name.endswith(".lock"):
                continue

            try:
                with open(queue_file) as f:
                    queue_data = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to parse queue file {queue_file}: {e}")
                continue

            queue_id = queue_data.get("queue_id")
            if not queue_id:
                continue

            # Get tasks for this queue
            queue_tasks = queue_to_tasks.get(queue_id, [])

            # Calculate queue-specific metrics
            completed = [t for t in queue_tasks if t.get("status") == "completed"]
            failed = [t for t in queue_tasks if t.get("status") == "failed"]
            pending = [t for t in queue_tasks if t.get("status") == "pending"]
            running = [t for t in queue_tasks if t.get("status") == "running"]

            # Stale tasks (pending > 24h)
            now = datetime.now()
            stale = 0
            for task in pending:
                created_str = task.get("created_at")
                if not created_str:
                    continue
                try:
                    created = _parse_datetime(created_str)
                    if created < now - timedelta(hours=24):
                        stale += 1
                except ValueError:
                    continue

            # Throughput (last 24h)
            recent_completed = []
            for task in completed:
                finished_str = task.get("finished_at")
                if not finished_str:
                    continue
                try:
                    finished = _parse_datetime(finished_str)
                    if finished > now - timedelta(hours=24):
                        recent_completed.append(task)
                except ValueError:
                    continue

            throughput = len(recent_completed) / 24.0 if recent_completed else 0.0

            # Average latency
            latencies = []
            for task in completed:
                started_str = task.get("started_at")
                finished_str = task.get("finished_at")
                if not started_str or not finished_str:
                    continue
                try:
                    started = _parse_datetime(started_str)
                    finished = _parse_datetime(finished_str)
                    latency = (finished - started).total_seconds() / 3600.0
                    if latency >= 0:
                        latencies.append(latency)
                except ValueError:
                    continue

            avg_latency = sum(latencies) / len(latencies) if latencies else None

            # Failure reasons for this queue
            failure_reasons = {}
            for task in failed:
                error = task.get("error", "").strip()
                if error:
                    key = error[:50]
                    failure_reasons[key] = failure_reasons.get(key, 0) + 1
                else:
                    failure_reasons["unknown"] = failure_reasons.get("unknown", 0) + 1

            metrics = QueueMetrics(
                queue_id=queue_id,
                total_items=len(queue_tasks),
                pending_items=len(pending),
                completed_items=len(completed),
                failed_items=len(failed),
                running_items=len(running),
                stale_items=stale,
                throughput_last_24h=throughput,
                avg_execution_latency=avg_latency,
                failure_reasons=failure_reasons,
            )
            queue_metrics.append(metrics)

        return queue_metrics

    def write_baseline(self, metrics: SystemMetrics, output_path: Path) -> Path:
        """Write metrics to a JSON baseline file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        metrics_dict = asdict(metrics)

        with open(output_path, "w") as f:
            json.dump(metrics_dict, f, indent=2, default=str)

        logger.info(f"Baseline written to {output_path}")
        return output_path

    def write_summary(self, metrics: SystemMetrics, output_path: Path) -> Path:
        """Write human-readable summary markdown file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            f.write("# Performance Metrics Summary\n\n")
            f.write(f"**Timestamp**: {metrics.timestamp}\n\n")

            f.write("## Overview\n")
            f.write(f"- **Total tasks**: {metrics.total_tasks}\n")
            f.write(f"- **Completed**: {metrics.total_completed}\n")
            f.write(f"- **Failed**: {metrics.total_failed}\n")
            f.write(f"- **Pending**: {metrics.total_pending} ({metrics.total_stale} stale)\n")
            f.write(f"- **Success rate**: {metrics.overall_success_rate:.1%}\n")
            f.write(
                f"- **Throughput (last 24h)**: {metrics.overall_throughput_24h:.2f} tasks/hour\n"
            )
            if metrics.avg_latency_all:
                f.write(f"- **Avg execution latency**: {metrics.avg_latency_all:.2f} hours\n")

            f.write("\n## Defensive Checks\n")
            f.write(f"- **Missing artifacts**: {metrics.missing_artifacts_count}\n")
            f.write(f"- **Duplicate pending tasks**: {metrics.duplicate_tasks_count}\n")
            f.write(f"- **Data quality issues**: {len(metrics.data_quality_issues)}\n")
            if metrics.data_quality_issues:
                f.write("\n### Data Quality Issues\n")
                for issue in metrics.data_quality_issues[:10]:
                    f.write(f"- {issue}\n")

            if metrics.failure_reason_distribution:
                f.write("\n## Top Failure Reasons\n")
                for reason, count in sorted(
                    metrics.failure_reason_distribution.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )[:10]:
                    f.write(f"- **{reason}**: {count}\n")

            if metrics.queue_metrics:
                f.write(f"\n## Queue Metrics ({len(metrics.queue_metrics)} queues)\n")
                for qm in metrics.queue_metrics:
                    f.write(f"\n### {qm.queue_id}\n")
                    f.write(f"- **Total items**: {qm.total_items}\n")
                    f.write(f"- **Completed**: {qm.completed_items}\n")
                    f.write(f"- **Failed**: {qm.failed_items}\n")
                    f.write(f"- **Pending**: {qm.pending_items} ({qm.stale_items} stale)\n")
                    f.write(f"- **Throughput (24h)**: {qm.throughput_last_24h:.2f} tasks/hour\n")
                    if qm.avg_execution_latency:
                        f.write(f"- **Avg latency**: {qm.avg_execution_latency:.2f} hours\n")

            f.write("\n---\n")
            f.write("*Generated by performance metrics collector*\n")

        logger.info(f"Summary written to {output_path}")
        return output_path


def main():
    parser = argparse.ArgumentParser(description="Collect performance metrics baseline")
    parser.add_argument(
        "--runtime-root",
        type=Path,
        default=Path("/Volumes/1TB-M2/openclaw"),
        help="Runtime root directory (default: /Volumes/1TB-M2/openclaw)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/Volumes/1TB-M2/openclaw/workspace/autoresearch"),
        help="Output directory for baseline files (default: workspace/autoresearch)",
    )
    parser.add_argument(
        "--baseline-name",
        type=str,
        default=None,
        help="Baseline file name (default: metrics_baseline_YYYYMMDD_HHMMSS.json)",
    )

    args = parser.parse_args()

    # Create collector
    collector = MetricsCollector(args.runtime_root)

    # Collect metrics
    metrics = collector.collect()

    # Determine output path
    if args.baseline_name:
        baseline_name = args.baseline_name
        if not baseline_name.endswith(".json"):
            baseline_name += ".json"
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        baseline_name = f"metrics_baseline_{timestamp}.json"

    output_path = args.output_dir / baseline_name

    # Write baseline
    collector.write_baseline(metrics, output_path)

    # Write summary markdown
    summary_path = output_path.with_suffix(".md")
    collector.write_summary(metrics, summary_path)

    # Print summary
    print("\n" + "=" * 60)
    print("Performance Metrics Baseline")
    print("=" * 60)
    print(f"Timestamp: {metrics.timestamp}")
    print(f"Total tasks: {metrics.total_tasks}")
    print(f"Completed: {metrics.total_completed}")
    print(f"Failed: {metrics.total_failed}")
    print(f"Pending: {metrics.total_pending} ({metrics.total_stale} stale)")
    print(f"Success rate: {metrics.overall_success_rate:.1%}")
    print(f"Throughput (last 24h): {metrics.overall_throughput_24h:.2f} tasks/hour")
    if metrics.avg_latency_all:
        print(f"Avg execution latency: {metrics.avg_latency_all:.2f} hours")

    if metrics.failure_reason_distribution:
        print("\nTop failure reasons:")
        for reason, count in sorted(
            metrics.failure_reason_distribution.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:5]:
            print(f"  {reason}: {count}")

    if metrics.queue_metrics:
        print(f"\nQueues analyzed: {len(metrics.queue_metrics)}")
        for qm in metrics.queue_metrics[:3]:  # Show first 3
            print(
                f"  {qm.queue_id}: {qm.completed_items}/{qm.total_items} completed, {qm.stale_items} stale"
            )

    print(f"\nBaseline saved to: {output_path}")
    print(f"Summary saved to: {summary_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
