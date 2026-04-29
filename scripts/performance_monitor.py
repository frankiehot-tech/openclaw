#!/usr/bin/env python3
"""
Performance Monitor Dashboard - Minimal summary of performance metrics and alerts.

Outputs structured JSON and human-readable markdown summary.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add scripts directory to path
scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

# Try to import performance metrics and alert engine
try:
    from agent.core.alert_rules import get_global_alert_engine
    from agent.core.performance_metrics import (
        MetricDimension,
        get_global_collector,
    )

    PERFORMANCE_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Performance modules not available: {e}")
    PERFORMANCE_MODULES_AVAILABLE = False


def collect_metrics_summary() -> dict[str, Any]:
    """Collect performance metrics summary."""
    if not PERFORMANCE_MODULES_AVAILABLE:
        return {"error": "Performance modules not available"}

    collector = get_global_collector()
    summary = collector.export_summary()

    # Add dimension-specific summaries
    dimension_summaries = {}
    for dim in [
        MetricDimension.RESPONSE_TIME,
        MetricDimension.QUEUE_LENGTH,
        MetricDimension.FAILURE_RATE,
        MetricDimension.CONCURRENCY,
        MetricDimension.SUCCESS_RATE,
    ]:
        aggregations = collector.get_aggregations(dimension=dim)
        if aggregations:
            # Take the most recent aggregation (by window_end)
            agg = max(aggregations, key=lambda a: a.window_end)
            dimension_summaries[dim.value] = {
                "count": agg.count,
                "avg": agg.avg,
                "min": agg.min,
                "max": agg.max,
                "unit": (
                    "seconds"
                    if dim == MetricDimension.RESPONSE_TIME
                    else (
                        "tasks"
                        if dim == MetricDimension.QUEUE_LENGTH
                        else (
                            "ratio"
                            if dim in (MetricDimension.FAILURE_RATE, MetricDimension.SUCCESS_RATE)
                            else "tasks"
                        )
                    )
                ),
            }

    summary["dimension_summaries"] = dimension_summaries
    return summary


def collect_alerts_summary() -> dict[str, Any]:
    """Collect alert summary."""
    if not PERFORMANCE_MODULES_AVAILABLE:
        return {"error": "Performance modules not available"}

    engine = get_global_alert_engine()
    summary = engine.export_summary()

    # Evaluate alerts to ensure freshness
    new_alerts = engine.evaluate_all()
    if new_alerts:
        summary["new_alerts_generated"] = len(new_alerts)
        # Update summary with fresh data
        summary = engine.export_summary()

    return summary


def generate_markdown_report(
    metrics_summary: dict[str, Any], alerts_summary: dict[str, Any]
) -> str:
    """Generate human-readable markdown report."""
    lines = []
    lines.append("# Performance Monitor Dashboard")
    lines.append(f"Generated: {datetime.now().isoformat()}")
    lines.append("")

    # Metrics section
    lines.append("## Performance Metrics")
    if "error" in metrics_summary:
        lines.append(f"Error: {metrics_summary['error']}")
    else:
        lines.append(f"- **Sample count**: {metrics_summary.get('sample_count', 0)}")
        lines.append(f"- **Aggregation count**: {metrics_summary.get('aggregation_count', 0)}")

        dim_summaries = metrics_summary.get("dimension_summaries", {})
        if dim_summaries:
            lines.append("\n### Key Metrics")
            for dim, data in dim_summaries.items():
                unit = data.get("unit", "")
                lines.append(
                    f"- **{dim}**: {data['avg']:.2f} {unit} (min: {data['min']:.2f}, max: {data['max']:.2f}, samples: {data['count']})"
                )

    # Alerts section
    lines.append("\n## Active Alerts")
    if "error" in alerts_summary:
        lines.append(f"Error: {alerts_summary['error']}")
    else:
        active_count = alerts_summary.get("active_alert_count", 0)
        lines.append(f"- **Active alerts**: {active_count}")

        alerts_by_level = alerts_summary.get("alerts_by_level", {})
        for level in ["critical", "warning", "info"]:
            count = alerts_by_level.get(level, 0)
            if count > 0:
                lines.append(f"  - **{level.upper()}**: {count}")

        active_alerts = alerts_summary.get("active_alerts", [])
        if active_alerts:
            lines.append("\n### Recent Alerts")
            for alert in active_alerts[:5]:  # Show top 5
                lines.append(
                    f"- **{alert.get('alert_level', 'unknown').upper()}**: {alert.get('message', 'No message')}"
                )
                lines.append(
                    f"  - Metric: {alert.get('metric_dimension', 'unknown')} = {alert.get('metric_value', 0):.2f} (threshold: {alert.get('threshold', 0):.2f})"
                )
                lines.append(
                    f"  - Time: {datetime.fromtimestamp(alert.get('timestamp', 0)).isoformat() if alert.get('timestamp') else 'unknown'}"
                )

    # Overall status
    lines.append("\n## Overall Status")
    if alerts_summary.get("active_alert_count", 0) == 0:
        lines.append("✅ **All systems nominal** - No active alerts")
    else:
        critical_count = alerts_summary.get("alerts_by_level", {}).get("critical", 0)
        warning_count = alerts_summary.get("alerts_by_level", {}).get("warning", 0)
        if critical_count > 0:
            lines.append(
                f"🔴 **CRITICAL** - {critical_count} critical alert(s) require immediate attention"
            )
        elif warning_count > 0:
            lines.append(f"🟡 **WARNING** - {warning_count} warning(s) need monitoring")
        else:
            lines.append("🔵 **INFO** - Informational alerts present")

    lines.append("\n---")
    lines.append("*Generated by performance monitor dashboard*")
    return "\n".join(lines)


def main():
    """Main function."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("Collecting performance metrics and alerts...")

    # Collect summaries
    metrics_summary = collect_metrics_summary()
    alerts_summary = collect_alerts_summary()

    # Generate markdown report
    markdown_report = generate_markdown_report(metrics_summary, alerts_summary)

    # Output to console
    print("\n" + "=" * 60)
    print(markdown_report)
    print("=" * 60)

    # Save to files
    output_dir = Path("/Volumes/1TB-M2/openclaw/workspace/performance")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save JSON combined report
    combined_report = {
        "timestamp": datetime.now().isoformat(),
        "metrics": metrics_summary,
        "alerts": alerts_summary,
    }

    json_path = output_dir / f"performance_report_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(combined_report, f, indent=2, ensure_ascii=False)
    print(f"\nJSON report saved to: {json_path}")

    # Save markdown report
    md_path = output_dir / f"performance_report_{timestamp}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown_report)
    print(f"Markdown report saved to: {md_path}")

    # Exit with error code if critical alerts present
    if alerts_summary.get("alerts_by_level", {}).get("critical", 0) > 0:
        print("\n⚠️  Critical alerts detected - exiting with code 1")
        sys.exit(1)
    elif alerts_summary.get("alerts_by_level", {}).get("warning", 0) > 0:
        print("\n⚠️  Warning alerts detected")
        sys.exit(0)
    else:
        print("\n✅ No critical or warning alerts")
        sys.exit(0)


if __name__ == "__main__":
    main()
